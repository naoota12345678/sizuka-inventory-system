#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Supabaseのテーブル構造を詳細に確認
"""

from supabase import create_client
import json

# 正しいSupabaseプロジェクト設定
SUPABASE_URL = "https://equrcpeifogdrxoldkpe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ"

print("=== Supabase Table Structure Verification ===")
print(f"Project ID: equrcpeifogdrxoldkpe")
print(f"URL: {SUPABASE_URL}")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# 1. テーブル一覧を確認
print("\n1. Available tables:")
try:
    # schema情報を取得
    from supabase._async.client import AsyncClient
    from supabase._sync.client import SyncClient
    
    # order_itemsテーブルが存在するかチェック
    result = supabase.table("order_items").select("*").limit(1).execute()
    print("   ✅ order_items table exists")
    
    # ordersテーブルが存在するかチェック
    orders_result = supabase.table("orders").select("*").limit(1).execute()
    print("   ✅ orders table exists")
    
except Exception as e:
    print(f"   ❌ Error accessing tables: {str(e)}")

# 2. order_itemsテーブルの統計情報
print("\n2. order_items table statistics:")
try:
    # 全件数
    total_count = supabase.table("order_items").select("id", count="exact").execute()
    print(f"   Total records: {total_count.count}")
    
    # 最新5件のIDと作成日時
    latest = supabase.table("order_items").select("id, created_at, product_code").order("id", desc=True).limit(5).execute()
    print(f"   Latest 5 records:")
    for item in latest.data:
        print(f"     ID: {item['id']} | Created: {item['created_at']} | Code: {item['product_code']}")
    
    # 最古のデータ
    oldest = supabase.table("order_items").select("id, created_at, product_code").order("id", desc=False).limit(3).execute()
    print(f"   Oldest 3 records:")
    for item in oldest.data:
        print(f"     ID: {item['id']} | Created: {item['created_at']} | Code: {item['product_code']}")
    
except Exception as e:
    print(f"   ❌ Error: {str(e)}")

# 3. 別のスキーマにテーブルがあるかチェック
print("\n3. Checking for different schemas:")
try:
    # publicスキーマ以外にテーブルがあるか確認
    # これは通常のクエリでは確認できないが、存在するテーブル名を直接指定してみる
    
    # もしかして order-items (ハイフン) テーブルが存在する？
    try:
        hyphen_result = supabase.table("order-items").select("*").limit(1).execute()
        print("   ⚠️  Found 'order-items' table (with hyphen)!")
        hyphen_count = supabase.table("order-items").select("id", count="exact").execute()
        print(f"      Records in 'order-items': {hyphen_count.count}")
    except:
        print("   ✅ No 'order-items' table (with hyphen)")
    
    # orderitemsテーブル（アンダースコアなし）
    try:
        no_underscore_result = supabase.table("orderitems").select("*").limit(1).execute()
        print("   ⚠️  Found 'orderitems' table (no underscore)!")
        no_underscore_count = supabase.table("orderitems").select("id", count="exact").execute()
        print(f"      Records in 'orderitems': {no_underscore_count.count}")
    except:
        print("   ✅ No 'orderitems' table (no underscore)")
    
except Exception as e:
    print(f"   Error checking schemas: {str(e)}")

# 4. 最新データの詳細確認
print("\n4. Latest data detailed check:")
try:
    # 8月3日の最新データを詳細表示
    aug_data = supabase.table("order_items").select("*").gte("created_at", "2025-08-03").order("created_at", desc=True).limit(3).execute()
    print(f"   Found {len(aug_data.data)} records from 2025-08-03:")
    for i, item in enumerate(aug_data.data, 1):
        print(f"   {i}. ID: {item['id']}")
        print(f"      Product Code: {item['product_code']}")
        print(f"      Product Name: {item['product_name'][:50]}...")
        print(f"      Created: {item['created_at']}")
        print(f"      Choice Code: {item.get('choice_code', 'None')[:50] if item.get('choice_code') else 'None'}...")
        print()

except Exception as e:
    print(f"   Error: {str(e)}")

print("\n=== SUMMARY ===")
print("If you can see the data above but not in Table Editor:")
print("1. Try refreshing the Supabase dashboard (Ctrl+F5)")
print("2. Check if you're looking at the correct table name")
print("3. Clear browser cache and cookies")
print("4. Try accessing: https://supabase.com/dashboard/project/equrcpeifogdrxoldkpe/editor/table/order_items")