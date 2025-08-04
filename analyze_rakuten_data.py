#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
楽天データのSKUと選択肢コード取得状況を分析
"""

from supabase import create_client
import json

SUPABASE_URL = "https://equrcpeifogdrxoldkpe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ"

print("=== Rakuten Data Analysis ===")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# 1. 楽天データのSKU・選択肢コード取得状況を確認
print("1. Analyzing Rakuten data SKU and choice codes:")

try:
    # 楽天商品データ（product_codeが10000で始まる）を取得
    rakuten_data = supabase.table("order_items").select("*").like("product_code", "10000%").order("created_at", desc=True).limit(10).execute()
    
    if rakuten_data.data:
        print(f"   Found {len(rakuten_data.data)} recent Rakuten items:")
        
        choice_code_count = 0
        rakuten_sku_count = 0
        
        for i, item in enumerate(rakuten_data.data, 1):
            has_choice = bool(item.get('choice_code'))
            has_sku = bool(item.get('rakuten_sku'))
            
            if has_choice: choice_code_count += 1
            if has_sku: rakuten_sku_count += 1
            
            print(f"\n   {i}. Product Code: {item['product_code']}")
            print(f"      Product Name: {item['product_name'][:50]}...")
            print(f"      Choice Code: {'YES' if has_choice else 'NO/EMPTY'}")
            if has_choice:
                print(f"        Content: {item['choice_code'][:100]}...")
            print(f"      Rakuten SKU: {'YES' if has_sku else 'NO/EMPTY'}")
            if has_sku:
                print(f"        Content: {item['rakuten_sku']}")
            print(f"      Rakuten Item Number: {item.get('rakuten_item_number', 'None')}")
            
            # extended_rakuten_dataの中身を確認
            if item.get('extended_rakuten_data'):
                try:
                    extended_data = item['extended_rakuten_data']
                    if isinstance(extended_data, dict):
                        raw_sku = extended_data.get('raw_sku_data', {})
                        print(f"      Raw SKU Method: {raw_sku.get('extraction_method', 'Unknown')}")
                        print(f"      Extracted SKU: {raw_sku.get('extracted_sku', 'None')}")
                except:
                    pass
        
        print(f"\n   Summary:")
        print(f"   - Items with choice_code: {choice_code_count}/{len(rakuten_data.data)}")
        print(f"   - Items with rakuten_sku: {rakuten_sku_count}/{len(rakuten_data.data)}")
        
    else:
        print("   No Rakuten data found")

except Exception as e:
    print(f"   ERROR: {str(e)}")

# 2. 実際に楽天APIから最新データを同期して確認
print("\n2. Testing live Rakuten API data extraction:")
print("   Checking if the issue is in the API extraction logic...")

# 実際の楽天APIの応答例を確認するため、Cloud RunのデバッグAPIを呼び出し
print("   You can test live data by calling:")
print("   https://sizuka-inventory-system-1025485420770.asia-northeast1.run.app/api/debug_rakuten_sync")

print("\n=== DIAGNOSIS ===")
print("If choice_code shows 'YES' but rakuten_sku shows 'NO/EMPTY':")
print("1. Choice codes are being extracted correctly")
print("2. SKU extraction logic needs investigation")
print("3. This might be due to Rakuten API not providing SKU data in the expected format")
print("")
print("The rakuten_item_number (商品番号) might be the actual 'SKU' you need.")
print("Many Rakuten merchants use item_number as their primary SKU identifier.")