#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
楽天データの実際の注文日を確認
8月3日のデータが本当に8月3日の注文なのかを検証
"""

from supabase import create_client
import json

SUPABASE_URL = "https://equrcpeifogdrxoldkpe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ"

def check_actual_order_dates():
    """実際の注文日を確認"""
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    print("=== 楽天データの実際の注文日確認 ===\n")
    
    # 8月3日に登録されたデータを確認
    orders = supabase.table("orders").select(
        "id, created_at, rakuten_order_data"
    ).gte("created_at", "2025-08-03").lt("created_at", "2025-08-04").limit(20).execute()
    
    if not orders.data:
        print("8月3日のデータが見つかりません")
        return
    
    print("8月3日に登録されたデータの実際の注文日:")
    print("（DB登録日 vs 実際の注文日）")
    print("-" * 50)
    
    actual_dates = {}
    
    for order in orders.data:
        order_id = order["id"]
        db_created = order["created_at"]
        
        # 楽天データから実際の注文日を取得
        rakuten_data = order.get("rakuten_order_data")
        if rakuten_data:
            try:
                data = json.loads(rakuten_data) if isinstance(rakuten_data, str) else rakuten_data
                actual_order_date = data.get("OrderDatetime", "N/A")
                
                if actual_order_date != "N/A":
                    actual_date = actual_order_date[:10]  # YYYY-MM-DD
                    actual_dates[actual_date] = actual_dates.get(actual_date, 0) + 1
                    
                    print(f"注文{order_id}: DB={db_created[:10]} / 実際={actual_date}")
                else:
                    print(f"注文{order_id}: DB={db_created[:10]} / 実際=データなし")
            except Exception as e:
                print(f"注文{order_id}: DB={db_created[:10]} / 実際=解析エラー ({str(e)[:20]})")
        else:
            print(f"注文{order_id}: DB={db_created[:10]} / 実際=楽天データなし")
    
    print(f"\n実際の注文日別の件数:")
    print("-" * 30)
    for date in sorted(actual_dates.keys()):
        count = actual_dates[date]
        print(f"{date}: {count}件")
    
    # 結論
    print(f"\n【結論】")
    if len(actual_dates) == 1 and "2025-08-03" in actual_dates:
        print("✅ 8月3日のデータは実際に8月3日の注文です")
        print("   545件すべてが8月3日の正常な売上です")
    elif len(actual_dates) > 1:
        print("⚠️  8月3日に複数日の注文が一括同期されています")
        print("   楽天API同期のタイミングに問題がある可能性")
    else:
        print("❓ 実際の注文日が特定できません")
    
    return actual_dates

if __name__ == "__main__":
    result = check_actual_order_dates()