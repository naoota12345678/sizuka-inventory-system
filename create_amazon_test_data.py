#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Amazonテストデータ作成スクリプト
実際のAmazon SP-API接続前にシステムをテストするためのダミーデータを作成
"""

import os
import logging
from datetime import datetime, timezone, timedelta
from supabase import create_client
import uuid

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_amazon_test_orders():
    """Amazonテスト注文データを作成"""
    
    SUPABASE_URL = 'https://equrcpeifogdrxoldkpe.supabase.co'
    SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ'
    
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    print("=== Amazonテストデータ作成 ===")
    
    # テスト用Amazon注文データ
    test_orders = [
        {
            'amazon_order_id': '123-4567890-1234567',
            'purchase_date': '2025-08-20',
            'total_amount': 2980.00,
            'items': [
                {'asin': 'B08N5WRWNW', 'title': 'Echo Dot (4th Gen)', 'price': 1980.00, 'quantity': 1},
                {'asin': 'B07FZ8S74R', 'title': 'Fire TV Stick', 'price': 1000.00, 'quantity': 1}
            ]
        },
        {
            'amazon_order_id': '123-4567890-2345678', 
            'purchase_date': '2025-08-19',
            'total_amount': 15800.00,
            'items': [
                {'asin': 'B08C1W5N87', 'title': 'Fire HD 10 Tablet', 'price': 15800.00, 'quantity': 1}
            ]
        },
        {
            'amazon_order_id': '123-4567890-3456789',
            'purchase_date': '2025-08-18', 
            'total_amount': 4500.00,
            'items': [
                {'asin': 'B08XXXX001', 'title': 'Amazon Basics Cable', 'price': 1500.00, 'quantity': 3}
            ]
        }
    ]
    
    orders_created = 0
    items_created = 0
    
    for i, test_order in enumerate(test_orders):
        try:
            # プラットフォームIDの生成（Integer型）
            platform_id = 2  # Amazon=2 (platformテーブルで確認済み)
            
            # 既存チェック（order_numberで確認）
            existing = supabase.table('orders').select('id').eq('order_number', test_order['amazon_order_id']).execute()
            if existing.data:
                print(f"注文 {test_order['amazon_order_id']} は既に存在します")
                continue
            
            # 注文データを作成
            order_data = {
                'platform_id': platform_id,
                'order_number': test_order['amazon_order_id'],
                'order_date': f"{test_order['purchase_date']}T10:00:00+00:00",
                'total_amount': test_order['total_amount'],
                'status': 'shipped',
                'order_status': 'completed',
                'shipping_fee': 0,
                'payment_method': 'Amazon Pay',
                'coupon_amount': 0,
                'point_amount': 0,
                'request_price': test_order['total_amount'],
                'deal_price': test_order['total_amount'],
                'created_at': datetime.now(timezone.utc).isoformat(),
                
                # Amazon特有データ
                'platform_data': {
                    'platform': 'amazon',
                    'amazon_order_id': test_order['amazon_order_id'],
                    'marketplace_id': 'A1VC38T7YXB528',
                    'order_status': 'Shipped',
                    'fulfillment_channel': 'AFN',
                    'sales_channel': 'Amazon.co.jp',
                    'customer_name': 'Amazon Test Customer'
                }
            }
            
            # 注文を保存
            order_result = supabase.table('orders').insert(order_data).execute()
            
            if order_result.data:
                order_id = order_result.data[0]['id']
                orders_created += 1
                print(f"✅ 注文作成: {test_order['amazon_order_id']} (¥{test_order['total_amount']:,.0f})")
                
                # 注文商品を作成
                for item in test_order['items']:
                    item_data = {
                        'order_id': order_id,
                        'product_code': item['asin'],
                        'product_name': item['title'],
                        'quantity': item['quantity'],
                        'price': item['price'],
                        'created_at': datetime.now(timezone.utc).isoformat(),
                        
                        # Amazon特有フィールド
                        'amazon_item_data': {
                            'asin': item['asin'],
                            'seller_sku': f"SKU-{item['asin']}",
                            'condition_id': 'New',
                            'fulfillment_channel': 'AFN',
                            'is_gift': False
                        },
                        
                        'is_cancelled': False
                    }
                    
                    item_result = supabase.table('order_items').insert(item_data).execute()
                    if item_result.data:
                        items_created += 1
                        print(f"    - {item['title']}: ¥{item['price']:,.0f} x {item['quantity']}")
            
        except Exception as e:
            print(f"❌ 注文作成エラー {test_order['amazon_order_id']}: {str(e)}")
            continue
    
    print(f"\n=== 作成結果 ===")
    print(f"Amazon注文: {orders_created}件")
    print(f"商品アイテム: {items_created}件")
    print(f"総売上: ¥{sum(order['total_amount'] for order in test_orders[:orders_created]):,.0f}")
    
    if orders_created > 0:
        print(f"\n🎉 Amazonテストデータ作成完了!")
        print("売上ダッシュボードでAmazon売上を確認できます")
        return True
    else:
        print("\n⚠️ テストデータ作成に失敗しました")
        return False

def create_amazon_product_mappings():
    """Amazonテスト商品のマッピングを作成"""
    
    SUPABASE_URL = 'https://equrcpeifogdrxoldkpe.supabase.co'
    SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ'
    
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    print("\n=== Amazon商品マッピング作成 ===")
    
    # Amazon商品のマッピング
    amazon_products = [
        {'asin': 'B08N5WRWNW', 'name': 'Echo Dot (4th Gen)', 'common_code': 'AM001'},
        {'asin': 'B07FZ8S74R', 'name': 'Fire TV Stick', 'common_code': 'AM002'},
        {'asin': 'B08C1W5N87', 'name': 'Fire HD 10 Tablet', 'common_code': 'AM003'},
        {'asin': 'B08XXXX001', 'name': 'Amazon Basics Cable', 'common_code': 'AM004'}
    ]
    
    mappings_created = 0
    
    for product in amazon_products:
        try:
            # 既存チェック
            existing = supabase.table('product_master').select('id').eq('rakuten_sku', product['asin']).execute()
            if existing.data:
                print(f"マッピング {product['asin']} は既に存在します")
                continue
            
            mapping_data = {
                'rakuten_sku': product['asin'],  # ASINをrakuten_skuフィールドに保存
                'common_code': product['common_code'],
                'product_name': product['name'],
                'platform': 'amazon',
                'created_at': datetime.now(timezone.utc).isoformat(),
                'amazon_data': {
                    'asin': product['asin'],
                    'platform': 'amazon',
                    'marketplace_id': 'A1VC38T7YXB528'
                }
            }
            
            result = supabase.table('product_master').insert(mapping_data).execute()
            if result.data:
                mappings_created += 1
                print(f"✅ {product['asin']} → {product['common_code']}: {product['name']}")
            
        except Exception as e:
            print(f"❌ マッピング作成エラー {product['asin']}: {str(e)}")
            continue
    
    print(f"\nAmazon商品マッピング: {mappings_created}件作成")
    return mappings_created > 0

if __name__ == "__main__":
    print("Amazon統合テストデータ作成開始\n")
    
    # 1. テスト注文データ作成
    orders_success = create_amazon_test_orders()
    
    # 2. 商品マッピング作成
    mapping_success = create_amazon_product_mappings()
    
    if orders_success and mapping_success:
        print("\n🚀 Amazon統合テスト準備完了!")
        print("ダッシュボードでAmazon売上が表示されるはずです")
    else:
        print("\n❌ テストデータ作成に問題がありました")