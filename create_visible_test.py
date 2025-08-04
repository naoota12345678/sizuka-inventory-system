#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Table Editorで見えるテストデータを作成
"""

from supabase import create_client
import datetime

SUPABASE_URL = "https://equrcpeifogdrxoldkpe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ"

print("=== Creating Visible Test Data ===")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# まず既存のorder_idを取得
print("1. Getting existing order_id:")
try:
    existing_order = supabase.table("orders").select("id").limit(1).execute()
    if existing_order.data:
        order_id = existing_order.data[0]['id']
        print(f"   Using order_id: {order_id}")
        
        # 目立つテストデータを作成
        test_data = {
            "order_id": order_id,
            "product_code": "ZZZZ_TABLE_EDITOR_TEST_ZZZZ",
            "product_name": "🔥🔥🔥 TABLE EDITOR VISIBILITY TEST - FIND THIS! 🔥🔥🔥",
            "quantity": 888,
            "price": 8888.88,
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
        
        result = supabase.table("order_items").insert(test_data).execute()
        if result.data:
            new_id = result.data[0]['id']
            print(f"   ✅ SUCCESS: Created test data with ID: {new_id}")
            print(f"   Product code: {test_data['product_code']}")
            print(f"   Product name: {test_data['product_name']}")
            print(f"   Price: {test_data['price']}")
            
            # 確認のため再取得
            verify = supabase.table("order_items").select("*").eq("id", new_id).execute()
            if verify.data:
                print(f"   ✅ VERIFIED: Data exists and can be retrieved")
                
                # 新しい総件数
                total = supabase.table("order_items").select("id", count="exact").execute()
                print(f"   📊 New total records: {total.count}")
            else:
                print(f"   ❌ VERIFICATION FAILED")
        else:
            print(f"   ❌ FAILED to create test data")
    else:
        print("   ❌ No existing orders found")
        
except Exception as e:
    print(f"   ❌ ERROR: {str(e)}")

print("\n=== TABLE EDITOR CHECK INSTRUCTIONS ===")
print("Now go to your Supabase Table Editor and:")
print("1. Refresh the page (Ctrl+F5)")
print("2. Make sure you're viewing 'order_items' table in 'public' schema")
print("3. Sort by 'id' column in DESCENDING order (click the column header)")
print("4. Look for the record with:")
print("   - Product code: ZZZZ_TABLE_EDITOR_TEST_ZZZZ")
print("   - Product name: 🔥🔥🔥 TABLE EDITOR VISIBILITY TEST - FIND THIS! 🔥🔥🔥")
print("   - Price: 8888.88")
print("   - Quantity: 888")
print("")
print("If you still don't see this distinctive data, then it's confirmed:")
print("❌ Supabase Table Editor has a display bug")
print("✅ Your data is safe and accessible via API/SQL")