#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Amazon注文データの日次同期スクリプト
GitHub Actions用（楽天と同じ仕組み）
"""

import os
import sys
from datetime import datetime, timedelta, timezone
from supabase import create_client
import logging
import requests
import json
import base64

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 環境変数から設定を読み込み
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
AMAZON_SECRET = os.getenv('AMAZON_SECRET')
AMAZON_KEY = os.getenv('AMAZON_KEY')

if not all([SUPABASE_URL, SUPABASE_KEY, AMAZON_SECRET, AMAZON_KEY]):
    logger.error("必要な環境変数が設定されていません")
    sys.exit(1)

# Supabaseクライアント初期化
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def sync_amazon_orders(days=1):
    """
    Amazon注文データを同期
    SP-API経由でデータ取得
    """
    try:
        # 期間設定
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)
        
        logger.info(f"Amazon同期期間: {start_date.strftime('%Y-%m-%d')} ～ {end_date.strftime('%Y-%m-%d')}")
        
        # Amazon SP-API認証
        # TODO: 実際のAmazon SP-API実装
        # ここでは仮の実装を示します
        
        # 認証ヘッダー作成
        headers = {
            'x-amz-access-token': AMAZON_KEY,
            'Content-Type': 'application/json'
        }
        
        # 注文一覧を取得
        orders_endpoint = 'https://sellingpartnerapi-fe.amazon.com/orders/v0/orders'
        params = {
            'MarketplaceIds': 'A1VC38T7YXB528',  # 日本
            'CreatedAfter': start_date.isoformat(),
            'CreatedBefore': end_date.isoformat()
        }
        
        # APIリクエスト（実際にはSP-APIライブラリを使用）
        # response = requests.get(orders_endpoint, headers=headers, params=params)
        
        # 仮のデータ（実際のAPI応答形式に合わせて調整）
        orders_data = {
            'orders': [
                {
                    'AmazonOrderId': '123-4567890-1234567',
                    'PurchaseDate': datetime.now(timezone.utc).isoformat(),
                    'OrderStatus': 'Shipped',
                    'OrderTotal': {'Amount': '5980', 'CurrencyCode': 'JPY'}
                }
            ]
        }
        
        # 注文を処理
        order_count = 0
        saved_count = 0
        
        for order in orders_data.get('orders', []):
            try:
                order_number = order.get('AmazonOrderId')
                
                if not order_number:
                    continue
                
                order_count += 1
                
                # 既存レコードチェック
                existing = supabase.table("orders").select("id").eq("order_number", order_number).execute()
                
                if existing.data:
                    logger.info(f"既存注文をスキップ: {order_number}")
                    continue
                
                # 注文データ作成
                order_data = {
                    'order_number': order_number,
                    'order_date': order.get('PurchaseDate'),
                    'platform': 'amazon',  # 重要: platformをamazonに
                    'status': order.get('OrderStatus', 'pending'),
                    'created_at': datetime.now(timezone.utc).isoformat()
                }
                
                # ordersテーブルに保存
                order_result = supabase.table('orders').insert(order_data).execute()
                
                if order_result.data:
                    order_id = order_result.data[0]['id']
                    
                    # 注文商品詳細を取得
                    items = get_order_items(order_number)
                    
                    for item in items:
                        process_order_item(order_id, item)
                    
                    saved_count += 1
                    logger.info(f"新規Amazon注文追加: {order_number}")
                    
            except Exception as e:
                logger.error(f"注文 {order_number} 保存エラー: {e}")
        
        logger.info(f"Amazon同期完了: {saved_count}/{order_count}件保存")
        return True
        
    except Exception as e:
        logger.error(f"Amazon同期エラー: {e}")
        import traceback
        traceback.print_exc()
        return False

def get_order_items(order_id):
    """
    注文商品詳細を取得
    """
    # 実際のSP-API実装では:
    # endpoint = f'https://sellingpartnerapi-fe.amazon.com/orders/v0/orders/{order_id}/orderItems'
    
    # 仮のデータ
    return [
        {
            'ASIN': 'B0B2R5V8BG',
            'SKU': 'AMZ-001',
            'Title': 'エゾ鹿スライスジャーキー',
            'QuantityOrdered': 2,
            'ItemPrice': {'Amount': '2990', 'CurrencyCode': 'JPY'}
        }
    ]

def process_order_item(order_id, item):
    """
    注文商品を処理して在庫を更新
    """
    try:
        asin = item.get('ASIN')
        
        # ASINから共通コードを取得
        mapping = supabase.table('product_master').select('common_code, product_name').eq('amazon_asin', asin).execute()
        
        if mapping.data:
            common_code = mapping.data[0]['common_code']
            product_name = mapping.data[0]['product_name']
        else:
            logger.warning(f"ASIN {asin} のマッピングが見つかりません")
            common_code = None
            product_name = item.get('Title', '')
        
        # order_itemsに保存
        item_data = {
            'order_id': order_id,
            'product_code': asin,  # ASINをproduct_codeとして保存
            'product_name': product_name,
            'quantity': int(item.get('QuantityOrdered', 1)),
            'price': float(item.get('ItemPrice', {}).get('Amount', 0)),
            'created_at': datetime.now(timezone.utc).isoformat()
        }
        
        supabase.table('order_items').insert(item_data).execute()
        
        # 在庫を更新（共通コードがある場合）
        if common_code:
            update_inventory(common_code, -item_data['quantity'])
            logger.info(f"在庫更新: ASIN {asin} → {common_code} (-{item_data['quantity']})")
            
    except Exception as e:
        logger.error(f"商品データ保存エラー: {e}")

def update_inventory(common_code, quantity_change):
    """
    在庫を更新
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
            
    except Exception as e:
        logger.error(f"在庫更新エラー: {str(e)}")

if __name__ == "__main__":
    # 実行
    success = sync_amazon_orders(days=1)
    
    if success:
        logger.info("Amazon同期処理が正常に完了しました")
    else:
        logger.error("Amazon同期処理でエラーが発生しました")
        sys.exit(1)