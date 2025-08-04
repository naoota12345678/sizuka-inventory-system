#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
データ整合性修正案
8月3日の異常データを除外し、正確な売上分析を実現
"""

from supabase import create_client

SUPABASE_URL = "https://equrcpeifogdrxoldkpe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ"

def propose_data_fix():
    """データ修正案の提案"""
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    print("=== データ整合性修正案 ===\n")
    
    # 現在の状況確認
    print("【現在の状況】")
    all_orders = supabase.table("orders").select("created_at, total_amount").execute()
    total_orders = len(all_orders.data)
    total_amount = sum(float(o["total_amount"]) for o in all_orders.data)
    
    aug3_orders = [o for o in all_orders.data if o["created_at"].startswith("2025-08-03")]
    aug3_count = len(aug3_orders)
    aug3_amount = sum(float(o["total_amount"]) for o in aug3_orders)
    
    other_orders = total_orders - aug3_count
    other_amount = total_amount - aug3_amount
    
    print(f"全体: {total_orders}件、{total_amount:,.0f}円")
    print(f"8月3日: {aug3_count}件、{aug3_amount:,.0f}円 (異常データ)")
    print(f"その他: {other_orders}件、{other_amount:,.0f}円 (正常データ)")
    print()
    
    # 修正案1: フラグベース除外
    print("【修正案1】フラグベース除外 (推奨)")
    print("ordersテーブルにis_test_dataカラムを追加し、異常データにフラグを設定")
    print("メリット:")
    print("- データを物理削除せず、後で復元可能")
    print("- 集計時にWHERE is_test_data = false で除外")
    print("- 安全で可逆的な対応")
    print()
    
    # 修正案2: 別テーブル移動
    print("【修正案2】別テーブル移動")
    print("test_ordersテーブルを作成し、異常データを移動")
    print("メリット:")
    print("- 本番データと完全分離")
    print("- パフォーマンス向上")
    print()
    
    # 修正案3: 日付フィルタ
    print("【修正案3】APIレベルでの日付フィルタ")
    print("集計API内で8月3日を除外する処理を追加")
    print("メリット:")
    print("- 最も簡単で即効性あり")
    print("- データベース変更不要")
    print()
    
    # 推奨実装
    print("【推奨実装手順】")
    print("1. APIレベルでの緊急対応（即時実装）")
    print("2. is_test_dataカラム追加（長期対応）")
    print("3. データ品質チェック機能の追加")
    print()
    
    # 修正後の売上予測
    print("【修正後の売上データ】")
    print(f"正常データのみ: {other_orders}件、{other_amount:,.0f}円")
    if other_orders > 0:
        avg_per_order = other_amount / other_orders
        print(f"1件平均: {avg_per_order:,.0f}円")
        print("この数値が正しい売上指標となります")
    
    return {
        "total_orders": total_orders,
        "abnormal_orders": aug3_count,
        "normal_orders": other_orders,
        "abnormal_amount": aug3_amount,
        "normal_amount": other_amount
    }

def implement_api_filter():
    """APIレベルでの緊急フィルタ実装案"""
    print("\n=== APIフィルタ実装コード案 ===\n")
    
    filter_code = '''
# rakuten_daily_aggregation.py の修正案
def aggregate_daily_sales(self, start_date: str = None, end_date: str = None):
    """指定期間の日次売上を集計（異常データ除外）"""
    
    # 異常データの日付を除外
    EXCLUDED_DATES = ['2025-08-03']  # テストデータ日付
    
    # 期間内の注文データを取得
    orders_response = self.supabase.table("orders").select(
        "created_at, total_amount"
    ).gte("created_at", start_date).lt("created_at", end_date_plus_one).execute()
    
    orders = orders_response.data if orders_response.data else []
    
    # 異常データを除外
    filtered_orders = []
    for order in orders:
        created_at = order.get('created_at', '')
        if 'T' in created_at:
            date = created_at.split('T')[0]
        else:
            date = created_at[:10]
        
        if date not in EXCLUDED_DATES:
            filtered_orders.append(order)
    
    logger.info(f"対象注文数: {len(orders)}件 → フィルタ後: {len(filtered_orders)}件")
    
    # 以下は既存の集計処理...
    '''
    
    print(filter_code)

if __name__ == "__main__":
    result = propose_data_fix()
    implement_api_filter()