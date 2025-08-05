#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from supabase import create_client
import re

SUPABASE_URL = "https://equrcpeifogdrxoldkpe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ"

def quick_test():
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    print("=== クイックテスト ===")
    
    # 1. 全データ数
    all_query = supabase.table('order_items').select('choice_code', count='exact').gte('orders.created_at', '2025-08-01').lte('orders.created_at', '2025-08-04')
    all_response = all_query.execute()
    total_count = all_response.count
    
    # 2. choice_codeがあるデータ数
    choice_query = supabase.table('order_items').select('choice_code', count='exact').gte('orders.created_at', '2025-08-01').lte('orders.created_at', '2025-08-04').not_.is_('choice_code', 'null').neq('choice_code', '')
    choice_response = choice_query.execute()
    choice_count = choice_response.count
    
    print(f"全注文数: {total_count}件")
    print(f"choice_code付き注文数: {choice_count}件")
    print(f"choice_code付き比率: {choice_count/total_count*100:.1f}%")
    
    # 3. 実際のchoice_codeサンプル
    sample_query = supabase.table('order_items').select('choice_code').not_.is_('choice_code', 'null').neq('choice_code', '').limit(5).execute()
    
    print(f"\nchoice_codeサンプル:")
    for item in sample_query.data:
        choice_code = item.get('choice_code', '')
        extracted = re.findall(r'R\d{2,}', choice_code)
        print(f"  '{choice_code}' → {extracted}")
    
    print(f"\n結論:")
    if choice_count == total_count:
        print("  全データにchoice_codeがあります → 基本売上集計のバグです")
    elif choice_count > total_count * 0.9:
        print("  ほぼ全データにchoice_codeがあります → フィルタリング条件の問題です")
    else:
        print(f"  {total_count - choice_count}件のデータにchoice_codeがありません → これが成功率低下の原因です")

if __name__ == "__main__":
    quick_test()