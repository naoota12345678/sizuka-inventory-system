#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
最終的なデバッグ確認
"""

from supabase import create_client
import json

SUPABASE_URL = "https://equrcpeifogdrxoldkpe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ"

print("=== Final Debug Check ===")
print(f"Project: equrcpeifogdrxoldkpe")
print(f"URL: {SUPABASE_URL}")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# 非常に特殊なテストデータを作成して、Table Editorで見つけやすくする
print("\n1. Creating distinctive test data:")
try:
    import datetime
    
    # 非常に目立つデータを作成
    distinctive_data = {
        "order_id": 999,
        "product_code": "AAAAA_LOOK_FOR_THIS_AAAAA",
        "product_name": "★★★ TABLE EDITOR TEST - LOOK FOR THIS DATA ★★★",
        "quantity": 777,
        "price": 7777.77,
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }
    
    result = supabase.table("order_items").insert(distinctive_data).execute()
    if result.data:
        new_id = result.data[0]['id']
        print(f"   SUCCESS: Created distinctive test data with ID: {new_id}")
        print(f"   Product code: {distinctive_data['product_code']}")
        print(f"   Product name: {distinctive_data['product_name']}")
        print(f"   Price: {distinctive_data['price']}")
        print(f"   Quantity: {distinctive_data['quantity']}")
        print(f"   --> Go to Table Editor and look for this specific data!")
    else:
        print("   FAILED to create test data")
        
except Exception as e:
    print(f"   ERROR: {str(e)}")

# 現在の総データ数を確認
print("\n2. Current total record count:")
try:
    total = supabase.table("order_items").select("id", count="exact").execute()
    print(f"   Total records in order_items: {total.count}")
except Exception as e:
    print(f"   ERROR: {str(e)}")

# 最新の10件を表示（ID順）
print("\n3. Latest 10 records (by ID):")
try:
    latest = supabase.table("order_items").select("id, product_code, product_name, created_at").order("id", desc=True).limit(10).execute()
    for i, item in enumerate(latest.data, 1):
        print(f"   {i}. ID: {item['id']} | Code: {item['product_code']} | Name: {item['product_name'][:40]}...")
except Exception as e:
    print(f"   ERROR: {str(e)}")

print("\n=== NEXT STEPS ===")
print("1. Refresh your Table Editor page (Ctrl+F5)")
print("2. Look for the test data with ID ending in the highest number")
print("3. Search for 'AAAAA_LOOK_FOR_THIS_AAAAA' in the table")
print("4. If you still don't see it, try these Table Editor troubleshooting:")
print("   - Click the refresh button in Table Editor")
print("   - Sort by 'id' column in descending order")
print("   - Clear any filters")
print("   - Go to the last page of results")
print("")
print("If the distinctive test data above doesn't appear in Table Editor,")
print("then it's definitely a Supabase Table Editor display bug.")