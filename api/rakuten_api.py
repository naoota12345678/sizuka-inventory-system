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

                    # 注文データの保存（重複チェック付き）
                    # 既存注文をチェック
                    existing = supabase.table("orders").select("id").eq("order_number", order_data["order_number"]).execute()
                    
                    if existing.data:
                        # 既存の注文があれば更新
                        order_result = supabase.table("orders").update(order_data).eq("order_number", order_data["order_number"]).execute()
                    else:
                        # 新規注文として挿入
                        order_result = supabase.table("orders").insert(order_data).execute()

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
        """注文データを準備（現在のスキーマに合わせて調整）"""
        # 現在のordersテーブルのスキーマに合わせる
        # カラム: id, platform_id, order_number, order_date, total_amount, status, created_at
        return {
            "platform_id": platform_id,
            "order_number": order["orderNumber"],
            "order_date": order.get("orderDatetime") or order.get("shopOrderCfmDatetime"),
            "total_amount": float(order.get("totalPrice", 0)),
            "status": "completed",  # 楽天から取得したデータは基本的に完了済み
            "created_at": datetime.now(timezone.utc).isoformat()
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
        """商品データを準備（現在のスキーマに合わせて調整）"""
        # 現在のorder_itemsテーブルのスキーマに合わせる
        # カラム: id, order_id, product_code, product_name, quantity, price, created_at
        
        item_name = item.get("itemName", "")
        quantity = int(item.get("units", 0))
        unit_price = float(item.get("price", 0))
        
        return {
            "order_id": order_id,
            "product_code": str(item.get("itemId", "")),
            "product_name": item_name,
            "quantity": quantity,
            "price": unit_price,  # order_itemsテーブルではpriceカラム（単価）
            "created_at": datetime.now(timezone.utc).isoformat()
        }

    def _save_parent_and_children(self, parent_item: Dict, order_id: int, order_number: str) -> int:
        """親商品とその子商品を保存（現在のスキーマに合わせて調整）"""
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
            
            child_item_data = {
                "order_id": order_id,
                "product_code": str(child_item.get("itemId", "")),
                "product_name": child_name,
                "quantity": int(parent_item.get("units", 0)),  # 親商品と同じ数量
                "price": 0,  # 個別価格は通常表示されない
                "created_at": datetime.now(timezone.utc).isoformat()
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