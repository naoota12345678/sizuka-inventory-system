#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
order_itemsテーブルを完全にクリアして楽天APIから再同期
"""

import os
import logging
from datetime import datetime, timedelta
from supabase import create_client

# 環境変数を設定
os.environ['SUPABASE_URL'] = 'https://equrcpeifogdrxoldkpe.supabase.co'
os.environ['SUPABASE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ'
os.environ['RAKUTEN_SERVICE_SECRET'] = 'SP338531_d1NJjF2R5OwZpWH6'
os.environ['RAKUTEN_LICENSE_KEY'] = 'SL338531_kUvqO4kIHaMbr9ik'

from api.rakuten_api import RakutenAPI

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SUPABASE_URL = "https://equrcpeifogdrxoldkpe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ"

def clean_and_resync():
    """order_itemsとordersをクリアして楽天APIから再同期"""
    
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    print("=== データクリア・再同期プロセス ===")
    
    # 1. 現在のデータ件数確認
    orders_count = len(supabase.table("orders").select("id").execute().data)
    items_count = len(supabase.table("order_items").select("id").execute().data)
    
    print(f"現在のデータ:")
    print(f"  orders: {orders_count}件")
    print(f"  order_items: {items_count}件")
    
    # 2. データ削除の確認
    response = input(f"\n全ての注文データ({orders_count}件の注文、{items_count}件の商品)を削除して再同期しますか？ (y/n): ")
    if response.lower() != 'y':
        print("キャンセルしました")
        return
    
    # 3. order_itemsテーブルをクリア
    print("\n=== order_itemsテーブルをクリア中 ===")
    try:
        # 全てのorder_itemsを削除
        delete_result = supabase.table("order_items").delete().neq("id", 0).execute()
        print(f"order_items削除完了: {len(delete_result.data)}件削除")
    except Exception as e:
        print(f"order_items削除エラー: {e}")
        return
    
    # 4. ordersテーブルをクリア
    print("\n=== ordersテーブルをクリア中 ===")
    try:
        # 全てのordersを削除
        delete_result = supabase.table("orders").delete().neq("id", 0).execute()
        print(f"orders削除完了: {len(delete_result.data)}件削除")
    except Exception as e:
        print(f"orders削除エラー: {e}")
        return
    
    # 5. 楽天APIから再同期
    print("\n=== 楽天APIから再同期開始 ===")
    
    api = RakutenAPI()
    
    # 期間を設定（例：過去30日間）
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    print(f"同期期間: {start_date.strftime('%Y-%m-%d')} ～ {end_date.strftime('%Y-%m-%d')}")
    
    try:
        # 注文データを取得
        orders = api.get_orders(start_date, end_date)
        print(f"取得した注文数: {len(orders)}件")
        
        if orders:
            # Supabaseに保存
            result = api.save_to_supabase(orders)
            print(f"\n=== 同期結果 ===")
            print(f"注文保存: {result['success_count']}/{result['total_orders']} ({result['success_rate']})")
            print(f"商品保存成功: {result['items_success']}件")
            print(f"商品保存失敗: {result['items_error']}件")
            
            if result['failed_orders']:
                print(f"失敗した注文: {len(result['failed_orders'])}件")
                for failed in result['failed_orders'][:3]:
                    print(f"  - {failed['order_number']}: {failed['error']}")
        else:
            print("指定期間に注文データがありませんでした")
    
    except Exception as e:
        print(f"同期エラー: {str(e)}")
        return
    
    # 6. 結果確認
    print("\n=== 同期後データ確認 ===")
    final_orders = len(supabase.table("orders").select("id").execute().data)
    final_items = len(supabase.table("order_items").select("id").execute().data)
    
    print(f"同期後のデータ:")
    print(f"  orders: {final_orders}件")
    print(f"  order_items: {final_items}件")
    
    # 7. マッピングテスト
    if final_items > 0:
        print("\n=== マッピングテスト ===")
        from fix_rakuten_sku_mapping import FixedMappingSystem
        
        mapping_system = FixedMappingSystem()
        
        # サンプル20件でテスト
        sample_orders = supabase.table("order_items").select("*").not_.like("product_code", "TEST%").limit(20).execute()
        
        success_count = 0
        total_count = len(sample_orders.data)
        
        for order in sample_orders.data:
            mapping = mapping_system.find_product_mapping(order)
            if mapping:
                success_count += 1
                print(f"✓ {order['product_code']} (SKU: {order.get('rakuten_item_number')}) → {mapping['common_code']}")
        
        mapping_rate = (success_count / total_count * 100) if total_count > 0 else 0
        print(f"\nマッピング結果: {success_count}/{total_count} ({mapping_rate:.1f}%)")
        
        if mapping_rate >= 90:
            print("🎉 マッピング率が90%以上に回復しました！")
        elif mapping_rate >= 70:
            print("✅ マッピング率が改善されました")
        else:
            print("⚠️ マッピング率がまだ低いです。追加の調査が必要です")
    
    print("\n=== 完了 ===")

if __name__ == "__main__":
    clean_and_resync()