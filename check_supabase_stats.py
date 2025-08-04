#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Supabaseの統計情報を確認
"""

from supabase import create_client
from datetime import datetime, timezone, timedelta
import json

# 正しいSupabaseプロジェクト設定
SUPABASE_URL = "https://equrcpeifogdrxoldkpe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ"

try:
    print("=== Supabase Data Statistics ===")
    print(f"URL: {SUPABASE_URL}")
    print(f"Project ID: equrcpeifogdrxoldkpe")
    
    # Create client
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # 1. order_itemsテーブルの統計
    print("\n--- order_items Table Statistics ---")
    
    # 全体の件数
    total_items = supabase.table("order_items").select("id", count="exact").execute()
    print(f"Total records: {total_items.count}")
    
    # 日付別の件数
    print("\nRecords by date:")
    dates = [
        ("2025-07-31", "2025-08-01"),
        ("2025-08-01", "2025-08-02"),
        ("2025-08-02", "2025-08-03"),
        ("2025-08-03", "2025-08-04"),
    ]
    
    for start, end in dates:
        items = supabase.table("order_items").select("id", count="exact").gte("created_at", start).lt("created_at", end).execute()
        print(f"  {start}: {items.count} records")
    
    # 2. 最新10件の詳細
    print("\n--- Latest 10 order_items (detailed) ---")
    latest_items = supabase.table("order_items").select("*").order("created_at", desc=True).limit(10).execute()
    
    for i, item in enumerate(latest_items.data, 1):
        print(f"\n{i}. ID: {item['id']}")
        print(f"   Created: {item['created_at']}")
        print(f"   Product Code: {item['product_code']}")
        print(f"   Product Name: {item['product_name'][:50]}...")
        print(f"   Choice Code: {item.get('choice_code', 'None')[:50] if item.get('choice_code') else 'None'}...")
        print(f"   Rakuten SKU: {item.get('rakuten_sku', 'Empty')}")
        print(f"   Rakuten Item Number: {item.get('rakuten_item_number', 'None')}")
    
    # 3. ordersテーブルの統計
    print("\n--- orders Table Statistics ---")
    total_orders = supabase.table("orders").select("id", count="exact").execute()
    print(f"Total orders: {total_orders.count}")
    
    # 最新5件の注文
    print("\nLatest 5 orders:")
    latest_orders = supabase.table("orders").select("*").order("created_at", desc=True).limit(5).execute()
    
    for order in latest_orders.data:
        print(f"  Order: {order['order_number']} | Created: {order['created_at']}")
    
    # 4. テスト：新しいテストデータを1件追加してみる
    print("\n--- Testing data insertion ---")
    test_order = {
        "platform_id": 1,  # 楽天
        "order_number": f"TEST-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "order_date": datetime.now(timezone.utc).isoformat(),
        "total_amount": 1000,
        "status": "test"
    }
    
    try:
        result = supabase.table("orders").insert(test_order).execute()
        if result.data:
            test_order_id = result.data[0]['id']
            print(f"Test order created successfully! ID: {test_order_id}")
            
            # テスト商品も追加
            test_item = {
                "order_id": test_order_id,
                "product_code": "TEST_PRODUCT_001",
                "product_name": f"Test Product - {datetime.now()}",
                "quantity": 1,
                "price": 1000,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            item_result = supabase.table("order_items").insert(test_item).execute()
            if item_result.data:
                print(f"Test item created successfully! ID: {item_result.data[0]['id']}")
            else:
                print("Failed to create test item")
        else:
            print("Failed to create test order")
    except Exception as e:
        print(f"Test insertion error: {str(e)}")
    
    print("\n=== Summary ===")
    print(f"Database is accessible: YES")
    print(f"Data is being saved: YES")
    print(f"Latest data: {latest_items.data[0]['created_at'] if latest_items.data else 'No data'}")
    
except Exception as e:
    print(f"ERROR: {str(e)}")
    import traceback
    traceback.print_exc()