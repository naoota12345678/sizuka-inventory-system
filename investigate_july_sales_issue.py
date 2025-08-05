#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
7月売上データの問題調査
300件のはずが8件しか表示されない原因を特定
"""

from supabase import create_client
from datetime import datetime

SUPABASE_URL = "https://equrcpeifogdrxoldkpe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ"

def investigate_july_sales():
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    print("=== 7月売上データ調査 ===\n")
    
    # 1. ordersテーブルの7月データを確認
    print("【1】ordersテーブルの7月データ確認")
    print("-" * 50)
    
    july_orders = supabase.table("orders").select(
        "id, created_at, total_amount"
    ).gte("created_at", "2025-07-01").lt("created_at", "2025-08-01").execute()
    
    orders = july_orders.data if july_orders.data else []
    print(f"ordersテーブル 7月データ: {len(orders)}件")
    
    if orders:
        total_amount = sum(float(order.get('total_amount', 0)) for order in orders)
        print(f"7月総売上（ordersベース）: {total_amount:,.0f}円")
        
        # 日別分布確認
        daily_counts = {}
        for order in orders:
            created_at = order.get('created_at', '')
            if 'T' in created_at:
                date = created_at.split('T')[0]
            else:
                date = created_at[:10]
            
            daily_counts[date] = daily_counts.get(date, 0) + 1
        
        print(f"\n7月の日別注文分布（上位10日）:")
        sorted_days = sorted(daily_counts.items(), key=lambda x: x[1], reverse=True)
        for date, count in sorted_days[:10]:
            print(f"  {date}: {count}件")
    
    # 2. platform_daily_salesテーブルの7月データを確認
    print(f"\n【2】platform_daily_salesテーブルの7月データ確認")
    print("-" * 50)
    
    platform_july = supabase.table("platform_daily_sales").select(
        "*"
    ).gte("sales_date", "2025-07-01").lt("sales_date", "2025-08-01").execute()
    
    platform_data = platform_july.data if platform_july.data else []
    print(f"platform_daily_salesテーブル 7月データ: {len(platform_data)}件")
    
    if platform_data:
        platform_total = sum(float(item.get('total_amount', 0)) for item in platform_data)
        print(f"7月総売上（platform_daily_salesベース）: {platform_total:,.0f}円")
        
        print(f"\n7月のplatform_daily_salesデータ:")
        for item in platform_data:
            print(f"  {item['sales_date']}: {item['total_amount']:,.0f}円 ({item['order_count']}件)")
    else:
        print("platform_daily_salesに7月データがありません")
    
    # 3. 差分の特定
    print(f"\n【3】データ差分の分析")
    print("-" * 50)
    
    if orders and platform_data:
        orders_count = len(orders)
        platform_count = sum(item['order_count'] for item in platform_data)
        
        print(f"ordersテーブル: {orders_count}件")
        print(f"platform_daily_sales集計: {platform_count}件")
        print(f"差分: {orders_count - platform_count}件")
        
        if orders_count != platform_count:
            print(f"\n🚨 問題発見: 集計データに {orders_count - platform_count}件の漏れがあります")
            print("原因の可能性:")
            print("1. 楽天データ集計処理が7月分を完全に処理していない")
            print("2. 日次集計処理のロジックに問題がある")
            print("3. created_atの日付フォーマットの問題")
    
    # 4. 日次集計処理をテスト実行
    print(f"\n【4】7月全体の再集計テスト")
    print("-" * 50)
    
    print("7月1日〜31日の再集計を実行します...")
    
    try:
        from rakuten_daily_aggregation import RakutenDailyAggregator
        aggregator = RakutenDailyAggregator()
        
        # 7月全体を再集計
        result = aggregator.aggregate_daily_sales("2025-07-01", "2025-07-31")
        
        if result['status'] == 'success':
            print(f"✅ 再集計完了:")
            print(f"   処理日数: {result['total_days']}日")
            print(f"   成功: {result['success_count']}日")
            print(f"   エラー: {result['error_count']}日")
            
            # 再集計後の確認
            updated_platform = supabase.table("platform_daily_sales").select(
                "*"
            ).gte("sales_date", "2025-07-01").lt("sales_date", "2025-08-01").execute()
            
            updated_data = updated_platform.data if updated_platform.data else []
            updated_total = sum(float(item.get('total_amount', 0)) for item in updated_data)
            updated_count = sum(item['order_count'] for item in updated_data)
            
            print(f"\n再集計後の結果:")
            print(f"   platform_daily_sales件数: {len(updated_data)}日分")
            print(f"   総売上: {updated_total:,.0f}円")
            print(f"   総注文数: {updated_count}件")
            
            if updated_count == len(orders):
                print("✅ 修正完了! 注文数が一致しました")
            else:
                print(f"⚠️  まだ差分があります: {len(orders) - updated_count}件")
        else:
            print(f"❌ 再集計失敗: {result['message']}")
    
    except Exception as e:
        print(f"❌ 再集計エラー: {str(e)}")
    
    print(f"\n=== 調査完了 ===")

if __name__ == "__main__":
    investigate_july_sales()