#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日次売上集計の詳細検証
手動集計 vs 自動集計の比較で正確性を確認
"""

from supabase import create_client

SUPABASE_URL = "https://equrcpeifogdrxoldkpe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ"

def verify_daily_sales():
    """日次売上集計の検証"""
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    print("=== 日次売上集計の詳細検証 ===\n")
    
    # 1. 全期間のordersデータを日別集計（手動計算）
    print("【1】ordersテーブルから手動で日別集計:")
    all_orders = supabase.table("orders").select("created_at, total_amount").execute()
    orders = all_orders.data
    
    daily_manual = {}
    for order in orders:
        created_at = order["created_at"]
        if "T" in created_at:
            date = created_at.split("T")[0]
        else:
            date = created_at[:10]
        
        amount = float(order["total_amount"])
        if date not in daily_manual:
            daily_manual[date] = {"amount": 0, "count": 0}
        daily_manual[date]["amount"] += amount
        daily_manual[date]["count"] += 1
    
    print("手動集計結果（最新10日）:")
    for date in sorted(daily_manual.keys())[-10:]:
        data = daily_manual[date]
        avg = data["amount"] / data["count"] if data["count"] > 0 else 0
        print(f"  {date}: {data['amount']:,.0f}円 ({data['count']}件) [平均: {avg:,.0f}円]")
    
    print()
    
    # 2. platform_daily_salesの集計データ
    print("【2】platform_daily_salesの集計データ:")
    platform_data = supabase.table("platform_daily_sales").select("*").order("sales_date").execute()
    
    print("集計済みデータ:")
    for item in platform_data.data:
        amount = float(item["total_amount"])
        count = int(item["order_count"])
        avg = amount / count if count > 0 else 0
        print(f"  {item['sales_date']}: {amount:,.0f}円 ({count}件) [平均: {avg:,.0f}円]")
    
    print()
    
    # 3. 差分チェック
    print("【3】手動集計 vs 自動集計の差分チェック:")
    platform_dict = {}
    for item in platform_data.data:
        platform_dict[item["sales_date"]] = {
            "amount": float(item["total_amount"]),
            "count": int(item["order_count"])
        }
    
    discrepancies = []
    for date in daily_manual.keys():
        manual = daily_manual[date]
        auto = platform_dict.get(date, {"amount": 0, "count": 0})
        
        amount_diff = manual["amount"] - auto["amount"]
        count_diff = manual["count"] - auto["count"]
        
        if abs(amount_diff) > 1 or count_diff != 0:  # 1円以上または件数差異
            discrepancies.append({
                "date": date,
                "manual_amount": manual["amount"],
                "auto_amount": auto["amount"],
                "amount_diff": amount_diff,
                "manual_count": manual["count"],
                "auto_count": auto["count"],
                "count_diff": count_diff
            })
    
    if discrepancies:
        print("問題発見: 差分があります")
        for disc in discrepancies:
            print(f"  {disc['date']}:")
            print(f"    手動: {disc['manual_amount']:,.0f}円 ({disc['manual_count']}件)")
            print(f"    自動: {disc['auto_amount']:,.0f}円 ({disc['auto_count']}件)")
            print(f"    差分: {disc['amount_diff']:,.0f}円 ({disc['count_diff']}件)")
            print()
    else:
        print("✅ 差分なし: 手動集計と自動集計が完全に一致")
    
    print()
    
    # 4. 合計値の検証
    print("【4】合計値の検証:")
    manual_total_amount = sum(data["amount"] for data in daily_manual.values())
    manual_total_count = sum(data["count"] for data in daily_manual.values())
    
    auto_total_amount = sum(float(item["total_amount"]) for item in platform_data.data)
    auto_total_count = sum(int(item["order_count"]) for item in platform_data.data)
    
    print(f"手動集計合計: {manual_total_amount:,.0f}円 ({manual_total_count}件)")
    print(f"自動集計合計: {auto_total_amount:,.0f}円 ({auto_total_count}件)")
    print(f"差分: {manual_total_amount - auto_total_amount:,.0f}円 ({manual_total_count - auto_total_count}件)")
    
    if abs(manual_total_amount - auto_total_amount) < 1 and manual_total_count == auto_total_count:
        print("✅ 合計値一致: 集計は正確です")
        accuracy = True
    else:
        print("❌ 合計値不一致: 集計に問題があります")
        accuracy = False
    
    print()
    
    # 5. 集計欠損の確認
    print("【5】集計欠損の確認:")
    missing_dates = []
    for date in daily_manual.keys():
        if date not in platform_dict:
            missing_dates.append(date)
    
    if missing_dates:
        print("未集計の日付:")
        for date in missing_dates:
            data = daily_manual[date]
            print(f"  {date}: {data['amount']:,.0f}円 ({data['count']}件) - 未集計")
    else:
        print("✅ 集計欠損なし: すべての日付が集計済み")
    
    # 6. 結論
    print("\n【6】結論:")
    if accuracy and not discrepancies and not missing_dates:
        print("✅ 日次売上集計は完全に正確です")
        print("   - 手動集計と自動集計が100%一致")
        print("   - 集計欠損なし")
        print("   - APIから正しくデータ取得・集計されています")
    else:
        print("⚠️  日次売上集計に問題があります:")
        if discrepancies:
            print(f"   - {len(discrepancies)}日分の差分あり")
        if missing_dates:
            print(f"   - {len(missing_dates)}日分の集計欠損")
        print("   - 再集計が必要です")
    
    return {
        "accuracy": accuracy,
        "discrepancies": len(discrepancies),
        "missing_dates": len(missing_dates),
        "total_manual": {"amount": manual_total_amount, "count": manual_total_count},
        "total_auto": {"amount": auto_total_amount, "count": auto_total_count}
    }

if __name__ == "__main__":
    result = verify_daily_sales()