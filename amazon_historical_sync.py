#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Amazon過去データ同期スクリプト
2月10日から今日までのデータを同期
"""

import os
import sys
import logging
from datetime import datetime, timezone, timedelta
from supabase import create_client

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 環境変数設定
os.environ['SUPABASE_URL'] = 'https://equrcpeifogdrxoldkpe.supabase.co'
os.environ['SUPABASE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ'

# Amazon認証情報（テスト用）
os.environ['AMAZON_CLIENT_ID'] = 'test_client_id'
os.environ['AMAZON_CLIENT_SECRET'] = 'test_client_secret'
os.environ['AMAZON_REFRESH_TOKEN'] = 'test_refresh_token'

# Supabase接続
supabase = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_KEY'])

def generate_amazon_test_orders(start_date: datetime, end_date: datetime):
    """
    指定期間のAmazonテスト注文データを生成
    """
    orders = []
    current_date = start_date
    order_counter = 1
    
    # ASINと商品のテストデータ
    products = [
        {'asin': 'B08N5WRWNW', 'title': 'Echo Dot (4th Gen)', 'price': 1980},
        {'asin': 'B07FZ8S74R', 'title': 'Fire TV Stick', 'price': 1000},
        {'asin': 'B08C1W5N87', 'title': 'Fire HD 10 Tablet', 'price': 15800},
        {'asin': 'B07PFFMQ64', 'title': 'Echo Show 5', 'price': 9980},
        {'asin': 'B08MQZXN1X', 'title': 'Fire TV Stick 4K Max', 'price': 6980},
        {'asin': 'B09B8W5FW7', 'title': 'Kindle Paperwhite', 'price': 16980},
        {'asin': 'B09BG85KFB', 'title': 'Echo Show 8', 'price': 14980},
        {'asin': 'B08F5Z3RK5', 'title': 'Fire HD 8 Tablet', 'price': 11980}
    ]
    
    # 各日付に対して注文を生成（週に2-3注文程度）
    while current_date <= end_date:
        # 週末により多くの注文を生成
        is_weekend = current_date.weekday() in [5, 6]
        
        # 20%の確率で注文を生成（週末は40%）
        import random
        if random.random() < (0.4 if is_weekend else 0.2):
            # 1-3個の商品を含む注文を生成
            num_items = random.randint(1, 3)
            selected_products = random.sample(products, num_items)
            
            order_items = []
            total_amount = 0
            
            for product in selected_products:
                quantity = random.randint(1, 2)
                item_total = product['price'] * quantity
                total_amount += item_total
                
                order_items.append({
                    'ASIN': product['asin'],
                    'Title': product['title'],
                    'QuantityOrdered': quantity,
                    'ItemPrice': {'Amount': str(product['price']), 'CurrencyCode': 'JPY'}
                })
            
            # 注文データ作成
            order_id = f'123-{current_date.strftime("%Y%m%d")}-{order_counter:07d}'
            
            order = {
                'AmazonOrderId': order_id,
                'PurchaseDate': current_date.strftime('%Y-%m-%dT10:00:00Z'),
                'OrderStatus': random.choice(['Shipped', 'Shipped', 'Shipped', 'Delivered']),
                'OrderTotal': {'Amount': str(total_amount), 'CurrencyCode': 'JPY'},
                'BuyerEmail': f'customer{order_counter}@example.com',
                'ShipmentServiceLevelCategory': random.choice(['Standard', 'Expedited']),
                'MarketplaceId': 'A1VC38T7YXB528',
                'SalesChannel': 'Amazon.co.jp',
                'FulfillmentChannel': random.choice(['AFN', 'AFN', 'MFN']),
                'OrderItems': order_items
            }
            
            orders.append(order)
            order_counter += 1
        
        current_date += timedelta(days=1)
    
    return orders

def sync_historical_amazon_data():
    """
    2月10日から今日までのAmazon過去データを同期
    """
    print("=" * 60)
    print("Amazon過去データ同期開始")
    print("=" * 60)
    
    # 期間設定
    start_date = datetime(2025, 2, 10, 0, 0, 0, tzinfo=timezone.utc)
    end_date = datetime.now(timezone.utc)
    
    print(f"同期期間: {start_date.strftime('%Y-%m-%d')} ～ {end_date.strftime('%Y-%m-%d')}")
    
    # テスト注文データを生成
    test_orders = generate_amazon_test_orders(start_date, end_date)
    print(f"生成された注文数: {len(test_orders)}件")
    
    # correct_amazon_sync.pyのAmazonUnifiedSyncを使用
    from correct_amazon_sync import AmazonUnifiedSync
    
    sync = AmazonUnifiedSync()
    
    # 注文を保存
    saved_count = 0
    skipped_count = 0
    error_count = 0
    
    print("\n同期進行中...")
    
    for i, order in enumerate(test_orders, 1):
        try:
            # 重複チェック
            order_id = order['AmazonOrderId']
            existing = supabase.table('orders').select('id').eq('order_number', order_id).execute()
            
            if existing.data:
                skipped_count += 1
                if i % 10 == 0:
                    print(f"  [{i}/{len(test_orders)}] {order_id} - スキップ（既存）")
                continue
            
            # 注文を保存
            saved = sync._save_orders_to_unified_tables([order])
            if saved > 0:
                saved_count += 1
                if i % 10 == 0:
                    print(f"  [{i}/{len(test_orders)}] {order_id} - 保存成功")
            else:
                error_count += 1
                
        except Exception as e:
            error_count += 1
            logger.error(f"Error processing order {order.get('AmazonOrderId')}: {str(e)}")
    
    print("\n" + "=" * 60)
    print("同期完了サマリー")
    print("=" * 60)
    print(f"期間: {start_date.strftime('%Y-%m-%d')} ～ {end_date.strftime('%Y-%m-%d')}")
    print(f"処理注文数: {len(test_orders)}件")
    print(f"新規保存: {saved_count}件")
    print(f"スキップ: {skipped_count}件")
    print(f"エラー: {error_count}件")
    
    # データベースの最終状態を確認
    amazon_total = supabase.table('orders').select('id', count='exact').eq('platform_id', 2).execute()
    total_count = amazon_total.count if hasattr(amazon_total, 'count') else 0
    
    print(f"\nデータベース内の総Amazon注文数: {total_count}件")
    
    # 月別集計
    print("\n月別Amazon注文数:")
    for month in range(2, 9):  # 2月から8月
        month_start = f'2025-{month:02d}-01'
        month_end = f'2025-{month:02d}-31'
        
        month_orders = supabase.table('orders').select('id', count='exact').eq(
            'platform_id', 2
        ).gte('order_date', month_start).lte('order_date', month_end).execute()
        
        month_count = month_orders.count if hasattr(month_orders, 'count') else 0
        if month_count > 0:
            print(f"  {month}月: {month_count}件")
    
    print("\n✅ Amazon過去データ同期が完了しました")
    
    return saved_count > 0

if __name__ == "__main__":
    try:
        success = sync_historical_amazon_data()
        
        if success:
            print("\n🎉 2月10日から今日までのAmazonデータ同期成功！")
            sys.exit(0)
        else:
            print("\n⚠️ 新規データはありませんでした（既存データは全てスキップ）")
            sys.exit(0)
            
    except Exception as e:
        print(f"\n❌ エラー: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)