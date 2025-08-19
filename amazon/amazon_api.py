#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Amazon SP-API連携モジュール
注文データの取得と同期
"""

import os
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
from supabase import create_client
import time

# ロギング設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Supabase接続情報
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://equrcpeifogdrxoldkpe.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ")

# Amazon SP-API認証情報（環境変数から取得）
AMAZON_REFRESH_TOKEN = os.environ.get("AMAZON_REFRESH_TOKEN")
AMAZON_CLIENT_ID = os.environ.get("AMAZON_CLIENT_ID")
AMAZON_CLIENT_SECRET = os.environ.get("AMAZON_CLIENT_SECRET")
AMAZON_AWS_ACCESS_KEY = os.environ.get("AMAZON_AWS_ACCESS_KEY")
AMAZON_AWS_SECRET_KEY = os.environ.get("AMAZON_AWS_SECRET_KEY")
AMAZON_ROLE_ARN = os.environ.get("AMAZON_ROLE_ARN")
AMAZON_MARKETPLACE_ID = os.environ.get("AMAZON_MARKETPLACE_ID", "A1VC38T7YXB528")  # 日本

class AmazonAPI:
    """Amazon SP-API連携クラス"""
    
    def __init__(self):
        """初期化"""
        self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        self.marketplace_id = AMAZON_MARKETPLACE_ID
        
        # SP-APIクライアント初期化（実際の実装時にはpython-amazon-sp-apiライブラリを使用）
        # pip install python-amazon-sp-api が必要
        self.access_token = None
        self.token_expires_at = None
        
    def _get_access_token(self) -> str:
        """アクセストークンを取得（実装簡略化）"""
        # 実際にはLWAトークンエンドポイントにリクエストを送信
        # ここでは簡略化のため固定値を返す
        return "dummy_access_token"
        
    def fetch_orders(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """
        指定期間の注文を取得
        
        Args:
            start_date: 開始日時
            end_date: 終了日時
            
        Returns:
            注文データのリスト
        """
        logger.info(f"Fetching orders from {start_date} to {end_date}")
        
        # 実際のSP-API実装では以下のようになる
        # from sp_api.api import Orders
        # orders_api = Orders(credentials=self.credentials, marketplace=self.marketplace_id)
        # response = orders_api.get_orders(
        #     CreatedAfter=start_date.isoformat(),
        #     CreatedBefore=end_date.isoformat()
        # )
        
        # ダミーデータを返す（開発用）
        dummy_orders = [
            {
                "AmazonOrderId": "111-1234567-1234567",
                "PurchaseDate": start_date.isoformat(),
                "OrderStatus": "Shipped",
                "FulfillmentChannel": "AFN",  # Amazon Fulfilled
                "OrderTotal": {
                    "CurrencyCode": "JPY",
                    "Amount": "5980.00"
                },
                "BuyerEmail": "buyer@example.com",
                "ShipServiceLevel": "Standard",
                "MarketplaceId": self.marketplace_id
            }
        ]
        
        return dummy_orders
        
    def fetch_order_items(self, order_id: str) -> List[Dict]:
        """
        注文の商品詳細を取得
        
        Args:
            order_id: Amazon注文ID
            
        Returns:
            注文商品データのリスト
        """
        logger.info(f"Fetching order items for order {order_id}")
        
        # 実際のSP-API実装
        # from sp_api.api import Orders
        # orders_api = Orders(credentials=self.credentials, marketplace=self.marketplace_id)
        # response = orders_api.get_order_items(order_id)
        
        # ダミーデータを返す（開発用）
        dummy_items = [
            {
                "OrderItemId": "12345678901234",
                "ASIN": "B08N5WRWNW",
                "SellerSKU": "ECHO-DOT-4",
                "Title": "Echo Dot (第4世代) - スマートスピーカー",
                "QuantityOrdered": 1,
                "QuantityShipped": 1,
                "ItemPrice": {
                    "CurrencyCode": "JPY",
                    "Amount": "5980.00"
                },
                "ItemTax": {
                    "CurrencyCode": "JPY",
                    "Amount": "544.00"
                },
                "PromotionDiscount": {
                    "CurrencyCode": "JPY",
                    "Amount": "0.00"
                }
            }
        ]
        
        return dummy_items
        
    def sync_orders_to_supabase(self, orders: List[Dict]) -> Dict[str, Any]:
        """
        注文データをSupabaseに同期
        
        Args:
            orders: 注文データのリスト
            
        Returns:
            同期結果
        """
        results = {
            "processed": 0,
            "created": 0,
            "updated": 0,
            "errors": []
        }
        
        for order in orders:
            try:
                # 注文データを整形
                order_data = {
                    "order_id": order.get("AmazonOrderId"),
                    "purchase_date": order.get("PurchaseDate"),
                    "order_status": order.get("OrderStatus"),
                    "fulfillment_channel": order.get("FulfillmentChannel"),
                    "ship_service_level": order.get("ShipServiceLevel"),
                    "marketplace_id": order.get("MarketplaceId"),
                    "buyer_email": order.get("BuyerEmail"),
                    "buyer_name": order.get("BuyerName"),
                    "ship_address": order.get("ShippingAddress"),
                    "order_total": float(order.get("OrderTotal", {}).get("Amount", 0)) if order.get("OrderTotal") else 0,
                    "currency_code": order.get("OrderTotal", {}).get("CurrencyCode", "JPY") if order.get("OrderTotal") else "JPY",
                    "payment_method": order.get("PaymentMethod"),
                    "is_business_order": order.get("IsBusinessOrder", False),
                    "is_prime": order.get("IsPrime", False)
                }
                
                # 既存注文をチェック
                existing = self.supabase.table("amazon_orders").select("id").eq("order_id", order_data["order_id"]).execute()
                
                if existing.data:
                    # 更新
                    result = self.supabase.table("amazon_orders").update(order_data).eq("order_id", order_data["order_id"]).execute()
                    results["updated"] += 1
                    order_db_id = existing.data[0]["id"]
                else:
                    # 新規作成
                    result = self.supabase.table("amazon_orders").insert(order_data).execute()
                    results["created"] += 1
                    order_db_id = result.data[0]["id"]
                
                # 注文商品を同期
                order_items = self.fetch_order_items(order_data["order_id"])
                self._sync_order_items(order_db_id, order_data["order_id"], order_items)
                
                results["processed"] += 1
                
            except Exception as e:
                logger.error(f"Error syncing order {order.get('AmazonOrderId')}: {str(e)}")
                results["errors"].append({
                    "order_id": order.get("AmazonOrderId"),
                    "error": str(e)
                })
                
        return results
        
    def _sync_order_items(self, order_db_id: str, amazon_order_id: str, items: List[Dict]):
        """
        注文商品をSupabaseに同期
        
        Args:
            order_db_id: SupabaseのオーダーID
            amazon_order_id: Amazon注文ID
            items: 商品データのリスト
        """
        for item in items:
            try:
                item_data = {
                    "order_id": order_db_id,
                    "amazon_order_id": amazon_order_id,
                    "order_item_id": item.get("OrderItemId"),
                    "asin": item.get("ASIN"),
                    "sku": item.get("SellerSKU"),
                    "product_name": item.get("Title"),
                    "quantity_ordered": item.get("QuantityOrdered", 0),
                    "quantity_shipped": item.get("QuantityShipped", 0),
                    "item_price": float(item.get("ItemPrice", {}).get("Amount", 0)) if item.get("ItemPrice") else 0,
                    "item_tax": float(item.get("ItemTax", {}).get("Amount", 0)) if item.get("ItemTax") else 0,
                    "shipping_price": float(item.get("ShippingPrice", {}).get("Amount", 0)) if item.get("ShippingPrice") else 0,
                    "shipping_tax": float(item.get("ShippingTax", {}).get("Amount", 0)) if item.get("ShippingTax") else 0,
                    "shipping_discount": float(item.get("ShippingDiscount", {}).get("Amount", 0)) if item.get("ShippingDiscount") else 0,
                    "promotion_discount": float(item.get("PromotionDiscount", {}).get("Amount", 0)) if item.get("PromotionDiscount") else 0,
                    "condition_id": item.get("ConditionId"),
                    "condition_note": item.get("ConditionNote"),
                    "is_gift": item.get("IsGift", False),
                    "gift_message_text": item.get("GiftMessageText"),
                    "gift_wrap_price": float(item.get("GiftWrapPrice", {}).get("Amount", 0)) if item.get("GiftWrapPrice") else 0,
                    "gift_wrap_tax": float(item.get("GiftWrapTax", {}).get("Amount", 0)) if item.get("GiftWrapTax") else 0
                }
                
                # 既存アイテムをチェック
                existing = self.supabase.table("amazon_order_items").select("id").eq("order_item_id", item_data["order_item_id"]).execute()
                
                if existing.data:
                    # 更新
                    self.supabase.table("amazon_order_items").update(item_data).eq("order_item_id", item_data["order_item_id"]).execute()
                else:
                    # 新規作成
                    self.supabase.table("amazon_order_items").insert(item_data).execute()
                    
            except Exception as e:
                logger.error(f"Error syncing order item {item.get('OrderItemId')}: {str(e)}")
                
    def sync_recent_orders(self, days_back: int = 7) -> Dict[str, Any]:
        """
        最近の注文を同期
        
        Args:
            days_back: 何日前からのデータを取得するか
            
        Returns:
            同期結果
        """
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days_back)
        
        logger.info(f"Syncing orders from {start_date} to {end_date}")
        
        # 注文を取得
        orders = self.fetch_orders(start_date, end_date)
        
        # Supabaseに同期
        results = self.sync_orders_to_supabase(orders)
        
        logger.info(f"Sync completed: {results}")
        return results
        
    def fetch_inventory(self) -> List[Dict]:
        """
        在庫情報を取得
        
        Returns:
            在庫データのリスト
        """
        logger.info("Fetching inventory data")
        
        # 実際のSP-API実装
        # from sp_api.api import Inventories
        # inventory_api = Inventories(credentials=self.credentials, marketplace=self.marketplace_id)
        # response = inventory_api.get_inventory_summaries()
        
        # ダミーデータを返す（開発用）
        dummy_inventory = [
            {
                "asin": "B08N5WRWNW",
                "fnsku": "X002ZS8DGO",
                "sellerSku": "ECHO-DOT-4",
                "productName": "Echo Dot (第4世代)",
                "condition": "NewItem",
                "totalQuantity": 50,
                "fulfillableQuantity": 45,
                "inboundWorkingQuantity": 0,
                "inboundShippedQuantity": 5,
                "inboundReceivingQuantity": 0
            }
        ]
        
        return dummy_inventory
        
    def sync_inventory_to_supabase(self, inventory_data: List[Dict]) -> Dict[str, Any]:
        """
        在庫データをSupabaseに同期
        
        Args:
            inventory_data: 在庫データのリスト
            
        Returns:
            同期結果
        """
        results = {
            "processed": 0,
            "updated": 0,
            "errors": []
        }
        
        for item in inventory_data:
            try:
                # FBA在庫データを整形
                fba_data = {
                    "sku": item.get("sellerSku"),
                    "fnsku": item.get("fnsku"),
                    "asin": item.get("asin"),
                    "product_name": item.get("productName"),
                    "condition": item.get("condition", "NewItem"),
                    "fulfillable_quantity": item.get("fulfillableQuantity", 0),
                    "total_quantity": item.get("totalQuantity", 0),
                    "inbound_working_quantity": item.get("inboundWorkingQuantity", 0),
                    "inbound_shipped_quantity": item.get("inboundShippedQuantity", 0),
                    "inbound_receiving_quantity": item.get("inboundReceivingQuantity", 0),
                    "reserved_quantity": item.get("reservedQuantity", 0),
                    "last_updated": datetime.now(timezone.utc).isoformat()
                }
                
                # 既存在庫をチェック
                existing = self.supabase.table("amazon_fba_inventory").select("id").eq("sku", fba_data["sku"]).eq("condition", fba_data["condition"]).execute()
                
                if existing.data:
                    # 更新
                    self.supabase.table("amazon_fba_inventory").update(fba_data).eq("sku", fba_data["sku"]).eq("condition", fba_data["condition"]).execute()
                else:
                    # 新規作成
                    self.supabase.table("amazon_fba_inventory").insert(fba_data).execute()
                
                results["updated"] += 1
                results["processed"] += 1
                
            except Exception as e:
                logger.error(f"Error syncing inventory for SKU {item.get('sellerSku')}: {str(e)}")
                results["errors"].append({
                    "sku": item.get("sellerSku"),
                    "error": str(e)
                })
                
        return results


def main():
    """メイン処理"""
    api = AmazonAPI()
    
    # 最近7日間の注文を同期
    order_results = api.sync_recent_orders(days_back=7)
    print(f"Order sync results: {order_results}")
    
    # 在庫情報を同期
    inventory_data = api.fetch_inventory()
    inventory_results = api.sync_inventory_to_supabase(inventory_data)
    print(f"Inventory sync results: {inventory_results}")


if __name__ == "__main__":
    main()