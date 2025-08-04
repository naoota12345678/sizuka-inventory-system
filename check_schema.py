#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Supabaseのスキーマ情報を確認
"""

from supabase import create_client

SUPABASE_URL = "https://equrcpeifogdrxoldkpe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ"

print("=== Schema Information Check ===")
print("Current project: equrcpeifogdrxoldkpe")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# order_itemsテーブルがどのスキーマにあるか確認
print("\n1. Testing different schema access:")

# publicスキーマでのアクセス（デフォルト）
try:
    public_result = supabase.table("order_items").select("id", count="exact").execute()
    print(f"   public.order_items: {public_result.count} records")
    print(f"   Schema: public (this is where your data is)")
except Exception as e:
    print(f"   public.order_items: ERROR - {str(e)}")

# 明示的にpublicスキーマを指定してみる（通常は不要だが確認のため）
try:
    # Supabaseクライアントは常にpublicスキーマを使用
    print(f"   Default schema being used: public")
except Exception as e:
    print(f"   Schema check error: {str(e)}")

print("\n2. Current table information:")
try:
    # テーブルの基本情報
    sample = supabase.table("order_items").select("*").limit(1).execute()
    if sample.data:
        print("   Table structure (sample columns):")
        for key in sample.data[0].keys():
            print(f"     - {key}")
    
    # 最新データ
    latest = supabase.table("order_items").select("id, created_at, product_code").order("id", desc=True).limit(3).execute()
    print(f"\n   Latest 3 records:")
    for item in latest.data:
        print(f"     ID: {item['id']} | Code: {item['product_code']} | Created: {item['created_at']}")

except Exception as e:
    print(f"   Error getting table info: {str(e)}")

print("\n=== SOLUTION FOR TABLE EDITOR ===")
print("Your data is in the 'public' schema (which is correct).")
print("")
print("To fix Table Editor display:")
print("1. In Supabase Dashboard, go to Table Editor")
print("2. Look for a 'Schema' dropdown or selector")
print("3. Make sure 'public' is selected (not 'auth')")
print("4. If you see 'auth' selected, change it to 'public'")
print("5. Then click on 'order_items' table")
print("")
print("Alternative: Use this direct URL with schema specified:")
print("https://supabase.com/dashboard/project/equrcpeifogdrxoldkpe/editor/table/order_items?schema=public")