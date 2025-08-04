#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
データの信頼性・整合性を検証
テストデータや重複データの検出
"""

from supabase import create_client
from collections import Counter
import json

SUPABASE_URL = "https://equrcpeifogdrxoldkpe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ"

def verify_data_integrity():
    """データの整合性を包括的に検証"""
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    print("=== データ信頼性検証 ===\n")
    
    # 1. 全ordersデータ取得
    print("【1】全ordersデータの基本統計:")
    all_orders = supabase.table("orders").select(
        "id, created_at, total_amount, customer_name, order_status"
    ).execute()
    orders = all_orders.data
    
    print(f"総注文数: {len(orders)}件")
    
    # 2. 時間帯分析
    print("\n【2】時間帯別分析:")
    hourly_count = Counter()
    daily_count = Counter()
    
    for order in orders:
        created_at = order["created_at"]
        if "T" in created_at and ":" in created_at:
            # 日付
            date = created_at.split("T")[0]
            daily_count[date] += 1
            
            # 時間
            time_part = created_at.split("T")[1]
            hour = time_part[:2] if len(time_part) > 2 else "00"
            hourly_count[hour] += 1
    
    print("異常な時間帯（100件以上）:")
    for hour, count in hourly_count.most_common():
        if count >= 100:
            print(f"  {hour}時台: {count}件 {'⚠️ 異常' if count > 200 else ''}")
    
    print(f"\n日別集中度:")
    for date, count in daily_count.most_common(5):
        avg_per_hour = count / 24
        print(f"  {date}: {count}件 (時間平均: {avg_per_hour:.1f}件)")
    
    # 3. 金額分析
    print("\n【3】金額分析:")
    amounts = [float(order["total_amount"]) for order in orders]
    amount_counter = Counter(amounts)
    
    print("同一金額の重複（10回以上）:")
    for amount, count in amount_counter.most_common():
        if count >= 10:
            print(f"  {amount:,.0f}円: {count}回 {'⚠️ 異常' if count > 20 else ''}")
    
    # 4. 顧客名分析
    print("\n【4】顧客名分析:")
    customer_names = [order.get("customer_name", "") for order in orders]
    name_counter = Counter(customer_names)
    
    print("同一顧客名の重複（5回以上）:")
    for name, count in name_counter.most_common():
        if count >= 5 and name:
            print(f"  '{name}': {count}回")
    
    # 5. タイムスタンプ間隔分析
    print("\n【5】8月3日のタイムスタンプ間隔分析:")
    aug3_orders = [o for o in orders if o["created_at"].startswith("2025-08-03")]
    aug3_orders.sort(key=lambda x: x["created_at"])
    
    if len(aug3_orders) >= 2:
        intervals = []
        for i in range(1, min(21, len(aug3_orders))):  # 最初の20件の間隔
            prev_time = aug3_orders[i-1]["created_at"]
            curr_time = aug3_orders[i]["created_at"]
            
            try:
                from datetime import datetime
                prev_dt = datetime.fromisoformat(prev_time.replace('Z', '+00:00'))
                curr_dt = datetime.fromisoformat(curr_time.replace('Z', '+00:00'))
                interval = (curr_dt - prev_dt).total_seconds()
                intervals.append(interval)
            except:
                continue
        
        if intervals:
            avg_interval = sum(intervals) / len(intervals)
            print(f"最初20件の平均間隔: {avg_interval:.2f}秒")
            print(f"最短間隔: {min(intervals):.2f}秒")
            print(f"最長間隔: {max(intervals):.2f}秒")
            
            if avg_interval < 1.0:
                print("⚠️ 異常: 平均間隔が1秒未満（機械的投入の可能性）")
    
    # 6. 注文ID連続性チェック
    print("\n【6】注文ID連続性チェック:")
    order_ids = [int(order["id"]) for order in orders if order["id"].isdigit()]
    order_ids.sort()
    
    if order_ids:
        print(f"注文ID範囲: {min(order_ids)} ～ {max(order_ids)}")
        
        gaps = []
        for i in range(1, len(order_ids)):
            if order_ids[i] - order_ids[i-1] > 1:
                gaps.append((order_ids[i-1], order_ids[i]))
        
        if gaps:
            print(f"ID欠番: {len(gaps)}箇所")
            for start, end in gaps[:5]:  # 最初の5箇所
                print(f"  {start} → {end} (欠番: {end-start-1}件)")
    
    # 7. テストデータの検出
    print("\n【7】テストデータ検出:")
    test_indicators = [
        "test", "テスト", "TEST", "sample", "サンプル", 
        "dummy", "ダミー", "debug", "デバッグ", "example"
    ]
    
    test_orders = []
    for order in orders:
        customer_name = order.get("customer_name", "").lower()
        if any(indicator.lower() in customer_name for indicator in test_indicators):
            test_orders.append(order)
    
    if test_orders:
        print(f"テストデータ疑い: {len(test_orders)}件")
        for order in test_orders[:5]:
            print(f"  注文{order['id']}: {order.get('customer_name', 'N/A')}")
    else:
        print("明確なテストデータは検出されず")
    
    # 8. 結論
    print("\n【8】データ信頼性の結論:")
    
    issues = []
    if max(hourly_count.values()) > 200:
        issues.append("異常な時間集中あり")
    if max(amount_counter.values()) > 20:
        issues.append("同一金額の異常重複あり")
    if avg_interval < 1.0 if 'avg_interval' in locals() else False:
        issues.append("機械的投入パターンあり")
    if test_orders:
        issues.append("テストデータ混入の可能性")
    
    if issues:
        print("⚠️ データ信頼性に問題があります:")
        for issue in issues:
            print(f"   - {issue}")
        print()
        print("推奨対応:")
        print("1. 8月3日のデータ（545件）の精査")
        print("2. テストデータの除外")
        print("3. 楽天API同期処理の確認")
        print("4. 本番データと開発データの分離")
    else:
        print("✅ データは正常です")
    
    # 9. 8月3日データの詳細レポート
    print("\n【9】8月3日データの詳細レポート:")
    print(f"8月3日の注文数: {len(aug3_orders)}件")
    
    if aug3_orders:
        amounts_aug3 = [float(o["total_amount"]) for o in aug3_orders]
        total_aug3 = sum(amounts_aug3)
        avg_aug3 = total_aug3 / len(amounts_aug3)
        
        print(f"8月3日総売上: {total_aug3:,.0f}円")
        print(f"8月3日平均単価: {avg_aug3:,.0f}円")
        print(f"最初の注文: {aug3_orders[0]['created_at']}")
        print(f"最後の注文: {aug3_orders[-1]['created_at']}")
        
        # 時間範囲
        from datetime import datetime
        try:
            first_time = datetime.fromisoformat(aug3_orders[0]["created_at"].replace('Z', '+00:00'))
            last_time = datetime.fromisoformat(aug3_orders[-1]["created_at"].replace('Z', '+00:00'))
            duration = (last_time - first_time).total_seconds() / 60
            print(f"投入期間: {duration:.0f}分間")
            print(f"分間平均: {len(aug3_orders) / duration * 60:.1f}件/時間")
        except:
            pass
    
    return {
        "total_orders": len(orders),
        "issues_found": len(issues),
        "aug3_orders": len(aug3_orders),
        "hourly_peak": max(hourly_count.values()) if hourly_count else 0,
        "test_data_count": len(test_orders)
    }

if __name__ == "__main__":
    result = verify_data_integrity()