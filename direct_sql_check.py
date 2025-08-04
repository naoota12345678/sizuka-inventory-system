#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Supabaseに直接SQLクエリを実行して確認
"""

from supabase import create_client
import json

# 正しいSupabaseプロジェクト設定
SUPABASE_URL = "https://equrcpeifogdrxoldkpe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ"

print("=== Direct Supabase Query ===")
print(f"Project: rakuten-sales-data")
print(f"URL: {SUPABASE_URL}")

# Create client
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# 1. 最も新しいデータを1件だけ取得
print("\n1. Most recent order_item:")
try:
    result = supabase.table("order_items").select("id, created_at, product_code, product_name").order("created_at", desc=True).limit(1).execute()
    if result.data:
        item = result.data[0]
        print(f"   ID: {item['id']}")
        print(f"   Created: {item['created_at']}")
        print(f"   Code: {item['product_code']}")
        print(f"   Name: {item['product_name'][:30]}...")
    else:
        print("   No data found")
except Exception as e:
    print(f"   Error: {str(e)}")

# 2. 日付でグループ化してカウント
print("\n2. Count by date (created_at):")
try:
    # 2025年7月31日のデータ
    july_result = supabase.table("order_items").select("id", count="exact").gte("created_at", "2025-07-31").lt("created_at", "2025-08-01").execute()
    print(f"   2025-07-31: {july_result.count} items")
    
    # 2025年8月3日のデータ
    aug_result = supabase.table("order_items").select("id", count="exact").gte("created_at", "2025-08-03").lt("created_at", "2025-08-04").execute()
    print(f"   2025-08-03: {aug_result.count} items")
    
except Exception as e:
    print(f"   Error: {str(e)}")

# 3. 最新のテストデータを確認
print("\n3. Test data check:")
try:
    test_result = supabase.table("order_items").select("*").ilike("product_code", "%TEST%").order("created_at", desc=True).limit(5).execute()
    if test_result.data:
        print(f"   Found {len(test_result.data)} test items")
        for item in test_result.data:
            print(f"   - {item['product_code']}: {item['product_name'][:30]}... (created: {item['created_at']})")
    else:
        print("   No test data found")
except Exception as e:
    print(f"   Error: {str(e)}")

# 4. 手動でデータを挿入してみる
print("\n4. Manual data insertion test:")
try:
    import datetime
    test_data = {
        "order_id": 1,  # 仮のorder_id
        "product_code": f"MANUAL_TEST_{datetime.datetime.now().strftime('%H%M%S')}",
        "product_name": f"Manual Test at {datetime.datetime.now()}",
        "quantity": 1,
        "price": 100,
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }
    
    insert_result = supabase.table("order_items").insert(test_data).execute()
    if insert_result.data:
        print(f"   SUCCESS: Inserted item with ID {insert_result.data[0]['id']}")
        print(f"   Product code: {insert_result.data[0]['product_code']}")
    else:
        print("   FAILED: Could not insert data")
except Exception as e:
    print(f"   Error: {str(e)}")

print("\n=== END ===")
print("If you see data above, the connection is working correctly.")
print("Please check your Supabase dashboard and refresh the page.")