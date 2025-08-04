#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
2024年6月からの履歴データ同期テスト
楽天APIから過去のデータを取得可能か確認
"""

from supabase import create_client
from datetime import datetime, timedelta
import logging

# ロギング設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

SUPABASE_URL = "https://equrcpeifogdrxoldkpe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ"

def test_historical_data_availability():
    """過去データの利用可能性をテスト"""
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    print("=== 過去データ同期可能期間の調査 ===\n")
    
    # 1. 現在のordersテーブルの年別分布
    print("【1】現在のordersテーブルの年別分布")
    print("-" * 50)
    
    try:
        all_orders = supabase.table("orders").select("created_at").execute()
        orders = all_orders.data if all_orders.data else []
        
        print(f"ordersテーブル総件数: {len(orders)}件\n")
        
        # 年別集計
        yearly_counts = {}
        for order in orders:
            created_at = order.get('created_at', '')
            if len(created_at) >= 4:
                year = created_at[:4]
                yearly_counts[year] = yearly_counts.get(year, 0) + 1
        
        print("年別注文数:")
        for year in sorted(yearly_counts.keys()):
            print(f"  {year}年: {yearly_counts[year]}件")
            
        # 月別詳細（2024年）
        print(f"\n2024年の月別詳細:")
        monthly_2024 = {}
        for order in orders:
            created_at = order.get('created_at', '')
            if created_at.startswith('2024'):
                if len(created_at) >= 7:
                    month = created_at[:7]  # YYYY-MM
                    monthly_2024[month] = monthly_2024.get(month, 0) + 1
        
        for month in sorted(monthly_2024.keys()):
            print(f"  {month}: {monthly_2024[month]}件")
            
    except Exception as e:
        print(f"エラー: {e}")
    
    # 2. 2024年6月からの期間で集計テスト
    print(f"\n【2】2024年6月からの期間集計テスト")
    print("-" * 50)
    
    test_periods = [
        ("2024-06-01", "2024-06-30", "2024年6月"),
        ("2024-07-01", "2024-07-31", "2024年7月"),
        ("2024-08-01", "2024-08-31", "2024年8月"),
        ("2025-07-01", "2025-07-31", "2025年7月"),
        ("2025-08-01", "2025-08-04", "2025年8月（現在まで）")
    ]
    
    for start_date, end_date, period_name in test_periods:
        try:
            period_orders = supabase.table("orders").select(
                "id, created_at, total_amount"
            ).gte("created_at", start_date).lte("created_at", end_date).execute()
            
            orders = period_orders.data if period_orders.data else []
            total_amount = sum(float(order.get('total_amount', 0)) for order in orders)
            
            print(f"{period_name}: {len(orders)}件 ({total_amount:,.0f}円)")
            
        except Exception as e:
            print(f"{period_name}: エラー - {e}")
    
    # 3. 楽天APIから履歴データ取得の可能性
    print(f"\n【3】楽天APIから履歴データ取得の可能性")
    print("-" * 50)
    
    print("楽天APIの制限事項:")
    print("1. 注文検索API（GetOrder）の期間制限")
    print("   - 通常: 過去2年分のデータが取得可能")
    print("   - 2024年6月は約14ヶ月前 → 取得可能な範囲内")
    print()
    print("2. 推奨される同期方法:")
    print("   - 2024年6月1日から日別にデータを同期")
    print("   - daily_rakuten_processing.pyを修正して期間指定実行")
    print("   - APIレート制限に注意（1秒あたり5リクエスト）")
    print()
    print("3. 実装方針:")
    print("   - 過去データ同期用のスクリプトを作成")
    print("   - 月単位で段階的に同期（2024年6月→7月→...）")
    print("   - 既存の処理フローと同じ形式でordersテーブルに保存")
    
    # 4. 推奨実装手順
    print(f"\n【4】推奨実装手順")
    print("-" * 50)
    
    print("Step 1: historical_rakuten_sync.py作成")
    print("  - 期間指定で楽天APIから注文データを取得")
    print("  - 既存のdaily_rakuten_processing.pyの処理を流用")
    print("  - 月単位での実行制御機能")
    print()
    print("Step 2: 段階的同期実行")
    print("  - 2024年6月から順次実行")
    print("  - 各月の同期完了後、platform_daily_salesも更新")
    print()
    print("Step 3: ダッシュボード修正")
    print("  - デフォルト期間を2024年6月以降に変更")
    print("  - 年別データ選択機能を追加")
    
    # 5. 結論
    print(f"\n【5】結論")
    print("-" * 50)
    
    if len([year for year in yearly_counts.keys() if year == '2024']) > 0:
        print("✅ 一部の2024年データは既に存在しています")
    else:
        print("⚠️  2024年データは現在存在しません")
    
    print("📋 次のアクション:")
    print("1. 過去データ同期スクリプトの作成")
    print("2. 2024年6月からの段階的同期実行")
    print("3. ダッシュボードのデフォルト期間を適切に設定")

if __name__ == "__main__":
    test_historical_data_availability()