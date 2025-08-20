#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Amazon統合同期のテストスクリプト
"""

import os
import sys

# 環境変数を直接設定
os.environ['SUPABASE_URL'] = 'https://equrcpeifogdrxoldkpe.supabase.co'
os.environ['SUPABASE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ'

# Amazon認証情報（テスト用ダミー）
os.environ['AMAZON_CLIENT_ID'] = 'test_client_id'
os.environ['AMAZON_CLIENT_SECRET'] = 'test_client_secret' 
os.environ['AMAZON_REFRESH_TOKEN'] = 'test_refresh_token'

# Amazon統合同期をインポートして実行
from correct_amazon_sync import AmazonUnifiedSync

def test_amazon_sync():
    """Amazon統合同期をテスト"""
    print("=== Amazon統合同期テスト ===")
    
    try:
        sync = AmazonUnifiedSync()
        
        # テストモードで同期実行（認証失敗時は自動的にテストデータ作成）
        success = sync.sync_recent_orders(days=1)
        
        if success:
            print("✅ Amazon統合同期テスト成功")
            
            # 結果確認
            from supabase import create_client
            supabase = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_KEY'])
            
            amazon_orders = supabase.table('orders').select('id', count='exact').eq('platform_id', 2).execute()
            total_orders = amazon_orders.count if hasattr(amazon_orders, 'count') else 0
            
            print(f"データベース内のAmazon注文: {total_orders}件")
            
            # 最新のAmazon注文を表示
            recent = supabase.table('orders').select('order_number, order_date, total_amount, platform_data').eq('platform_id', 2).order('created_at', desc=True).limit(3).execute()
            
            if recent.data:
                print("\n最新のAmazon注文:")
                for order in recent.data:
                    order_num = order['order_number']
                    amount = order['total_amount']
                    date = order['order_date'][:10] if order['order_date'] else 'N/A'
                    platform_data = order.get('platform_data', {})
                    sales_channel = platform_data.get('sales_channel', 'N/A')
                    
                    print(f"  - {order_num}: ¥{amount:,.0f} | {date} | {sales_channel}")
            
        else:
            print("❌ Amazon統合同期テスト失敗")
            
    except Exception as e:
        print(f"❌ テストエラー: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_amazon_sync()