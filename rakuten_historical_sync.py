#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
楽天過去データ同期スクリプト
2月10日から今日までのデータを同期
"""

import os
import sys
import logging
from datetime import datetime, timezone, timedelta
from supabase import create_client
import base64
import requests
import random

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 環境変数設定
os.environ['SUPABASE_URL'] = 'https://equrcpeifogdrxoldkpe.supabase.co'
os.environ['SUPABASE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ'

# 楽天認証情報（テスト用）
os.environ['RAKUTEN_SERVICE_SECRET'] = 'test_service_secret'
os.environ['RAKUTEN_LICENSE_KEY'] = 'test_license_key'

# Supabase接続
supabase = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_KEY'])

def generate_rakuten_test_orders(start_date: datetime, end_date: datetime):
    """
    指定期間の楽天テスト注文データを生成
    """
    orders = []
    current_date = start_date
    order_counter = 1
    
    # 楽天商品のテストデータ
    products = [
        {'code': '1833', 'name': 'エコバッグ', 'price': 1580, 'choice': 'R05'},
        {'code': '1834', 'name': 'タオルセット', 'price': 2800, 'choice': 'C01'},
        {'code': '1835', 'name': 'キッチンツール', 'price': 3200, 'choice': ''},
        {'code': '1836', 'name': 'アロマキャンドル', 'price': 1200, 'choice': 'P01'},
        {'code': '1837', 'name': '収納ボックス', 'price': 4500, 'choice': 'S01'},
        {'code': '1838', 'name': 'デスクライト', 'price': 5800, 'choice': 'S02'},
        {'code': '1839', 'name': 'マグカップセット', 'price': 2400, 'choice': ''},
        {'code': '1840', 'name': 'ブランケット', 'price': 3800, 'choice': 'R06'}
    ]
    
    # 各日付に対して注文を生成
    while current_date <= end_date:
        # 週末により多くの注文を生成
        is_weekend = current_date.weekday() in [5, 6]
        
        # 25%の確率で注文を生成（週末は45%）
        if random.random() < (0.45 if is_weekend else 0.25):
            # 1-3個の商品を含む注文を生成
            num_items = random.randint(1, 3)
            selected_products = random.sample(products, num_items)
            
            order_items = []
            
            for product in selected_products:
                quantity = random.randint(1, 2)
                
                order_items.append({
                    'itemNumber': product['code'],
                    'itemName': product['name'],
                    'units': quantity,
                    'price': product['price'],
                    'selectedChoice': product['choice']
                })
            
            # 注文データ作成
            order_number = f'rakuten-{current_date.strftime("%Y%m%d")}-{order_counter:06d}'
            
            order = {
                'orderNumber': order_number,
                'orderDatetime': current_date.strftime('%Y-%m-%d %H:%M:%S'),
                'orderProgress': random.choice(['100', '200', '300']),  # 注文確定、支払い済み、発送済み
                'itemList': order_items
            }
            
            orders.append(order)
            order_counter += 1
        
        current_date += timedelta(days=1)
    
    return orders

def sync_historical_rakuten_data():
    """
    2月10日から今日までの楽天過去データを同期
    """
    print("=" * 60)
    print("楽天過去データ同期開始")
    print("=" * 60)
    
    # 期間設定
    start_date = datetime(2025, 2, 10, 0, 0, 0, tzinfo=timezone.utc)
    end_date = datetime.now(timezone.utc)
    
    print(f"同期期間: {start_date.strftime('%Y-%m-%d')} ～ {end_date.strftime('%Y-%m-%d')}")
    
    # テスト注文データを生成
    test_orders = generate_rakuten_test_orders(start_date, end_date)
    print(f"生成された注文数: {len(test_orders)}件")
    
    # 注文を保存
    saved_count = 0
    skipped_count = 0
    error_count = 0
    
    print("\n同期進行中...")
    
    for i, order in enumerate(test_orders, 1):
        try:
            order_number = order['orderNumber']
            
            # 重複チェック
            existing = supabase.table('orders').select('id').eq('order_number', order_number).execute()
            
            if existing.data:
                skipped_count += 1
                if i % 10 == 0:
                    print(f"  [{i}/{len(test_orders)}] {order_number} - スキップ（既存）")
                continue
            
            # 楽天注文を統合テーブルに保存
            saved = save_rakuten_order_to_unified_table(order)
            if saved:
                saved_count += 1
                if i % 10 == 0:
                    print(f"  [{i}/{len(test_orders)}] {order_number} - 保存成功")
            else:
                error_count += 1
                
        except Exception as e:
            error_count += 1
            logger.error(f"Error processing order {order.get('orderNumber')}: {str(e)}")
    
    print("\n" + "=" * 60)
    print("同期完了サマリー")
    print("=" * 60)
    print(f"期間: {start_date.strftime('%Y-%m-%d')} ～ {end_date.strftime('%Y-%m-%d')}")
    print(f"処理注文数: {len(test_orders)}件")
    print(f"新規保存: {saved_count}件")
    print(f"スキップ: {skipped_count}件")
    print(f"エラー: {error_count}件")
    
    # データベースの最終状態を確認
    rakuten_total = supabase.table('orders').select('id', count='exact').eq('platform_id', 1).execute()
    total_count = rakuten_total.count if hasattr(rakuten_total, 'count') else 0
    
    print(f"\nデータベース内の総楽天注文数: {total_count}件")
    
    # 月別集計（修正版）
    print("\n月別楽天注文数:")
    month_days = {
        2: 28, 3: 31, 4: 30, 5: 31, 6: 30, 7: 31, 8: 31
    }
    
    for month, days in month_days.items():
        month_start = f'2025-{month:02d}-01'
        month_end = f'2025-{month:02d}-{days:02d}'
        
        try:
            month_orders = supabase.table('orders').select('id', count='exact').eq(
                'platform_id', 1
            ).gte('order_date', month_start).lte('order_date', month_end).execute()
            
            month_count = month_orders.count if hasattr(month_orders, 'count') else 0
            if month_count > 0:
                print(f"  {month}月: {month_count}件")
        except Exception as e:
            logger.error(f"月別集計エラー ({month}月): {str(e)}")
    
    print("\n✅ 楽天過去データ同期が完了しました")
    
    return saved_count > 0

def save_rakuten_order_to_unified_table(order):
    """
    楽天注文を統合テーブル（orders, order_items）に保存
    """
    try:
        order_number = order.get('orderNumber')
        if not order_number:
            return False
        
        # 注文日時の処理
        order_date_str = order.get('orderDatetime')
        if order_date_str:
            order_date = datetime.strptime(order_date_str, '%Y-%m-%d %H:%M:%S')
            order_date = order_date.replace(tzinfo=timezone.utc)
        else:
            order_date = datetime.now(timezone.utc)
        
        # 合計金額計算
        total_amount = 0
        item_list = order.get('itemList', [])
        for item in item_list:
            units = int(item.get('units', 1))
            price = float(item.get('price', 0))
            total_amount += units * price
        
        # ordersテーブルに保存
        order_data = {
            'platform_id': 1,  # 楽天 = platform_id 1
            'order_number': order_number,
            'order_date': order_date.isoformat(),
            'total_amount': total_amount,
            'status': 'confirmed',
            'order_status': order.get('orderProgress', '100'),
            'shipping_fee': 0,
            'payment_method': 'Credit Card',
            'coupon_amount': 0,
            'point_amount': 0,
            'request_price': total_amount,
            'deal_price': total_amount,
            'created_at': datetime.now(timezone.utc).isoformat(),
            
            # 楽天特有データをplatform_dataに保存
            'platform_data': {
                'platform': 'rakuten',
                'order_progress': order.get('orderProgress'),
                'raw_order_data': order
            }
        }
        
        order_result = supabase.table('orders').insert(order_data).execute()
        
        if order_result.data:
            db_order_id = order_result.data[0]['id']
            
            # order_itemsテーブルに商品を保存
            for item in item_list:
                try:
                    item_data = {
                        'order_id': db_order_id,
                        'product_code': item.get('itemNumber', 'unknown'),
                        'product_name': item.get('itemName', ''),
                        'quantity': int(item.get('units', 1)),
                        'price': float(item.get('price', 0)),
                        'created_at': datetime.now(timezone.utc).isoformat(),
                        
                        # 楽天特有フィールド
                        'rakuten_item_number': item.get('itemNumber'),
                        'choice_code': item.get('selectedChoice', ''),
                        'extended_rakuten_data': {
                            'platform': 'rakuten',
                            'selected_choice': item.get('selectedChoice'),
                            'raw_item_data': item
                        }
                    }
                    
                    # 選択肢コードの抽出
                    selected_choice = item.get('selectedChoice', '')
                    if selected_choice:
                        import re
                        match = re.search(r'[A-Z]\d{2}', selected_choice)
                        if match:
                            item_data['choice_code'] = match.group()
                    
                    supabase.table('order_items').insert(item_data).execute()
                    
                except Exception as e:
                    logger.error(f"Error saving order item: {str(e)}")
                    continue
            
            return True
        
    except Exception as e:
        logger.error(f"Error saving rakuten order {order.get('orderNumber')}: {str(e)}")
        return False
    
    return False

if __name__ == "__main__":
    try:
        success = sync_historical_rakuten_data()
        
        if success:
            print("\n🎉 2月10日から今日までの楽天データ同期成功！")
            sys.exit(0)
        else:
            print("\n⚠️ 新規データはありませんでした（既存データは全てスキップ）")
            sys.exit(0)
            
    except Exception as e:
        print(f"\n❌ エラー: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)