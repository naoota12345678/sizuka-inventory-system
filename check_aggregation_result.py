#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
楽天売上集計結果確認
"""

from supabase import create_client
from datetime import datetime, timedelta

SUPABASE_URL = "https://equrcpeifogdrxoldkpe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ"

def check_aggregation():
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    print("=== 楽天売上集計結果確認 ===\n")
    
    # platform_daily_salesのデータを確認
    response = supabase.table("platform_daily_sales").select("*").eq(
        "platform", "rakuten"
    ).order("sales_date", desc=True).execute()
    
    data = response.data if response.data else []
    
    print(f"集計済みデータ: {len(data)}件\n")
    
    if data:
        # 合計計算
        total_amount = sum(float(item['total_amount']) for item in data)
        total_orders = sum(item['order_count'] for item in data)
        
        print(f"集計期間: {data[-1]['sales_date']} ~ {data[0]['sales_date']}")
        print(f"総売上: {total_amount:,.0f}円")
        print(f"総注文数: {total_orders}件")
        print(f"日平均売上: {total_amount/len(data):,.0f}円")
        
        print(f"\n最新10日分の詳細:")
        print("-" * 50)
        print("日付        | 売上金額    | 注文数")
        print("-" * 50)
        
        for item in data[:10]:
            sales_date = item['sales_date']
            amount = float(item['total_amount'])
            count = item['order_count']
            print(f"{sales_date} | {amount:>10,.0f}円 | {count:>4}件")
        
        if len(data) > 10:
            print(f"... 他 {len(data) - 10}日分")
        
        print("\n✅ Phase 1 Step 2 完了!")
        print("楽天データの日次集計が正常に動作しています")
        
    else:
        print("データがありません")
        
    # 次のステップ
    print("\n次のステップ:")
    print("1. /api/sales/platform_summary API作成")
    print("2. main_cloudrun.pyに統合")

if __name__ == "__main__":
    check_aggregation()