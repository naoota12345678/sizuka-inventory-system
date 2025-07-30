#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import logging

# ログ設定を最初に行う
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 必須のインポート
from fastapi import FastAPI, HTTPException
import httpx
import base64
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
import asyncio
from datetime import timezone
import pytz
import json
import traceback
import re
from dotenv import load_dotenv

# 環境変数の読み込み
load_dotenv()

# FastAPIアプリケーションの作成
app = FastAPI()

# Supabaseクライアントの初期化を試みる
try:
    from supabase import create_client
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_KEY')
    
    if supabase_url and supabase_key:
        supabase = create_client(supabase_url, supabase_key)
        logger.info("Supabase client initialized successfully")
    else:
        logger.warning("Supabase credentials not found in environment variables")
        supabase = None
except Exception as e:
    logger.error(f"Failed to initialize Supabase client: {e}")
    supabase = None

# データベース初期化関数のインポート（エラーハンドリング付き）
try:
    from product_master.db_setup import initialize_database
    DB_SETUP_AVAILABLE = True
except Exception as e:
    DB_SETUP_AVAILABLE = False
    logger.warning(f"Could not import db_setup: {e}")
    # ダミー関数を定義
    def initialize_database():
        return {}

# Google Sheets同期は必要な場合のみインポート
SHEETS_SYNC_AVAILABLE = False
GoogleSheetsSync = None

try:
    # 必要なパッケージがインストールされているか確認
    import google.auth
    import googleapiclient
    import pandas
    
    # sheets_syncモジュールをインポート
    from product_master.sheets_sync import GoogleSheetsSync as _GoogleSheetsSync
    GoogleSheetsSync = _GoogleSheetsSync
    
    # Google認証の確認
    google_creds_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    google_creds_file = os.getenv('GOOGLE_CREDENTIALS_FILE')
    
    # 複数のパスを試す
    cred_paths = [
        google_creds_path,
        google_creds_file,
        '/app/credentials.json',
        'google-credentials.json'
    ]
    
    cred_file_found = False
    for path in cred_paths:
        if path and os.path.exists(path):
            cred_file_found = True
            logger.info(f"Google credentials found at: {path}")
            break
    
    if cred_file_found:
        SHEETS_SYNC_AVAILABLE = True
        logger.info("Google Sheets sync is available")
    else:
        logger.warning("Google Sheets credentials file not found")
        
except ImportError as e:
    logger.warning(f"Google Sheets sync not available - missing dependencies: {e}")
except Exception as e:
    logger.warning(f"Google Sheets sync not available: {e}")

# 残りのコードは同じ...

def extract_product_code_prefix(product_name):
    """商品名から先頭の商品コード部分を抽出する
    
    例: "S01 ひとくちサーモン 30g" -> "S01"
    """
    if not product_name:
        return ""
    
    # 空白またはハイフンの前までの文字列を取得
    parts = product_name.split()
    if not parts:
        return ""
    
    # 先頭部分が商品コードのパターンに一致するか確認（S01など）
    prefix = parts[0]
    if re.match(r'^[A-Z]\d{2}$', prefix):  # 「アルファベット1文字+数字2桁」のパターン
        return prefix
    
    return ""

def extract_sku_data(sku_models: List[Dict]) -> Tuple[str, str, str, Dict]:
    """SKUモデルから必要なデータを抽出する
    
    Args:
        sku_models: SkuModelListのデータ
        
    Returns:
        Tuple containing:
            merchant_item_id: 商品管理番号
            item_number: 商品番号（JANコードなど）
            variant_id: バリエーションID
            item_choice: 選択肢情報（辞書形式）
    """
    # デフォルト値を設定
    merchant_item_id = ""
    item_number = ""
    variant_id = ""
    item_choice = {}
    
    if not sku_models:
        return merchant_item_id, item_number, variant_id, item_choice
    
    # 最初のSKUモデルを使用する
    sku = sku_models[0]
    
    # 商品管理番号（merchantDefinedSkuId）を抽出
    if sku.get("merchantDefinedSkuId") is not None:
        merchant_item_id = str(sku.get("merchantDefinedSkuId"))
    
    # バリエーションID（variantId）を抽出
    if sku.get("variantId") is not None:
        variant_id = str(sku.get("variantId"))
    
    # 選択肢情報（skuInfo）を抽出
    sku_info = sku.get("skuInfo")
    if isinstance(sku_info, dict):
        item_choice = sku_info
        
        # JANコードなどを探す（skuInfoにデータがある場合）
        if "janCode" in sku_info:
            item_number = str(sku_info.get("janCode", ""))
    
    return merchant_item_id, item_number, variant_id, item_choice

def extract_selected_choices(selected_choice_text):
    """
    selectedChoiceテキストから選択された商品コードと商品名を抽出する
    
    Args:
        selected_choice_text: selectedChoiceフィールドのテキスト
        
    Returns:
        選択された商品コードと商品名のリスト
    """
    if not selected_choice_text:
        return []
    
    choices = []
    
    # 改行で分割
    lines = selected_choice_text.split('\n')
    
    # 選択肢の行を処理（◆から始まる行）
    for line in lines:
        if line.startswith('◆'):
            # コロンで分割して右側（選択内容）を取得
            parts = line.split(':', 1)
            if len(parts) > 1:
                choice_info = parts[1].strip()
                
                # 商品コード（RXXなど）を抽出
                code_match = re.search(r'(R\d+|S\d+)', choice_info)
                code = code_match.group(1) if code_match else ""
                
                # 商品名（コードの後のテキスト）
                name = choice_info
                if code:
                    name = re.sub(r'^' + re.escape(code) + r'\s+', '', choice_info)
                
                choices.append({
                    "code": code,
                    "name": name
                })
    
    return choices

class RakutenAPI:
    def __init__(self):
        self.service_secret = os.getenv('RAKUTEN_SERVICE_SECRET')
        self.license_key = os.getenv('RAKUTEN_LICENSE_KEY')
        
        if not self.service_secret or not self.license_key:
            raise ValueError("Environment variables RAKUTEN_SERVICE_SECRET and RAKUTEN_LICENSE_KEY must be set")
        
        # 認証ヘッダーの生成
        auth_string = f"{self.service_secret}:{self.license_key}"
        encoded_auth = base64.b64encode(auth_string.encode('utf-8')).decode('utf-8')
        
        self.headers = {
            'Authorization': f'ESA {encoded_auth}',
            'Content-Type': 'application/json; charset=utf-8'
        }
        self.jst = pytz.timezone('Asia/Tokyo')
        self.base_url = 'https://api.rms.rakuten.co.jp/es/2.0'

    async def get_orders(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """注文データの検索"""
        url = f'{self.base_url}/purchaseItem/searchOrderItem/'
        
        jst_st = start_date.astimezone(self.jst).strftime("%Y-%m-%dT%H:%M:%S+0900")
        jst_ed = end_date.astimezone(self.jst).strftime("%Y-%m-%dT%H:%M:%S+0900")

        search_data = {
            "dateType": 1,
            "startDatetime": jst_st,
            "endDatetime": jst_ed,
            "orderProgressList": [100, 200, 300, 400, 500, 600, 700],
            "PaginationRequestModel": {
                "requestRecordsAmount": 1000,
                "requestPage": 1
            }
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    headers=self.headers,
                    json=search_data,
                    timeout=30.0
                )

                if response.status_code == 401:
                    raise HTTPException(status_code=401, detail=f"Authentication failed: {response.text}")

                response.raise_for_status()
                data = response.json()
                order_numbers = data.get('orderNumberList', [])

                if order_numbers:
                    return await self.get_order_details(order_numbers)
                return []

        except Exception as e:
            logger.error(f"Error in get_orders: {str(e)}")
            raise

    async def get_order_details(self, order_numbers: List[str]) -> List[Dict]:
        """注文の詳細情報を取得"""
        url = f'{self.base_url}/purchaseItem/getOrderItem/'
        chunk_size = 100
        all_orders = []
        
        for i in range(0, len(order_numbers), chunk_size):
            chunk = order_numbers[i:i + chunk_size]
            order_data = {'orderNumberList': chunk}
            
            try:
                async with httpx.AsyncClient() as client:
                    logger.info(f"Getting details for orders {i+1} to {i+len(chunk)}")
                    
                    response = await client.post(
                        url,
                        headers=self.headers,
                        json=order_data,
                        timeout=30.0
                    )
                    
                    if response.status_code == 401:
                        raise HTTPException(status_code=401, detail="Authentication failed")
                    
                    response.raise_for_status()
                    data = response.json()
                    
                    if 'OrderModelList' in data:
                        all_orders.extend(data['OrderModelList'])
                    
            except Exception as e:
                logger.error(f"Error getting order details for chunk {i//chunk_size + 1}: {str(e)}")
                continue
        
        return all_orders

    async def save_to_supabase(self, orders: List[Dict]):
        """注文データをSupabaseに保存"""
        MAX_RETRIES = 3
        RETRY_DELAY = 1
        
        try:
            # 楽天のplatform_idを取得
            platform_response = await self._get_platform_id_with_retry()
            rakuten_platform_id = platform_response.data[0]['id']
            
            success_count = 0
            error_count = 0
            items_success = 0
            items_error = 0
            failed_orders = []
            processed_orders = set()

            for order in orders:
                order_number = order.get('orderNumber')
                if not order_number or order_number in processed_orders:
                    logger.warning(f"Skipping invalid or duplicate order: {order_number}")
                    continue
                    
                processed_orders.add(order_number)
                
                try:
                    # 注文データの準備
                    order_data = {
                        "platform_id": rakuten_platform_id,
                        "order_number": order["orderNumber"],
                        "order_date": order.get("orderDatetime") or order.get("shopOrderCfmDatetime"),
                        "total_amount": float(order.get("totalPrice", 0)),
                        "shipping_fee": float(order.get("postagePrice", 0)),
                        "payment_method": order.get("SettlementModel", {}).get("settlementMethodCode", ""),
                        "order_status": str(order.get("orderProgress", "")),
                        "coupon_amount": float(order.get("couponAllTotalPrice", 0)),
                        "point_amount": float(order.get("PointModel", {}).get("usedPoint", 0)),
                        "request_price": float(order.get("requestPrice", 0)),
                        "deal_price": float(order.get("goodsPrice", 0)),
                        "platform_data": json.dumps(order),
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    }

                    # 注文データの保存
                    order_result = supabase.table("orders").upsert(
                        order_data,
                        on_conflict="platform_id,order_number"
                    ).execute()

                    if not order_result.data:
                        raise Exception(f"Failed to save order: {order_number}")

                    order_id = order_result.data[0]["id"]
                    logger.info(f"Successfully saved order {order_number} with ID: {order_id}")

                    # 注文商品情報の保存
                    items = []
                    for package in order.get("PackageModelList", []):
                        items.extend(package.get("ItemModelList", []))
                    
                    if not items:
                        logger.warning(f"No items found for order: {order_number}")
                        continue

                    for item in items:
                        for attempt in range(MAX_RETRIES):
                            try:
                                # まとめ商品の処理
                                is_parent = item.get("itemType") == 1
                                parent_product_code = ""
                                
                                # SKU情報の処理
                                sku_models = item.get("SkuModelList", [])
                                # JSON形式で保存する情報
                                sku_info = {
                                    "variantId": sku_models[0].get("variantId") if sku_models else None,
                                    "merchantDefinedSkuId": sku_models[0].get("merchantDefinedSkuId") if sku_models else None,
                                    "skuInfo": sku_models[0].get("skuInfo") if sku_models else None
                                }
                                
                                # 新しい列への保存用データを抽出
                                # SKUモデルからデータを抽出
                                merchant_item_id, item_number, variant_id, item_choice = extract_sku_data(sku_models)
                                
                                # 商品番号と管理番号も設定（APIから直接取得）
                                if not item_number and item.get("itemNumber"):
                                    item_number = item.get("itemNumber")
                                
                                if not merchant_item_id and item.get("manageNumber"):
                                    merchant_item_id = item.get("manageNumber")
                                
                                # 選択された商品の選択肢情報を抽出
                                selected_choice = item.get("selectedChoice", "")
                                choices = extract_selected_choices(selected_choice)
                                
                                # 商品名から商品コードプレフィックスを抽出
                                item_name = item.get("itemName", "")
                                product_code_prefix = extract_product_code_prefix(item_name)

                                if is_parent:
                                    # 親商品として処理
                                    item_data = {
                                        "order_id": order_id,
                                        "product_code": str(item.get("itemId", "")),
                                        "product_name": item_name,
                                        "quantity": int(item.get("units", 0)),
                                        "unit_price": float(item.get("price", 0)),
                                        "total_price": float(item.get("price", 0)) * int(item.get("units", 0)),
                                        "point_rate": float(item.get("pointRate", 0)) if "pointRate" in item else 0,
                                        "tax_rate": float(item.get("taxRate", 0)),
                                        "sku_info": json.dumps(sku_info) if sku_info else None,
                                        "deal_flag": bool(item.get("dealFlag", False)),
                                        "restore_inventory_flag": bool(item.get("restoreInventoryFlag", False)),
                                        "is_parent": True,
                                        "is_child": False,
                                        "parent_product_code": "",
                                        "product_code_prefix": product_code_prefix,
                                        # 新しいカラムに値を設定
                                        "merchant_item_id": merchant_item_id,
                                        "item_number": item_number,
                                        "variant_id": variant_id,
                                        "item_choice": json.dumps(choices) if choices else None,
                                        "selected_choice_raw": selected_choice,  # 元のテキストも保存
                                        "created_at": datetime.now(timezone.utc).isoformat(),
                                        "updated_at": datetime.now(timezone.utc).isoformat()
                                    }
                                    
                                    # 親商品のデータを保存
                                    item_result = supabase.table("order_items").insert(item_data).execute()
                                    
                                    if not item_result.data:
                                        raise Exception(f"No data returned when saving parent item: {item_data['product_code']}")
                                    
                                    logger.info(f"Successfully saved parent item {item_data['product_code']} for order {order_number}")
                                    items_success += 1
                                    
                                    # selectedItemsから子商品情報を抽出
                                    selected_items = item.get("selectedItems", [])
                                    for child_item in selected_items:
                                        child_name = child_item.get("itemName", "")
                                        child_prefix = extract_product_code_prefix(child_name)
                                        
                                        child_item_data = {
                                            "order_id": order_id,
                                            "product_code": str(child_item.get("itemId", "")),
                                            "product_name": child_name,
                                            "quantity": int(item.get("units", 0)),  # 親商品と同じ数量
                                            "unit_price": 0,  # 個別価格は通常表示されない
                                            "total_price": 0,
                                            "point_rate": 0,
                                            "tax_rate": 0,
                                            "sku_info": None,
                                            "deal_flag": False,
                                            "restore_inventory_flag": False,
                                            "is_parent": False,
                                            "is_child": True,
                                            "parent_product_code": str(item.get("itemId", "")),
                                            "product_code_prefix": child_prefix,
                                            # 新しいカラムに値を設定
                                            "merchant_item_id": child_item.get("manageNumber", ""),
                                            "item_number": child_item.get("itemNumber", ""),
                                            "variant_id": "",
                                            "item_choice": None,
                                            "selected_choice_raw": None,
                                            "created_at": datetime.now(timezone.utc).isoformat(),
                                            "updated_at": datetime.now(timezone.utc).isoformat()
                                        }
                                        
                                        # 子商品データの保存
                                        child_result = supabase.table("order_items").insert(child_item_data).execute()
                                        
                                        if not child_result.data:
                                            raise Exception(f"No data returned when saving child item: {child_item_data['product_code']}")
                                        
                                        logger.info(f"Successfully saved child item {child_item_data['product_code']} for order {order_number}")
                                        items_success += 1
                                else:
                                    # 通常商品の処理
                                    item_data = {
                                        "order_id": order_id,
                                        "product_code": str(item.get("itemId", "")),
                                        "product_name": item_name,
                                        "quantity": int(item.get("units", 0)),
                                        "unit_price": float(item.get("price", 0)),
                                        "total_price": float(item.get("price", 0)) * int(item.get("units", 0)),
                                        "point_rate": float(item.get("pointRate", 0)) if "pointRate" in item else 0,
                                        "tax_rate": float(item.get("taxRate", 0)),
                                        "sku_info": json.dumps(sku_info) if sku_info else None,
                                        "deal_flag": bool(item.get("dealFlag", False)),
                                        "restore_inventory_flag": bool(item.get("restoreInventoryFlag", False)),
                                        "is_parent": False,
                                        "is_child": False,
                                        "parent_product_code": "",
                                        "product_code_prefix": product_code_prefix,
                                        # 新しいカラムに値を設定
                                        "merchant_item_id": merchant_item_id,
                                        "item_number": item_number,
                                        "variant_id": variant_id,
                                        "item_choice": json.dumps(choices) if choices else None,
                                        "selected_choice_raw": selected_choice,  # 元のテキストも保存
                                        "created_at": datetime.now(timezone.utc).isoformat(),
                                        "updated_at": datetime.now(timezone.utc).isoformat()
                                    }
                                    
                                    # 商品データの保存
                                    item_result = supabase.table("order_items").insert(item_data).execute()
                                    
                                    if not item_result.data:
                                        raise Exception(f"No data returned when saving item: {item_data['product_code']}")
                                    
                                    logger.info(f"Successfully saved item {item_data['product_code']} for order {order_number}")
                                    items_success += 1
                                    
                                break

                            except Exception as e:
                                error_msg = str(e)
                                logger.error(f"[DEBUG] Error saving item: {error_msg}")
                                logger.error(f"[DEBUG] Stacktrace: {traceback.format_exc()}")
                                
                                if attempt < MAX_RETRIES - 1:
                                    logger.warning(f"Retrying... Attempt {attempt + 1} of {MAX_RETRIES}")
                                    await asyncio.sleep(RETRY_DELAY)
                                else:
                                    items_error += 1
                                    logger.error(f"Failed all retry attempts for item")

                    success_count += 1
                    
                except Exception as e:
                    logger.error(f"Error processing order {order_number}: {str(e)}")
                    error_count += 1
                    failed_orders.append({
                        'order_number': order_number,
                        'error': str(e)
                    })

            result = {
                'total_orders': len(orders),
                'success_count': success_count,
                'error_count': error_count,
                'items_success': items_success,
                'items_error': items_error,
                'success_rate': f"{(success_count / len(orders) * 100):.2f}%" if orders else "0%",
                'failed_orders': failed_orders
            }

            logger.info(f"Sync complete: {json.dumps(result, indent=2)}")
            return result

        except Exception as e:
            logger.error(f"Critical error in save_to_supabase: {str(e)}")
            raise

    async def _get_platform_id_with_retry(self, max_retries=3, delay=1):
        """Platform IDの取得（リトライ機能付き）"""
        if not supabase:
            raise ValueError("Supabase client is not initialized")
        
        for attempt in range(max_retries):
            try:
                response = supabase.table("platform").select("id").eq("platform_code", "rakuten").execute()
                if response.data:
                    return response
                raise ValueError("Platform 'rakuten' not found")
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(delay)

#################################################
# 在庫管理用の共通関数
#################################################

async def get_platform_id(platform_code):
    """プラットフォームコードからIDを取得"""
    try:
        platform_result = supabase.table("platform").select("id").eq("platform_code", platform_code).execute()
        if platform_result.data:
            return platform_result.data[0]["id"]
        return None
    except Exception as e:
        logger.error(f"プラットフォームID取得エラー: {str(e)}")
        return None

async def update_inventory(product_code, quantity, movement_type, reference_id, platform_id, notes=""):
    """在庫を更新し、在庫変動を記録する（全プラットフォーム共通）"""
    try:
        # 商品が在庫テーブルに存在するか確認
        inventory_result = supabase.table("inventory").select("*").eq(
            "product_code", product_code
        ).eq("platform_id", platform_id).execute()
        
        if not inventory_result.data:
            logger.warning(f"商品 {product_code} (プラットフォームID: {platform_id}) は在庫テーブルに存在しません。スキップします。")
            return False
        
        # 1. 在庫変動を記録
        movement_data = {
            "product_code": product_code,
            "platform_id": platform_id,
            "quantity": quantity,
            "movement_type": movement_type,
            "reference_id": reference_id,
            "notes": notes,
            "movement_date": datetime.now(timezone.utc).isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        movement_result = supabase.table("stock_movements").insert(movement_data).execute()
        
        # 2. 在庫テーブルの更新
        current_stock = inventory_result.data[0]["current_stock"]
        new_stock = current_stock + quantity
        
        update_result = supabase.table("inventory").update({
            "current_stock": new_stock,
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }).eq("id", inventory_result.data[0]["id"]).execute()
        
        return True
    
    except Exception as e:
        logger.error(f"在庫更新エラー ({product_code}): {str(e)}")
        raise
    
#################################################
# 楽天プラットフォーム在庫管理コネクタ
#################################################

class RakutenConnector:
    """楽天用在庫管理コネクタ"""
    
    def __init__(self):
        self.platform_code = "rakuten"
        self.platform_id = None
    
    async def initialize(self):
        """プラットフォームIDを初期化"""
        self.platform_id = await get_platform_id(self.platform_code)
        if not self.platform_id:
            raise ValueError(f"プラットフォーム '{self.platform_code}' が見つかりません")
        return self.platform_id
    
    async def extract_inventory_items(self, days=None):
        """楽天の注文データから在庫管理用の商品を抽出"""
        await self.initialize()
        
        try:
            # 注文データ取得期間を設定（指定がなければすべて）
            query = supabase.table("order_items").select(
                "product_code", "product_name", "merchant_item_id", 
                "item_number", "variant_id", "is_parent", "is_child"
            )
            
            if days:
                start_date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
                # order_idから対応する注文日時が一定期間内のものだけを取得
                orders = supabase.table("orders").select("id").gte("order_date", start_date).execute()
                order_ids = [order["id"] for order in orders.data]
                if order_ids:
                    query = query.in_("order_id", order_ids)
            
            items_result = query.execute()
            
            if not items_result.data:
                return {"message": "抽出可能な商品がありません"}
            
            # 在庫管理対象の商品を格納するリスト
            inventory_items = []
            unique_product_codes = set()
            
            for item in items_result.data:
                product_code = item.get("product_code")
                
                # 親商品は除外し、通常商品または子商品のみを対象とする
                if (not item.get("is_parent", False)) and product_code and product_code not in unique_product_codes:
                    inventory_items.append({
                        "product_code": product_code,
                        "product_name": item.get("product_name", ""),
                        "platform_id": self.platform_id,
                        "platform_product_id": product_code,  # 楽天の場合は同じ
                        "merchant_item_id": item.get("merchant_item_id", ""),
                        "item_number": item.get("item_number", ""),
                        "variant_id": item.get("variant_id", ""),
                        "is_active": True
                    })
                    unique_product_codes.add(product_code)
            
            # チョイス商品の選択肢も抽出
            items_with_choices = supabase.table("order_items").select(
                "item_choice"
            ).neq("item_choice", None).execute()
            
            for item in items_with_choices.data:
                item_choice = item.get("item_choice")
                if item_choice:
                    try:
                        choices = json.loads(item_choice)
                        for choice in choices:
                            if "code" in choice and choice["code"] and choice["code"] not in unique_product_codes:
                                inventory_items.append({
                                    "product_code": choice["code"],
                                    "product_name": choice.get("name", ""),
                                    "platform_id": self.platform_id,
                                    "platform_product_id": choice["code"],
                                    "merchant_item_id": "",
                                    "item_number": "",
                                    "variant_id": "",
                                    "is_active": True
                                })
                                unique_product_codes.add(choice["code"])
                    except (json.JSONDecodeError, TypeError):
                        continue
            
            return {
                "total_items": len(inventory_items),
                "inventory_items": inventory_items
            }
        
        except Exception as e:
            logger.error(f"楽天商品抽出エラー: {str(e)}")
            raise
    
    async def process_order_inventory(self, order_id):
        """楽天注文の在庫減少処理"""
        await self.initialize()
        
        try:
            # 注文商品を取得
            items_result = supabase.table("order_items").select("*").eq("order_id", order_id).execute()
            
            processed_items = []
            
            for item in items_result.data:
                product_code = item["product_code"]
                quantity = item["quantity"]
                
                # 親商品は除外し、通常商品と子商品のみを処理
                if not item.get("is_parent", False):
                    # 在庫を減少
                    await update_inventory(
                        product_code, 
                        -quantity, 
                        "order", 
                        order_id, 
                        self.platform_id
                    )
                    processed_items.append({
                        "product_code": product_code,
                        "quantity": quantity,
                        "type": "通常商品" if not item.get("is_child", False) else "子商品"
                    })
                
                # チョイス商品の選択肢があれば処理
                if item.get("item_choice"):
                    try:
                        choices = json.loads(item["item_choice"])
                        for choice in choices:
                            if "code" in choice and choice["code"]:
                                # 選択された子商品の在庫を減少
                                await update_inventory(
                                    choice["code"], 
                                    -quantity, 
                                    "order", 
                                    order_id, 
                                    self.platform_id,
                                    notes=f"チョイス商品の選択肢：{choice.get('name', '')}"
                                )
                                processed_items.append({
                                    "product_code": choice["code"],
                                    "quantity": quantity,
                                    "type": "チョイス商品選択肢"
                                })
                    except (json.JSONDecodeError, TypeError):
                        logger.warning(f"選択肢データの解析に失敗: {item.get('item_choice')}")
                        continue
            
            return {
                "success": True,
                "order_id": order_id,
                "platform": self.platform_code,
                "processed_items": processed_items
            }
        
        except Exception as e:
            logger.error(f"楽天在庫処理エラー: {str(e)}")
            raise
    
    async def update_sales_data(self, days=7):
        """楽天の売上データを更新する"""
        await self.initialize()
        
        try:
            # 期間指定
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=days)
            
            # 注文データを取得
            orders_result = supabase.table("orders").select("*").gte(
                "order_date", start_date.isoformat()
            ).lte("order_date", end_date.isoformat()).execute()
            
            if not orders_result.data:
                return {"message": "対象期間の注文データがありません"}
            
            # 処理済み注文のカウント
            processed_count = 0
            sales_data = {}  # 日付・商品別の売上データ
            
            for order in orders_result.data:
                order_id = order["id"]
                order_date_str = order.get("order_date")
                
                if not order_date_str:
                    continue
                    
                # 注文日をDateオブジェクトに変換
                try:
                    order_date = datetime.fromisoformat(order_date_str.replace('Z', '+00:00')).date()
                except ValueError:
                    logger.warning(f"日付形式が無効: {order_date_str}")
                    continue
                
                # 注文商品を取得
                items_result = supabase.table("order_items").select("*").eq("order_id", order_id).execute()
                
                for item in items_result.data:
                    # 親商品は除外
                    if item.get("is_parent", False):
                        continue
                    
                    product_code = item["product_code"]
                    product_name = item.get("product_name", "")
                    quantity = item.get("quantity", 0)
                    unit_price = item.get("unit_price", 0)
                    
                    # 売上を計算
                    sales_amount = unit_price * quantity
                    
                    # 日付・商品ごとに集計
                    key = (order_date.isoformat(), product_code)
                    if key not in sales_data:
                        sales_data[key] = {
                            "date": order_date.isoformat(),
                            "product_code": product_code,
                            "product_name": product_name,
                            "platform_id": self.platform_id,
                            "units": 0,
                            "sales": 0
                        }
                    
                    sales_data[key]["units"] += quantity
                    sales_data[key]["sales"] += sales_amount
                
                # チョイス商品の選択肢も処理
                for item in items_result.data:
                    item_choice = item.get("item_choice")
                    if item_choice:
                        try:
                            choices = json.loads(item_choice)
                            quantity = item.get("quantity", 0)
                            # チョイス商品は単価0円で集計（数量のみ）
                            for choice in choices:
                                if "code" in choice and choice["code"]:
                                    key = (order_date.isoformat(), choice["code"])
                                    if key not in sales_data:
                                        sales_data[key] = {
                                            "date": order_date.isoformat(),
                                            "product_code": choice["code"],
                                            "product_name": choice.get("name", ""),
                                            "platform_id": self.platform_id,
                                            "units": 0,
                                            "sales": 0  # チョイス商品単体の売上は0円
                                        }
                                    
                                    sales_data[key]["units"] += quantity
                        except (json.JSONDecodeError, TypeError):
                            continue
                
                processed_count += 1
            
            # 集計データをsales_dailyテーブルに保存
            inserted_count = 0
            updated_count = 0
            
            for key, data in sales_data.items():
                # 既存データを検索
                existing = supabase.table("sales_daily").select("*").eq(
                    "summary_date", data["date"]
                ).eq("product_code", data["product_code"]).eq(
                    "platform_id", data["platform_id"]
                ).execute()
                
                if existing.data:
                    # 既存データを更新
                    supabase.table("sales_daily").update({
                        "units_sold": data["units"],
                        "gross_sales": data["sales"],
                        "net_sales": data["sales"],
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    }).eq("id", existing.data[0]["id"]).execute()
                    updated_count += 1
                else:
                    # 新規データを挿入
                    supabase.table("sales_daily").insert({
                        "summary_date": data["date"],
                        "product_code": data["product_code"],
                        "product_name": data["product_name"],
                        "platform_id": data["platform_id"],
                        "units_sold": data["units"],
                        "gross_sales": data["sales"],
                        "discounts": 0,
                        "net_sales": data["sales"],
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    }).execute()
                    inserted_count += 1
            
            return {
                "message": "売上データを更新しました",
                "platform": self.platform_code,
                "processed_orders": processed_count,
                "total_products": len(sales_data),
                "inserted": inserted_count,
                "updated": updated_count
            }
            
        except Exception as e:
            logger.error(f"楽天売上更新エラー: {str(e)}")
            raise

#################################################
# 元のAPIエンドポイント
#################################################

@app.on_event("startup")
async def startup_event():
    """アプリケーション起動時の処理"""
    try:
        if DB_SETUP_AVAILABLE:
            # データベースの初期化チェック
            existing_tables = initialize_database()
            logger.info(f"データベース初期化チェック完了: {existing_tables}")
        else:
            logger.warning("データベース初期化機能は利用できません")
    except Exception as e:
        logger.error(f"起動時エラー: {str(e)}")
        # エラーが発生してもアプリケーションは継続

@app.get("/")
async def root():
    """ルートエンドポイント"""
    return {
        "message": "Rakuten Order Sync API",
        "version": "1.0.0",
        "endpoints": [
            "/health",
            "/sync-orders",
            "/check-connection",
            "/docs"
        ]
    }

@app.get("/debug-env")
async def debug_environment():
    """環境変数とファイルの存在を確認"""
    import os
    google_creds_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', 'Not set')
    
    result = {
        "google_creds_env": google_creds_path,
        "file_exists": os.path.exists(google_creds_path) if google_creds_path != 'Not set' else False,
        "working_directory": os.getcwd(),
        "app_files": os.listdir('/app') if os.path.exists('/app') else [],
        "sheets_sync_available": SHEETS_SYNC_AVAILABLE
    }
    
    # 認証ファイルが存在する場合、ファイルサイズも確認
    if result["file_exists"]:
        result["file_size"] = os.path.getsize(google_creds_path)
    
    # 追加のデバッグ情報
    result["debug_info"] = {
        "google_auth_imported": "google.auth" in sys.modules,
        "googleapiclient_imported": "googleapiclient" in sys.modules,
        "pandas_imported": "pandas" in sys.modules,
        "GoogleSheetsSync_loaded": GoogleSheetsSync is not None
    }
    
    return result

@app.get("/health")
async def health_check():
    """ヘルスチェックエンドポイント"""
    return {
        "status": "healthy",
        "supabase_initialized": supabase is not None,
        "db_setup_available": DB_SETUP_AVAILABLE,
        "sheets_sync_available": SHEETS_SYNC_AVAILABLE
    }


@app.get("/check-connection")
async def check_connection():
    """データベース接続確認エンドポイント"""
    try:
        # プラットフォーム情報の取得テスト
        platform_result = supabase.table("platform").select("*").execute()
        
        # orders テーブルのカウント
        orders_result = supabase.table("orders").select("count").execute()
        
        # order_items テーブルのカウント
        items_result = supabase.table("order_items").select("count").execute()
        
        return {
            "status": "connected",
            "platform": platform_result.data,
            "orders_count": orders_result.data,
            "items_count": items_result.data
        }
    except Exception as e:
        logger.error(f"Connection check failed: {str(e)}")
        return {"status": "error", "message": str(e)}


@app.get("/check-data")
async def check_data():
    """データ保存状況を確認するエンドポイント"""
    try:
        # 最新の注文を確認
        orders_response = supabase.table("orders").select("*").order('order_date', desc=True).limit(5).execute()
        
        # 最新の注文商品を確認
        items_response = supabase.table("order_items").select("*").order('updated_at', desc=True).limit(5).execute()
        
        return {
            "latest_orders": orders_response.data,
            "latest_items": items_response.data
        }
    except Exception as e:
        logger.error(f"Error checking data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sync-orders")
async def sync_orders(days: int = 1):
    """指定日数分の注文データを同期"""
    try:
        rakuten_api = RakutenAPI()
        end_date = datetime.now(pytz.UTC)
        start_date = end_date - timedelta(days=days)

        logger.info(f"Starting order sync from {start_date} to {end_date}")

        # 注文データの取得
        orders = await rakuten_api.get_orders(start_date, end_date)
        
        if orders:
            # Supabaseへの保存
            result = await rakuten_api.save_to_supabase(orders)
            
            # 新規注文の在庫処理（追加機能）
            try:
                rakuten_connector = RakutenConnector()
                # 保存した注文のIDを特定
                order_numbers = [order.get("orderNumber") for order in orders]
                saved_orders = supabase.table("orders").select("id").in_("order_number", order_numbers).execute()
                
                for order in saved_orders.data:
                    order_id = order.get("id")
                    if order_id:
                        await rakuten_connector.process_order_inventory(order_id)
                        logger.info(f"在庫処理完了: 注文ID {order_id}")
            except Exception as e:
                logger.error(f"在庫処理エラー: {str(e)}")
            
            logger.info(f"Successfully synced {len(orders)} orders")
            return {
                "status": "success",
                "message": f"Synced orders from {start_date} to {end_date}",
                "order_count": len(orders),
                "sync_result": result
            }
        else:
            logger.info("No orders found for the specified period")
            return {
                "status": "success",
                "message": "No orders found for the specified period",
                "order_count": 0
            }

    except Exception as e:
        logger.error(f"Error in sync_orders: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sync-orders-range")
async def sync_orders_range(start_date: str, end_date: str):
    """指定期間の注文データを同期するエンドポイント"""
    try:
        rakuten_api = RakutenAPI()
        
        # 文字列をdatetimeオブジェクトに変換
        start = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=pytz.UTC)
        end = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59, tzinfo=pytz.UTC)

        logger.info(f"Starting order sync from {start} to {end}")

        # 注文データの取得
        orders = await rakuten_api.get_orders(start, end)
        
        if orders:
            result = await rakuten_api.save_to_supabase(orders)
            
            # 新規注文の在庫処理（追加機能）
            try:
                rakuten_connector = RakutenConnector()
                # 保存した注文のIDを特定
                order_numbers = [order.get("orderNumber") for order in orders]
                saved_orders = supabase.table("orders").select("id").in_("order_number", order_numbers).execute()
                
                for order in saved_orders.data:
                    order_id = order.get("id")
                    if order_id:
                        await rakuten_connector.process_order_inventory(order_id)
                        logger.info(f"在庫処理完了: 注文ID {order_id}")
            except Exception as e:
                logger.error(f"在庫処理エラー: {str(e)}")
            
            logger.info(f"Successfully synced {len(orders)} orders")
            return {
                "status": "success",
                "message": f"Synced orders from {start_date} to {end_date}",
                "order_count": len(orders),
                "sync_result": result
            }
        else:
            logger.info("No orders found for the specified period")
            return {
                "status": "success",
                "message": "No orders found for the specified period",
                "order_count": 0
            }

    except ValueError as e:
        logger.error(f"Invalid date format: {str(e)}")
        raise HTTPException(
            status_code=400, 
            detail="Invalid date format. Please use YYYY-MM-DD format."
        )
    except Exception as e:
        logger.error(f"Error in sync_orders_range: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/debug-order-structure")
async def debug_order_structure():
    """楽天APIの注文データ構造を確認"""
    try:
        rakuten_api = RakutenAPI()
        # 本日の注文を1件だけ取得してみる
        end_date = datetime.now(pytz.UTC)
        start_date = end_date - timedelta(days=1)
        
        orders = await rakuten_api.get_orders(start_date, end_date)
        if orders:
            first_order = orders[0]
            return {
                "available_fields": list(first_order.keys()),
                "sample_data": first_order,
                "order_items_sample": first_order.get("OrderItems", [])[0] if first_order.get("OrderItems") else None
            }
        return {"message": "No orders found"}
    except Exception as e:
        logger.error(f"Debug error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/extract-product-prefixes")
async def extract_product_prefixes():
    """注文商品から商品コードプレフィックスを抽出して表示"""
    try:
        items_result = supabase.table("order_items").select("product_name").execute()
        
        if not items_result.data:
            return {"message": "No items found"}
        
        prefixes = {}
        for item in items_result.data:
            product_name = item.get("product_name", "")
            prefix = extract_product_code_prefix(product_name)
            if prefix:
                if prefix not in prefixes:
                    prefixes[prefix] = []
                if product_name not in prefixes[prefix]:
                    prefixes[prefix].append(product_name)
        
        return {
            "total_items": len(items_result.data),
            "items_with_prefix": sum(len(items) for items in prefixes.values()),
            "unique_prefixes": len(prefixes),
            "prefix_details": prefixes
        }
    except Exception as e:
        logger.error(f"Error extracting product prefixes: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/debug-database")
async def debug_database():
    """データベースの状態を確認"""
    try:
        orders_result = supabase.table("orders").select("*").order('created_at', desc=True).limit(1).execute()
        items_result = supabase.table("order_items").select("*").order('created_at', desc=True).limit(1).execute()
        
        # テーブルごとの件数を取得
        counts = {
            "orders_count": len(supabase.table("orders").select("id").execute().data),
            "items_count": len(supabase.table("order_items").select("id").execute().data),
            "platform_count": len(supabase.table("platform").select("id").execute().data)
        }
        
        # 在庫管理テーブルのデータも確認
        inventory_count = 0
        stock_movements_count = 0
        sales_daily_count = 0
        
        try:
            inventory_count = len(supabase.table("inventory").select("id").limit(1).execute().data)
            stock_movements_count = len(supabase.table("stock_movements").select("id").limit(1).execute().data)
            sales_daily_count = len(supabase.table("sales_daily").select("id").limit(1).execute().data)
        except:
            pass
        
        counts.update({
            "inventory_count": inventory_count,
            "stock_movements_count": stock_movements_count,
            "sales_daily_count": sales_daily_count
        })
        
        return {
            "counts": counts,
            "latest_order": orders_result.data[0] if orders_result.data else None,
            "latest_item": items_result.data[0] if items_result.data else None
        }
    except Exception as e:
        logger.error(f"Database debug error: {str(e)}")
        return {"error": str(e)}

#################################################
# 在庫・売上管理用の新しいエンドポイント
#################################################

@app.post("/initialize-inventory/rakuten")
async def initialize_inventory_rakuten(initial_stock: int = 0):
    """
    楽天の商品データを在庫テーブルに初期化する
    """
    try:
        connector = RakutenConnector()
        items_data = await connector.extract_inventory_items()
        inventory_items = items_data.get("inventory_items", [])
        
        if not inventory_items:
            return {"message": "楽天から登録可能な商品がありません"}
        
        # 既存の在庫データを取得
        existing_inventory = supabase.table("inventory").select("product_code", "platform_id").eq(
            "platform_id", await connector.initialize()
        ).execute()
        
        existing_keys = {(item["product_code"], item["platform_id"]) for item in existing_inventory.data}
        
        # 新規登録する商品データを準備
        new_inventory_items = []
        for item in inventory_items:
            if (item["product_code"], item["platform_id"]) not in existing_keys:
                new_inventory_items.append({
                    "product_code": item["product_code"],
                    "product_name": item["product_name"],
                    "platform_id": item["platform_id"],
                    "platform_product_id": item.get("platform_product_id", ""),
                    "merchant_item_id": item.get("merchant_item_id", ""),
                    "item_number": item.get("item_number", ""),
                    "variant_id": item.get("variant_id", ""),
                    "current_stock": initial_stock,
                    "minimum_stock": 0,
                    "is_active": True,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat()
                })
        
        # バッチ処理で登録
        batch_size = 100
        results = []
        
        for i in range(0, len(new_inventory_items), batch_size):
            batch = new_inventory_items[i:i+batch_size]
            if batch:
                result = supabase.table("inventory").insert(batch).execute()
                results.append(result)
        
        return {
            "message": f"{len(new_inventory_items)}件の商品を在庫テーブルに登録しました",
            "platform": "rakuten",
            "existing_items": len(existing_keys),
            "new_items": len(new_inventory_items),
            "total_items": len(inventory_items)
        }
        
    except Exception as e:
        logger.error(f"在庫初期化エラー: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/process-order-inventory/{order_id}")
async def process_order_inventory_endpoint(order_id: int):
    """注文の在庫処理を行うエンドポイント"""
    try:
        connector = RakutenConnector()
        result = await connector.process_order_inventory(order_id)
        return result
    except Exception as e:
        logger.error(f"注文処理エラー: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/update-sales-rakuten")
async def update_sales_rakuten(days: int = 7):
    """
    指定日数分の注文データから売上情報を集計・更新する
    """
    try:
        connector = RakutenConnector()
        result = await connector.update_sales_data(days)
        return result
    except Exception as e:
        logger.error(f"売上更新エラー: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/inventory-dashboard")
async def inventory_dashboard(low_stock_threshold: int = 5):
    """
    在庫状況ダッシュボードのデータを提供
    """
    try:
        # 在庫データを取得
        inventory_result = supabase.table("inventory").select("*").execute()
        
        if not inventory_result.data:
            return {"message": "在庫データがありません"}
        
        # プラットフォーム情報を取得
        platform_result = supabase.table("platform").select("id", "platform_code", "name").execute()
        platform = {p["id"]: {"code": p.get("platform_code", ""), "name": p["name"]} for p in platform_result.data}
        
        # 在庫状況を分析
        total_products = len(inventory_result.data)
        active_products = sum(1 for item in inventory_result.data if item["is_active"])
        
        # 在庫切れ商品
        out_of_stock = [
            {**item, "platform": platform.get(item["platform_id"], {"name": "不明"})}
            for item in inventory_result.data 
            if item["current_stock"] <= 0 and item["is_active"]
        ]
        
        # 在庫が少ない商品
        low_stock = [
            {**item, "platform": platform.get(item["platform_id"], {"name": "不明"})}
            for item in inventory_result.data 
            if 0 < item["current_stock"] <= low_stock_threshold and item["is_active"]
        ]
        
        # 商品コードプレフィックスごとの集計
        prefix_summary = {}
        for item in inventory_result.data:
            code = item["product_code"]
            # 商品コードの最初の1〜3文字をプレフィックスとして使用
            prefix = code[:1] if len(code) >= 1 else ""
            if len(code) >= 3 and code[:1].isalpha() and code[1:3].isdigit():
                prefix