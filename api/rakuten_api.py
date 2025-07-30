#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
楽天API処理モジュール
注文データの取得と保存
"""

import base64
import json
import logging
import time
import traceback
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional

import httpx
import pytz
from fastapi import HTTPException

from core.config import Config
from core.database import supabase
from core.utils import extract_product_code_prefix, extract_sku_data, extract_selected_choices

logger = logging.getLogger(__name__)

class RakutenAPI:
    """楽天APIクライアント"""
    
    def __init__(self):
        self.service_secret = Config.RAKUTEN_SERVICE_SECRET
        self.license_key = Config.RAKUTEN_LICENSE_KEY
        
        if not self.service_secret or not self.license_key:
            raise ValueError("楽天API認証情報が設定されていません")
        
        # 認証ヘッダーの生成
        auth_string = f"{self.service_secret}:{self.license_key}"
        encoded_auth = base64.b64encode(auth_string.encode('utf-8')).decode('utf-8')
        
        self.headers = {
            'Authorization': f'ESA {encoded_auth}',
            'Content-Type': 'application/json; charset=utf-8'
        }
        self.jst = pytz.timezone('Asia/Tokyo')
        self.base_url = 'https://api.rms.rakuten.co.jp/es/2.0'

    def get_orders(self, start_date: datetime, end_date: datetime) -> List[Dict]:
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
            with httpx.Client() as client:
                response = client.post(
                    url,
                    headers=self.headers,
                    json=search_data,
                    timeout=30.0
                )

                if response.status_code == 401:
                    raise HTTPException(status_code=401, detail=f"認証に失敗しました: {response.text}")

                response.raise_for_status()
                data = response.json()
                order_numbers = data.get('orderNumberList', [])

                if order_numbers:
                    return self.get_order_details(order_numbers)
                return []

        except Exception as e:
            logger.error(f"注文取得エラー: {str(e)}")
            raise

    def get_order_details(self, order_numbers: List[str]) -> List[Dict]:
        """注文の詳細情報を取得"""
        url = f'{self.base_url}/purchaseItem/getOrderItem/'
        chunk_size = 100
        all_orders = []
        
        for i in range(0, len(order_numbers), chunk_size):
            chunk = order_numbers[i:i + chunk_size]
            order_data = {'orderNumberList': chunk}
            
            try:
                with httpx.Client() as client:
                    logger.info(f"注文詳細を取得中: {i+1} から {i+len(chunk)} 件目")
                    
                    response = client.post(
                        url,
                        headers=self.headers,
                        json=order_data,
                        timeout=30.0
                    )
                    
                    if response.status_code == 401:
                        raise HTTPException(status_code=401, detail="認証に失敗しました")
                    
                    response.raise_for_status()
                    data = response.json()
                    
                    if 'OrderModelList' in data:
                        all_orders.extend(data['OrderModelList'])
                    
            except Exception as e:
                logger.error(f"チャンク {i//chunk_size + 1} の詳細取得エラー: {str(e)}")
                continue
        
        return all_orders

    def save_to_supabase(self, orders: List[Dict]) -> Dict[str, Any]:
        """注文データをSupabaseに保存"""
        MAX_RETRIES = 3
        RETRY_DELAY = 1
        
        if not supabase:
            raise ValueError("Supabaseクライアントが初期化されていません")
        
        try:
            # 楽天のplatform_idを取得
            platform_response = self._get_platform_id_with_retry()
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
                    logger.warning(f"無効または重複した注文をスキップ: {order_number}")
                    continue
                    
                processed_orders.add(order_number)
                
                try:
                    # 注文データの準備
                    order_data = self._prepare_order_data(order, rakuten_platform_id)

                    # 注文データの保存
                    order_result = supabase.table("orders").upsert(
                        order_data,
                        on_conflict="platform_id,order_number"
                    ).execute()

                    if not order_result.data:
                        raise Exception(f"注文の保存に失敗: {order_number}")

                    order_id = order_result.data[0]["id"]
                    logger.info(f"注文 {order_number} を保存しました (ID: {order_id})")

                    # 注文商品情報の保存
                    items_count = self._save_order_items(order, order_id)
                    items_success += items_count['success']
                    items_error += items_count['error']

                    success_count += 1
                    
                except Exception as e:
                    logger.error(f"注文 {order_number} の処理エラー: {str(e)}")
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

            logger.info(f"同期完了: {json.dumps(result, indent=2)}")
            return result

        except Exception as e:
            logger.error(f"save_to_supabaseで重大なエラー: {str(e)}")
            raise

    def _prepare_order_data(self, order: Dict, platform_id: int) -> Dict:
        """注文データを準備"""
        return {
            "platform_id": platform_id,
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

    def _save_order_items(self, order: Dict, order_id: int) -> Dict[str, int]:
        """注文商品を保存"""
        items = []
        for package in order.get("PackageModelList", []):
            items.extend(package.get("ItemModelList", []))
        
        if not items:
            logger.warning(f"注文に商品が見つかりません: {order.get('orderNumber')}")
            return {"success": 0, "error": 0}

        success_count = 0
        error_count = 0
        MAX_RETRIES = 3

        for item in items:
            for attempt in range(MAX_RETRIES):
                try:
                    # 商品データの処理
                    is_parent = item.get("itemType") == 1
                    
                    if is_parent:
                        # 親商品とその子商品を保存
                        saved = self._save_parent_and_children(item, order_id, order.get('orderNumber'))
                        success_count += saved
                    else:
                        # 通常商品を保存
                        item_data = self._prepare_item_data(item, order_id, is_parent=False)
                        
                        # 商品データの保存
                        item_result = supabase.table("order_items").insert(item_data).execute()
                        
                        if not item_result.data:
                            raise Exception(f"商品データの保存に失敗: {item_data['product_code']}")
                        
                        logger.info(f"商品 {item_data['product_code']} を保存しました")
                        success_count += 1
                        
                    break

                except Exception as e:
                    error_msg = str(e)
                    logger.error(f"[DEBUG] 商品保存エラー: {error_msg}")
                    logger.error(f"[DEBUG] スタックトレース: {traceback.format_exc()}")
                    
                    if attempt < MAX_RETRIES - 1:
                        logger.warning(f"リトライ中... 試行 {attempt + 1}/{MAX_RETRIES}")
                        time.sleep(1)
                    else:
                        error_count += 1
                        logger.error(f"すべてのリトライに失敗しました")

        return {"success": success_count, "error": error_count}

    def _prepare_item_data(self, item: Dict, order_id: int, is_parent: bool = False, is_child: bool = False, parent_product_code: str = "") -> Dict:
        """商品データを準備"""
        # SKU情報の処理
        sku_models = item.get("SkuModelList", [])
        sku_info = {
            "variantId": sku_models[0].get("variantId") if sku_models else None,
            "merchantDefinedSkuId": sku_models[0].get("merchantDefinedSkuId") if sku_models else None,
            "skuInfo": sku_models[0].get("skuInfo") if sku_models else None
        }
        
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

        return {
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
            "is_parent": is_parent,
            "is_child": is_child,
            "parent_product_code": parent_product_code,
            "product_code_prefix": product_code_prefix,
            "merchant_item_id": merchant_item_id,
            "item_number": item_number,
            "variant_id": variant_id,
            "item_choice": json.dumps(choices) if choices else None,
            "selected_choice_raw": selected_choice,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }

    def _save_parent_and_children(self, parent_item: Dict, order_id: int, order_number: str) -> int:
        """親商品とその子商品を保存"""
        saved_count = 0
        
        # 親商品のデータを保存
        parent_data = self._prepare_item_data(parent_item, order_id, is_parent=True)
        parent_result = supabase.table("order_items").insert(parent_data).execute()
        
        if not parent_result.data:
            raise Exception(f"親商品の保存に失敗: {parent_data['product_code']}")
        
        logger.info(f"親商品 {parent_data['product_code']} を保存しました (注文: {order_number})")
        saved_count += 1
        
        # selectedItemsから子商品情報を抽出
        selected_items = parent_item.get("selectedItems", [])
        for child_item in selected_items:
            child_name = child_item.get("itemName", "")
            child_prefix = extract_product_code_prefix(child_name)
            
            child_item_data = {
                "order_id": order_id,
                "product_code": str(child_item.get("itemId", "")),
                "product_name": child_name,
                "quantity": int(parent_item.get("units", 0)),  # 親商品と同じ数量
                "unit_price": 0,  # 個別価格は通常表示されない
                "total_price": 0,
                "point_rate": 0,
                "tax_rate": 0,
                "sku_info": None,
                "deal_flag": False,
                "restore_inventory_flag": False,
                "is_parent": False,
                "is_child": True,
                "parent_product_code": str(parent_item.get("itemId", "")),
                "product_code_prefix": child_prefix,
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
                raise Exception(f"子商品の保存に失敗: {child_item_data['product_code']}")
            
            logger.info(f"子商品 {child_item_data['product_code']} を保存しました (注文: {order_number})")
            saved_count += 1
        
        return saved_count

    def _get_platform_id_with_retry(self, max_retries=3, delay=1):
        """Platform IDの取得（リトライ機能付き）"""
        if not supabase:
            raise ValueError("Supabaseクライアントが初期化されていません")
        
        for attempt in range(max_retries):
            try:
                response = supabase.table("platform").select("id").eq("platform_code", "rakuten").execute()
                if response.data:
                    return response
                raise ValueError("プラットフォーム 'rakuten' が見つかりません")
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                time.sleep(delay)