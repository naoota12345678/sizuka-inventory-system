#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
最新のorder_itemsデータを確認
"""

from supabase import create_client
from datetime import datetime, timezone, timedelta

# 正しいSupabaseプロジェクト設定
SUPABASE_URL = "https://equrcpeifogdrxoldkpe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ"

try:
    print("=== Order Items Latest Data Check ===")
    print(f"Supabase URL: {SUPABASE_URL}")
    
    # Create client
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("Supabase client created successfully")
    
    # 最新のorder_itemsを取得（created_atで降順ソート）
    print("\n--- Latest order_items (sorted by created_at DESC) ---")
    items_result = supabase.table("order_items").select("*").order("created_at", desc=True).limit(10).execute()
    
    if items_result.data:
        print(f"Found {len(items_result.data)} latest items")
        for i, item in enumerate(items_result.data, 1):
            print(f"\n{i}. Product: {item.get('product_name', 'No name')}")
            print(f"   Created: {item.get('created_at', 'Unknown')}")
            print(f"   Product Code: {item.get('product_code', 'Unknown')}")
            print(f"   Choice Code: {item.get('choice_code', 'None')}")
            print(f"   Rakuten SKU: {item.get('rakuten_sku', 'None')}")
            print(f"   Rakuten Item Number: {item.get('rakuten_item_number', 'None')}")
    else:
        print("No items found in order_items table")
    
    # 2025年8月のデータだけを取得
    print("\n--- August 2025 order_items ---")
    start_date = datetime(2025, 8, 1, 0, 0, 0, tzinfo=timezone.utc).isoformat()
    end_date = datetime(2025, 8, 31, 23, 59, 59, tzinfo=timezone.utc).isoformat()
    
    august_items = supabase.table("order_items").select("*").gte("created_at", start_date).lte("created_at", end_date).execute()
    
    if august_items.data:
        print(f"Found {len(august_items.data)} items in August 2025")
        for item in august_items.data[:5]:  # 最初の5件のみ表示
            print(f"  - {item.get('product_name')} | {item.get('created_at')}")
    else:
        print("No items found for August 2025")
    
    # 注文テーブルの最新データも確認
    print("\n--- Latest orders ---")
    orders_result = supabase.table("orders").select("*").order("created_at", desc=True).limit(5).execute()
    
    if orders_result.data:
        print(f"Found {len(orders_result.data)} latest orders")
        for order in orders_result.data:
            print(f"  - Order: {order.get('order_number')} | Date: {order.get('order_date')} | Created: {order.get('created_at')}")
    else:
        print("No orders found")
    
except Exception as e:
    print(f"ERROR: {str(e)}")
    import traceback
    traceback.print_exc()