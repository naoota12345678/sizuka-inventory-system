#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
シンプルなテーブル確認
"""

from supabase import create_client

SUPABASE_URL = "https://equrcpeifogdrxoldkpe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ"

print("=== Simple Table Check ===")
print(f"Project: equrcpeifogdrxoldkpe")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

print("\n1. order_items table check:")
try:
    result = supabase.table("order_items").select("*").limit(1).execute()
    print("   SUCCESS: order_items table exists")
    
    count = supabase.table("order_items").select("id", count="exact").execute()
    print(f"   Total records: {count.count}")
    
    latest = supabase.table("order_items").select("id, created_at").order("id", desc=True).limit(1).execute()
    if latest.data:
        print(f"   Latest ID: {latest.data[0]['id']}")
        print(f"   Latest created: {latest.data[0]['created_at']}")
    
except Exception as e:
    print(f"   ERROR: {str(e)}")

print("\n2. Check for hyphenated table name:")
try:
    hyphen_result = supabase.table("order-items").select("*").limit(1).execute()
    print("   WARNING: Found 'order-items' table (with hyphen)!")
    hyphen_count = supabase.table("order-items").select("id", count="exact").execute()
    print(f"   Records in 'order-items': {hyphen_count.count}")
except Exception as e:
    print("   No 'order-items' table found (good)")

print("\n3. Manual data insertion test:")
try:
    import datetime
    test_data = {
        "order_id": 1,
        "product_code": f"FINAL_TEST_{datetime.datetime.now().strftime('%H%M%S')}",
        "product_name": "Final Test Product",
        "quantity": 1,
        "price": 999,
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }
    
    insert_result = supabase.table("order_items").insert(test_data).execute()
    if insert_result.data:
        print(f"   SUCCESS: Inserted test data with ID {insert_result.data[0]['id']}")
        print(f"   Test product code: {insert_result.data[0]['product_code']}")
    else:
        print("   FAILED: Could not insert test data")
except Exception as e:
    print(f"   ERROR: {str(e)}")

print("\n=== END ===")
print("Check your Supabase Table Editor now for the test data.")
print("Direct URL: https://supabase.com/dashboard/project/equrcpeifogdrxoldkpe/editor/table/order_items")