#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from supabase import create_client

SUPABASE_URL = "https://equrcpeifogdrxoldkpe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ"

def check_orders():
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    print("=== 注文データ確認 ===")
    
    # 総件数確認
    try:
        all_count = supabase.table("orders").select("id", count="exact").execute()
        print(f"orders総件数: {all_count.count}件")
        
        # 月別件数
        july_2025 = supabase.table("orders").select("id", count="exact").gte("created_at", "2025-07-01").lt("created_at", "2025-08-01").execute()
        print(f"2025年7月: {july_2025.count}件")
        
        july_2024 = supabase.table("orders").select("id", count="exact").gte("created_at", "2024-07-01").lt("created_at", "2024-08-01").execute()
        print(f"2024年7月: {july_2024.count}件")
        
        aug_2025 = supabase.table("orders").select("id", count="exact").gte("created_at", "2025-08-01").lt("created_at", "2025-09-01").execute()
        print(f"2025年8月: {aug_2025.count}件")
        
        # 期待していた300件がどの期間のものか確認
        print(f"\n期間別詳細:")
        
        # 過去3ヶ月
        for year in [2024, 2025]:
            for month in range(6, 9):  # 6月、7月、8月
                start_date = f"{year}-{month:02d}-01"
                if month == 12:
                    end_date = f"{year+1}-01-01"
                else:
                    end_date = f"{year}-{month+1:02d}-01"
                
                count_response = supabase.table("orders").select("id", count="exact").gte("created_at", start_date).lt("created_at", end_date).execute()
                print(f"  {year}年{month}月: {count_response.count}件")
        
    except Exception as e:
        print(f"エラー: {e}")

if __name__ == "__main__":
    check_orders()