#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Enhanced Rakuten API with Return/Refund Status Handling
楽天API拡張版 - 返品・返金ステータス対応

既存のAPIロジックを拡張して、実際の注文ステータスを正しく処理
安全性重視：既存機能を破壊せず、新機能を追加
"""

import httpx
import pytz
import base64
import os
import logging
from datetime import datetime, timezone
from typing import List, Dict, Optional
from fastapi import HTTPException

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnhancedRakutenAPI:
    """
    拡張版楽天API
    返品・キャンセルステータスを正しく処理
    """
    
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
        
        # ステータスマッピング
        self.status_mapping = {
            100: 'confirmed',      # 注文確定
            200: 'paid',          # 決済確認
            300: 'preparing',     # 発送準備
            400: 'shipped',       # 発送済み
            500: 'delivered',     # 配送完了
            600: 'cancelled',     # キャンセル
            700: 'returned'       # 返品・返金
        }
    
    async def get_orders_with_status(self, start_date: datetime, end_date: datetime, include_returns: bool = True) -> List[Dict]:
        """
        注文データの検索（ステータス別処理対応）
        
        Args:
            start_date: 検索開始日時
            end_date: 検索終了日時  
            include_returns: 返品・キャンセルを含むかどうか
        """
        url = f'{self.base_url}/purchaseItem/searchOrderItem/'
        
        jst_st = start_date.astimezone(self.jst).strftime("%Y-%m-%dT%H:%M:%S+0900")
        jst_ed = end_date.astimezone(self.jst).strftime("%Y-%m-%dT%H:%M:%S+0900")

        # ステータス指定
        if include_returns:
            # 全ステータス（返品・キャンセル含む）
            order_progress_list = [100, 200, 300, 400, 500, 600, 700]
        else:
            # 通常注文のみ（既存動作）
            order_progress_list = [100, 200, 300, 400, 500]

        search_data = {
            "dateType": 1,
            "startDatetime": jst_st,
            "endDatetime": jst_ed,
            "orderProgressList": order_progress_list,
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
                    return await self.get_order_details_with_status(order_numbers)
                return []

        except Exception as e:
            logger.error(f"Error in get_orders_with_status: {str(e)}")
            raise
    
    async def get_order_details_with_status(self, order_numbers: List[str]) -> List[Dict]:
        """
        注文の詳細情報を取得（ステータス情報付き）
        """
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
                        for order in data['OrderModelList']:
                            processed_order = self.process_order_with_status(order)
                            all_orders.append(processed_order)
                    
            except Exception as e:
                logger.error(f"Error getting order details for chunk {i}: {str(e)}")
                continue
        
        logger.info(f"Retrieved {len(all_orders)} orders with status information")
        return all_orders
    
    def process_order_with_status(self, order: Dict) -> Dict:
        """
        注文データを処理（実際のステータス情報を保持）
        """
        try:
            # 実際のステータスを取得
            order_progress = order.get('orderProgress', 100)
            actual_status = self.status_mapping.get(order_progress, 'unknown')
            
            # 注文情報の基本処理
            platform_id = f"rakuten_{order['orderNumber']}"
            
            # 返品・キャンセルの場合の特別処理
            is_return_or_cancel = order_progress in [600, 700]
            
            processed_order = {
                "platform_id": platform_id,
                "order_number": order["orderNumber"],
                "order_date": order.get("orderDatetime") or order.get("shopOrderCfmDatetime"),
                "total_amount": float(order.get("totalPrice", 0)),
                "status": actual_status,  # 実際のステータスを設定
                "order_progress": order_progress,  # 数値ステータスも保持
                "is_return_or_cancel": is_return_or_cancel,
                "created_at": datetime.now(timezone.utc).isoformat(),
                
                # 返品・キャンセル特有の情報
                "return_date": order.get("returnDatetime") if is_return_or_cancel else None,
                "cancel_date": order.get("cancelDatetime") if is_return_or_cancel else None,
                "return_reason": order.get("returnReason", "") if is_return_or_cancel else None,
                
                # 既存フィールド（互換性維持）
                "customer_name": order.get("buyerName", ""),
                "shipping_fee": float(order.get("shippingFee", 0)),
                "coupon_amount": float(order.get("couponAllTotalPrice", 0)),
                "point_amount": float(order.get("PointModel", {}).get("usedPoint", 0)),
                "request_price": float(order.get("requestPrice", 0)),
                "deal_price": float(order.get("goodsPrice", 0)),
                "payment_method": order.get("PaymentModel", {}).get("paymentName", ""),
                
                # 完全なAPIレスポンスを保存（デバッグ・拡張用）
                "platform_data": order
            }
            
            # 注文アイテムの処理
            order_items = []
            if 'PurchaseItemModelList' in order:
                for item in order['PurchaseItemModelList']:
                    processed_item = self.process_order_item_with_status(item, order_progress, platform_id)
                    order_items.append(processed_item)
            
            processed_order["items"] = order_items
            
            return processed_order
            
        except Exception as e:
            logger.error(f"Error processing order {order.get('orderNumber', 'unknown')}: {str(e)}")
            return {}
    
    def process_order_item_with_status(self, item: Dict, order_progress: int, platform_id: str) -> Dict:
        """
        注文アイテムを処理（ステータス考慮）
        """
        try:
            # 返品・キャンセルの場合は数量を負の値で記録する場合もある
            # ただし、楽天APIの仕様により実装が異なる可能性があるため、
            # まずは正の値で記録し、transaction_typeで区別
            quantity = item.get("purchaseQuantity", 1)
            
            # 返品・キャンセルの場合のトランザクション種別
            if order_progress == 600:  # キャンセル
                transaction_type = 'cancel'
            elif order_progress == 700:  # 返品
                transaction_type = 'return'
            else:
                transaction_type = 'sale'
            
            processed_item = {
                "platform_id": platform_id,
                "order_number": item.get("orderNumber", ""),
                "product_code": item.get("productCode", ""),
                "product_name": item.get("productName", ""),
                "rakuten_item_number": item.get("rakutenItemCode", ""),
                "price": float(item.get("price", 0)),
                "quantity": quantity,
                "transaction_type": transaction_type,  # 新規フィールド
                "order_progress": order_progress,      # ステータス情報
                
                # 返品・キャンセル特有の情報
                "is_returned": order_progress == 700,
                "is_cancelled": order_progress == 600,
                
                # 選択肢情報（既存ロジック）
                "choice_code": self.extract_choice_code(item),
                "choice_info": item.get("choiceInfo", ""),
                
                # 拡張データ（デバッグ・分析用）
                "extended_rakuten_data": {
                    "original_price": float(item.get("originalPrice", 0)),
                    "discount_price": float(item.get("discountPrice", 0)),
                    "deal_flag": item.get("dealFlag", False),
                    "point_rate": float(item.get("pointRate", 0)),
                    "transaction_type": transaction_type,
                    "order_status": order_progress,
                    "raw_item_data": item  # 完全なアイテムデータ
                },
                
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            return processed_item
            
        except Exception as e:
            logger.error(f"Error processing order item: {str(e)}")
            return {}
    
    def extract_choice_code(self, item: Dict) -> str:
        """
        選択肢コードの抽出（既存ロジック）
        """
        choice_info = item.get('choiceInfo', '')
        if choice_info:
            # L01, R05, N03 などの形式を検索
            import re
            match = re.search(r'\b([A-Z]\d{2})\b', choice_info)
            if match:
                return match.group(1)
        return ""
    
    async def get_return_orders_only(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """
        返品・キャンセル注文のみを取得
        """
        url = f'{self.base_url}/purchaseItem/searchOrderItem/'
        
        jst_st = start_date.astimezone(self.jst).strftime("%Y-%m-%dT%H:%M:%S+0900")
        jst_ed = end_date.astimezone(self.jst).strftime("%Y-%m-%dT%H:%M:%S+0900")

        search_data = {
            "dateType": 1,
            "startDatetime": jst_st,
            "endDatetime": jst_ed,
            "orderProgressList": [600, 700],  # キャンセル・返品のみ
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

                response.raise_for_status()
                data = response.json()
                order_numbers = data.get('orderNumberList', [])

                if order_numbers:
                    return await self.get_order_details_with_status(order_numbers)
                return []

        except Exception as e:
            logger.error(f"Error in get_return_orders_only: {str(e)}")
            raise
    
    def get_status_summary(self, orders: List[Dict]) -> Dict:
        """
        注文ステータスの統計情報を取得
        """
        status_counts = {}
        total_orders = len(orders)
        
        for order in orders:
            status = order.get('status', 'unknown')
            status_counts[status] = status_counts.get(status, 0) + 1
        
        return {
            'total_orders': total_orders,
            'status_breakdown': status_counts,
            'return_orders': status_counts.get('returned', 0),
            'cancelled_orders': status_counts.get('cancelled', 0),
            'completed_orders': status_counts.get('delivered', 0) + status_counts.get('shipped', 0),
            'return_rate': (status_counts.get('returned', 0) / total_orders * 100) if total_orders > 0 else 0,
            'cancellation_rate': (status_counts.get('cancelled', 0) / total_orders * 100) if total_orders > 0 else 0
        }

# 既存APIとの互換性を保つラッパー関数
async def get_orders_enhanced(start_date: datetime, end_date: datetime, include_returns: bool = False) -> List[Dict]:
    """
    既存のAPIコールを拡張版で置き換える互換関数
    """
    api = EnhancedRakutenAPI()
    return await api.get_orders_with_status(start_date, end_date, include_returns)

async def get_return_orders(start_date: datetime, end_date: datetime) -> List[Dict]:
    """
    返品・キャンセル注文専用の取得関数
    """
    api = EnhancedRakutenAPI()
    return await api.get_return_orders_only(start_date, end_date)

if __name__ == "__main__":
    # テスト実行
    import asyncio
    from datetime import timedelta
    
    async def test_enhanced_api():
        api = EnhancedRakutenAPI()
        
        # 過去7日間のデータを取得（返品含む）
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        print("=== 拡張版楽天API テスト ===")
        
        try:
            # 全注文取得（返品含む）
            all_orders = await api.get_orders_with_status(start_date, end_date, include_returns=True)
            print(f"取得注文数: {len(all_orders)}件")
            
            # ステータス統計
            summary = api.get_status_summary(all_orders)
            print(f"統計情報: {summary}")
            
            # 返品のみ取得
            return_orders = await api.get_return_orders_only(start_date, end_date)
            print(f"返品・キャンセル注文: {len(return_orders)}件")
            
        except Exception as e:
            print(f"エラー: {str(e)}")
    
    # asyncio.run(test_enhanced_api())