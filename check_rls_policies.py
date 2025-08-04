#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
RLSポリシーとテーブル権限を確認
"""

from supabase import create_client

SUPABASE_URL = "https://equrcpeifogdrxoldkpe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ"

print("=== RLS and Permissions Check ===")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# 現在のユーザー権限で確実にデータが取得できるかテスト
print("1. Testing data access with current permissions:")
try:
    # 最新データを取得
    result = supabase.table("order_items").select("id, created_at, product_code, product_name").order("id", desc=True).limit(5).execute()
    
    if result.data:
        print(f"   SUCCESS: Retrieved {len(result.data)} records")
        for item in result.data:
            print(f"   - ID: {item['id']} | Code: {item['product_code']} | Created: {item['created_at']}")
    else:
        print("   WARNING: No data returned (but no error)")
        
except Exception as e:
    print(f"   ERROR: {str(e)}")

# 権限の詳細な情報を確認
print("\n2. Testing different query methods:")

# 方法1: 単純なselect
try:
    simple = supabase.table("order_items").select("*").limit(1).execute()
    print(f"   Simple select: {len(simple.data)} records")
except Exception as e:
    print(f"   Simple select ERROR: {str(e)}")

# 方法2: count only
try:
    count_only = supabase.table("order_items").select("*", count="exact").limit(0).execute()
    print(f"   Count only: {count_only.count} total records")
except Exception as e:
    print(f"   Count only ERROR: {str(e)}")

# 方法3: 特定のIDで検索
try:
    by_id = supabase.table("order_items").select("*").eq("id", 3011).execute()
    print(f"   By ID 3011: {len(by_id.data)} records found")
    if by_id.data:
        print(f"   Product code: {by_id.data[0]['product_code']}")
except Exception as e:
    print(f"   By ID ERROR: {str(e)}")

print("\n=== RECOMMENDATION ===")
print("If all above tests pass but Table Editor shows nothing:")
print("1. This is likely a Supabase Table Editor display bug")
print("2. Your data is safe and accessible via API")
print("3. Use SQL Editor as alternative: SELECT * FROM order_items ORDER BY id DESC;")
print("4. Consider creating a custom dashboard for data viewing")