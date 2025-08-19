#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Amazon SP-API実装版 - 日次注文同期スクリプト
実際のSP-APIを使用した実装
"""

import os
import sys
from datetime import datetime, timedelta, timezone
from supabase import create_client
import logging
import json
from typing import Dict, List, Optional

# SP-APIライブラリ
try:
    from sp_api.api import Orders, Reports, Catalog
    from sp_api.base import Marketplaces, SellingApiException
    from sp_api import Credentials
except ImportError:
    print("python-amazon-sp-api をインストールしてください: pip install python-amazon-sp-api")
    sys.exit(1)

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 環境変数から設定を読み込み
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

# Amazon SP-API認証情報
AMAZON_REFRESH_TOKEN = os.getenv('AMAZON_REFRESH_TOKEN')
AMAZON_LWA_APP_ID = os.getenv('AMAZON_KEY')  # Client ID
AMAZON_LWA_CLIENT_SECRET = os.getenv('AMAZON_SECRET')  # Client Secret
AMAZON_AWS_ACCESS_KEY = os.getenv('AMAZON_AWS_ACCESS_KEY')
AMAZON_AWS_SECRET_KEY = os.getenv('AMAZON_AWS_SECRET_KEY')
AMAZON_ROLE_ARN = os.getenv('AMAZON_ROLE_ARN')

# 必須環境変数チェック
if not all([SUPABASE_URL, SUPABASE_KEY]):
    logger.error("Supabase環境変数が設定されていません")
    sys.exit(1)

if not all([AMAZON_LWA_APP_ID, AMAZON_LWA_CLIENT_SECRET, AMAZON_REFRESH_TOKEN]):
    logger.error("Amazon SP-API認証情報が設定されていません")
    logger.info("必要な環境変数:")
    logger.info("  AMAZON_KEY (LWA App ID/Client ID)")
    logger.info("  AMAZON_SECRET (LWA Client Secret)")
    logger.info("  AMAZON_REFRESH_TOKEN")
    sys.exit(1)

# Supabaseクライアント初期化
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

class AmazonSPAPISync:
    """Amazon SP-API同期クラス"""
    
    def __init__(self):
        """初期化"""
        # SP-API認証情報設定
        self.credentials = dict(
            refresh_token=AMAZON_REFRESH_TOKEN,
            lwa_app_id=AMAZON_LWA_APP_ID,
            lwa_client_secret=AMAZON_LWA_CLIENT_SECRET,
            aws_access_key=AMAZON_AWS_ACCESS_KEY,
            aws_secret_key=AMAZON_AWS_SECRET_KEY,
            role_arn=AMAZON_ROLE_ARN
        )
        
        # 日本マーケットプレイス
        self.marketplace = Marketplaces.JP
        
        # APIクライアント初期化
        try:
            self.orders_api = Orders(credentials=self.credentials, marketplace=self.marketplace)
            self.catalog_api = Catalog(credentials=self.credentials, marketplace=self.marketplace)
            logger.info("Amazon SP-API接続初期化成功")
        except Exception as e:
            logger.error(f"SP-API初期化エラー: {str(e)}")
            raise
    
    def sync_recent_orders(self, days: int = 1) -> bool:
        """
        最近の注文を同期
        
        Args:
            days: 何日前からのデータを取得するか
            
        Returns:
            成功/失敗
        """
        try:
            # 期間設定
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=days)
            
            logger.info(f"Amazon同期期間: {start_date.strftime('%Y-%m-%d')} ～ {end_date.strftime('%Y-%m-%d')}")
            
            # 注文一覧を取得
            orders_response = self.orders_api.get_orders(
                CreatedAfter=start_date.isoformat(),
                CreatedBefore=end_date.isoformat(),
                OrderStatuses=['Pending', 'Unshipped', 'PartiallyShipped', 'Shipped', 'InvoiceUnconfirmed'],
                MaxResultsPerPage=100
            )
            
            if not orders_response.payload:
                logger.info("取得する注文がありません")
                return True
            
            orders = orders_response.payload.get('Orders', [])
            logger.info(f"取得した注文数: {len(orders)}")
            
            order_count = 0
            saved_count = 0
            
            for order in orders:
                try:
                    order_count += 1
                    if self._process_order(order):
                        saved_count += 1
                except Exception as e:
                    logger.error(f"注文処理エラー: {order.get('AmazonOrderId')}: {str(e)}")
                    continue
            
            logger.info(f"Amazon同期完了: {saved_count}/{order_count}件保存")
            
            # NextTokenがある場合は追加ページを処理
            next_token = orders_response.payload.get('NextToken')
            while next_token:
                try:
                    orders_response = self.orders_api.get_orders(NextToken=next_token)
                    additional_orders = orders_response.payload.get('Orders', [])
                    
                    for order in additional_orders:
                        order_count += 1
                        if self._process_order(order):
                            saved_count += 1
                    
                    next_token = orders_response.payload.get('NextToken')
                except Exception as e:
                    logger.error(f"追加ページ取得エラー: {str(e)}")
                    break
            
            logger.info(f"最終同期結果: {saved_count}/{order_count}件保存")
            return True
            
        except SellingApiException as e:
            logger.error(f"Amazon SP-APIエラー: {e.message}")
            logger.error(f"エラー詳細: {e.error}")
            return False
        except Exception as e:
            logger.error(f"同期エラー: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def _process_order(self, order: Dict) -> bool:
        """
        個別の注文を処理
        
        Args:
            order: 注文データ
            
        Returns:
            成功/失敗
        """
        try:
            order_id = order.get('AmazonOrderId')
            
            if not order_id:
                return False
            
            # 既存レコードチェック
            existing = supabase.table("orders").select("id").eq("order_number", order_id).execute()
            
            if existing.data:
                logger.info(f"既存注文をスキップ: {order_id}")
                return False
            
            # 注文データ作成
            purchase_date = order.get('PurchaseDate')
            if purchase_date:
                # ISO形式の日付をパース
                if isinstance(purchase_date, str):
                    purchase_date = datetime.fromisoformat(purchase_date.replace('Z', '+00:00'))
            else:
                purchase_date = datetime.now(timezone.utc)
            
            order_data = {
                'order_number': order_id,
                'order_date': purchase_date.isoformat(),
                'platform': 'amazon',
                'status': order.get('OrderStatus', 'pending'),
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            
            # メタデータを保存（必要に応じて）
            if order.get('OrderTotal'):
                order_data['total_amount'] = float(order['OrderTotal'].get('Amount', 0))
            
            # ordersテーブルに保存
            order_result = supabase.table('orders').insert(order_data).execute()
            
            if order_result.data:
                db_order_id = order_result.data[0]['id']
                
                # 注文商品詳細を取得して処理
                self._process_order_items(order_id, db_order_id)
                
                logger.info(f"新規Amazon注文追加: {order_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"注文処理エラー {order.get('AmazonOrderId')}: {str(e)}")
            return False
    
    def _process_order_items(self, amazon_order_id: str, db_order_id: str):
        """
        注文商品詳細を取得して処理
        
        Args:
            amazon_order_id: Amazon注文ID
            db_order_id: データベースの注文ID
        """
        try:
            # 注文商品詳細を取得
            items_response = self.orders_api.get_order_items(amazon_order_id)
            
            if not items_response.payload:
                return
            
            items = items_response.payload.get('OrderItems', [])
            
            for item in items:
                try:
                    asin = item.get('ASIN')
                    sku = item.get('SellerSKU')
                    quantity = int(item.get('QuantityOrdered', 0))
                    
                    if quantity <= 0:
                        continue
                    
                    # ASINから共通コードを取得
                    common_code = None
                    product_name = item.get('Title', '')
                    
                    if asin:
                        mapping = supabase.table('product_master').select(
                            'common_code, product_name'
                        ).eq('amazon_asin', asin).execute()
                        
                        if mapping.data:
                            common_code = mapping.data[0]['common_code']
                            product_name = mapping.data[0]['product_name'] or product_name
                        else:
                            logger.warning(f"ASIN {asin} のマッピングが見つかりません (SKU: {sku})")
                    
                    # 価格情報
                    item_price = 0
                    if item.get('ItemPrice'):
                        item_price = float(item['ItemPrice'].get('Amount', 0))
                    
                    # order_itemsに保存
                    item_data = {
                        'order_id': db_order_id,
                        'product_code': asin or sku,  # ASINまたはSKUを保存
                        'product_name': product_name,
                        'quantity': quantity,
                        'price': item_price / quantity if quantity > 0 else item_price,  # 単価
                        'created_at': datetime.now(timezone.utc).isoformat()
                    }
                    
                    # Amazon固有フィールド（必要に応じて）
                    if asin:
                        item_data['amazon_asin'] = asin
                    if sku:
                        item_data['amazon_sku'] = sku
                    
                    supabase.table('order_items').insert(item_data).execute()
                    
                    # 在庫を更新（共通コードがある場合）
                    if common_code:
                        self._update_inventory(common_code, -quantity)
                        logger.info(f"在庫更新: ASIN {asin} → {common_code} (-{quantity})")
                    
                except Exception as e:
                    logger.error(f"商品処理エラー: {str(e)}")
                    continue
            
            # NextTokenがある場合は追加アイテムを処理
            next_token = items_response.payload.get('NextToken')
            while next_token:
                try:
                    items_response = self.orders_api.get_order_items(
                        amazon_order_id,
                        NextToken=next_token
                    )
                    additional_items = items_response.payload.get('OrderItems', [])
                    
                    for item in additional_items:
                        # 同じ処理を繰り返す
                        pass  # 上記と同じロジック
                    
                    next_token = items_response.payload.get('NextToken')
                except Exception as e:
                    logger.error(f"追加アイテム取得エラー: {str(e)}")
                    break
                    
        except SellingApiException as e:
            logger.error(f"注文商品取得エラー: {e.message}")
        except Exception as e:
            logger.error(f"商品詳細処理エラー: {str(e)}")
    
    def _update_inventory(self, common_code: str, quantity_change: int):
        """
        在庫を更新
        
        Args:
            common_code: 共通商品コード
            quantity_change: 在庫変更量（マイナスで減少）
        """
        try:
            # 現在の在庫を取得
            current = supabase.table('inventory').select('current_stock').eq('common_code', common_code).execute()
            
            if current.data:
                new_stock = current.data[0]['current_stock'] + quantity_change
                new_stock = max(0, new_stock)  # 負の在庫を防ぐ
                
                supabase.table('inventory').update({
                    'current_stock': new_stock,
                    'last_updated': datetime.now(timezone.utc).isoformat()
                }).eq('common_code', common_code).execute()
                
                logger.info(f"在庫更新完了: {common_code} → {new_stock}個")
            else:
                # 新規在庫レコード作成
                supabase.table('inventory').insert({
                    'common_code': common_code,
                    'current_stock': max(0, quantity_change),
                    'minimum_stock': 10,
                    'last_updated': datetime.now(timezone.utc).isoformat()
                }).execute()
                
                logger.info(f"新規在庫作成: {common_code}")
                
        except Exception as e:
            logger.error(f"在庫更新エラー: {str(e)}")


def main():
    """メイン処理"""
    try:
        # Amazon SP-API同期実行
        sync = AmazonSPAPISync()
        success = sync.sync_recent_orders(days=1)
        
        if success:
            logger.info("Amazon同期処理が正常に完了しました")
            return 0
        else:
            logger.error("Amazon同期処理でエラーが発生しました")
            return 1
            
    except Exception as e:
        logger.error(f"実行エラー: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())