#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from supabase import create_client
import re

SUPABASE_URL = "https://equrcpeifogdrxoldkpe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ"

def simple_check():
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    print("=== データ状況確認 ===")
    
    # 期間指定で全order_itemsを取得（ordersとのjoin含む）
    all_query = supabase.table('order_items').select('choice_code, orders!inner(created_at)', count='exact').gte('orders.created_at', '2025-08-01').lte('orders.created_at', '2025-08-04')
    all_response = all_query.execute()
    total_count = all_response.count
    
    # choice_codeがあるデータのみ
    choice_query = supabase.table('order_items').select('choice_code, orders!inner(created_at)', count='exact').gte('orders.created_at', '2025-08-01').lte('orders.created_at', '2025-08-04').not_.is_('choice_code', 'null').neq('choice_code', '')
    choice_response = choice_query.execute()
    choice_count = choice_response.count
    
    print(f"期間内全注文: {total_count}件")
    print(f"choice_code付き: {choice_count}件")
    print(f"choice_codeなし: {total_count - choice_count}件")
    print(f"choice_code付き比率: {choice_count/total_count*100:.1f}%")
    
    print(f"\n=== 結論 ===")
    if choice_count == total_count:
        print("❌ 全データにchoice_codeがあるのに基本売上集計が0.4%は明らかなバグ")
    elif choice_count > 0:
        print(f"⚠️  choice_code付きデータは{choice_count}件存在")
        print(f"   基本売上集計は同じフィルタリングを使えば同じ成功率になるはず")
    else:
        print("❓ choice_code付きデータが存在しない")

if __name__ == "__main__":
    simple_check()