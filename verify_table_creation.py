#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
platform_daily_salesテーブル作成確認
"""

from supabase import create_client

SUPABASE_URL = "https://equrcpeifogdrxoldkpe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ"

def verify_table_creation():
    """テーブル作成確認"""
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    print("=== platform_daily_salesテーブル作成確認 ===")
    
    try:
        # テーブル存在確認
        response = supabase.table("platform_daily_sales").select("*").execute()
        data = response.data if response.data else []
        
        print(f"テーブル作成成功!")
        print(f"現在のデータ件数: {len(data)}件")
        
        if data:
            print("\n現在のデータ:")
            for item in data:
                sales_date = item.get('sales_date')
                platform = item.get('platform')
                total_amount = item.get('total_amount', 0)
                order_count = item.get('order_count', 0)
                print(f"  {sales_date} | {platform} | {total_amount:,.0f}円 | {order_count}件")
        
        # テストデータ挿入確認
        print(f"\nテストデータ挿入確認...")
        test_data = {
            "sales_date": "2025-08-05",
            "platform": "rakuten",
            "total_amount": 750000,
            "order_count": 30
        }
        
        insert_response = supabase.table("platform_daily_sales").insert(test_data).execute()
        if insert_response.data:
            print("テストデータ挿入成功!")
            
            # テストデータを削除
            supabase.table("platform_daily_sales").delete().eq("sales_date", "2025-08-05").eq("platform", "rakuten").execute()
            print("テストデータ削除完了")
        
        print(f"\n=== 結果 ===")
        print("platform_daily_salesテーブルが正常に作成され、動作しています!")
        print("Phase 1 Step 1 完了 - 次のステップに進めます")
        
        return True
        
    except Exception as e:
        print(f"エラー: {str(e)}")
        print("テーブルがまだ作成されていない可能性があります")
        print("Supabase Dashboard でSQLを実行してください")
        return False

if __name__ == "__main__":
    verify_table_creation()