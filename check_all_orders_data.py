#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全期間のordersデータ確認
7月のデータが本当に少ないのか、それとも別の問題なのかを調査
"""

from supabase import create_client
from collections import defaultdict

SUPABASE_URL = "https://equrcpeifogdrxoldkpe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFuno5YXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ"

def check_all_orders():
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    print("=== 全期間ordersデータ確認 ===\n")
    
    # 1. 全ordersデータの概要
    print("【1】ordersテーブル全体の概要")
    print("-" * 50)
    
    all_orders = supabase.table("orders").select("id, created_at, total_amount").execute()
    orders = all_orders.data if all_orders.data else []
    
    print(f"ordersテーブル総件数: {len(orders)}件")
    
    if orders:
        total_amount = sum(float(order.get('total_amount', 0)) for order in orders)
        print(f"総売上: {total_amount:,.0f}円")
        
        # 月別分布
        monthly_counts = defaultdict(int)
        monthly_amounts = defaultdict(float)
        
        for order in orders:
            created_at = order.get('created_at', '')
            
            # 年月を抽出
            if 'T' in created_at:
                date_part = created_at.split('T')[0]
            else:
                date_part = created_at[:10]
            
            if len(date_part) >= 7:
                year_month = date_part[:7]  # YYYY-MM
                monthly_counts[year_month] += 1
                monthly_amounts[year_month] += float(order.get('total_amount', 0))
        
        print(f"\n月別注文分布:")
        for year_month in sorted(monthly_counts.keys()):
            count = monthly_counts[year_month]
            amount = monthly_amounts[year_month]
            print(f"  {year_month}: {count}件 ({amount:,.0f}円)")
    
    # 2. 7月データの詳細確認
    print(f"\n【2】7月データの詳細確認")
    print("-" * 50)
    
    july_2025 = supabase.table("orders").select("*").gte(
        "created_at", "2025-07-01"
    ).lt("created_at", "2025-08-01").execute()
    
    july_orders = july_2025.data if july_2025.data else []
    
    print(f"2025年7月の注文: {len(july_orders)}件")
    
    if july_orders:
        print("\n7月の全注文詳細:")
        for order in july_orders:
            created_at = order.get('created_at', '')
            total_amount = order.get('total_amount', 0)
            order_id = order.get('id', 'N/A')
            print(f"  ID:{order_id} | {created_at} | {total_amount:,.0f}円")
    
    # 3. 2024年7月のデータも確認
    print(f"\n【3】2024年7月のデータも確認")
    print("-" * 50)
    
    july_2024 = supabase.table("orders").select("*").gte(
        "created_at", "2024-07-01"
    ).lt("created_at", "2024-08-01").execute()
    
    july_2024_orders = july_2024.data if july_2024.data else []
    print(f"2024年7月の注文: {len(july_2024_orders)}件")
    
    if july_2024_orders:
        july_2024_total = sum(float(order.get('total_amount', 0)) for order in july_2024_orders)
        print(f"2024年7月総売上: {july_2024_total:,.0f}円")
    
    # 4. 最新データの確認
    print(f"\n【4】最新データの確認")
    print("-" * 50)
    
    recent_orders = supabase.table("orders").select(
        "id, created_at, total_amount"
    ).order("created_at", desc=True).limit(10).execute()
    
    recent = recent_orders.data if recent_orders.data else []
    
    print("最新10件の注文:")
    for order in recent:
        created_at = order.get('created_at', '')
        total_amount = order.get('total_amount', 0)
        order_id = order.get('id', 'N/A')
        print(f"  ID:{order_id} | {created_at} | {total_amount:,.0f}円")
    
    # 5. 結論
    print(f"\n【5】結論")
    print("-" * 50)
    
    if len(july_orders) < 50:  # 50件未満なら少ない
        print("🚨 問題確認: 2025年7月のordersデータが異常に少ない")
        print("考えられる原因:")
        print("1. 楽天APIからのデータ同期が7月から開始された")
        print("2. 7月以前のデータが別のテーブルに保存されている")
        print("3. データ移行が未完了")
        print("4. 実際に7月は売上が少なかった")
        
        if len(july_2024_orders) > 100:
            print(f"\n💡 発見: 2024年7月は{len(july_2024_orders)}件あります")
            print("→ 年を間違えて検索していた可能性があります")
        
    else:
        print("✅ 7月のordersデータは正常範囲内です")
        print("platform_daily_salesの集計処理に問題がある可能性があります")

if __name__ == "__main__":
    check_all_orders()