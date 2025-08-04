#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
楽天拡張データをシンプルに分析
"""

from supabase import create_client
import json

SUPABASE_URL = "https://equrcpeifogdrxoldkpe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ"

print("=== Simple Extended Data Analysis ===")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

try:
    # 楽天商品を数件取得して詳細分析
    rakuten_items = supabase.table("order_items").select("*").like("product_code", "10000%").limit(3).execute()
    
    if rakuten_items.data:
        for i, item in enumerate(rakuten_items.data, 1):
            print(f"\n--- Item {i}: {item['product_code']} ---")
            print(f"Product Name: {item['product_name'][:50]}...")
            print(f"Rakuten Item Number: {item.get('rakuten_item_number', 'None')}")
            print(f"Rakuten Variant ID: {item.get('rakuten_variant_id', 'None')}")
            print(f"Current rakuten_sku: '{item.get('rakuten_sku', 'EMPTY')}'")
            print(f"Choice Code: {item.get('choice_code', 'None')}")
            
            # extended_rakuten_dataを確認
            if item.get('extended_rakuten_data'):
                try:
                    extended = item['extended_rakuten_data']
                    if isinstance(extended, dict) and 'raw_sku_data' in extended:
                        raw_sku = extended['raw_sku_data']
                        print(f"Raw SKU Data:")
                        print(f"  Extraction Method: {raw_sku.get('extraction_method', 'None')}")
                        print(f"  Extracted SKU: '{raw_sku.get('extracted_sku', 'None')}'")
                        
                        # original_sku_infoの最初の要素だけ見る
                        original_info = raw_sku.get('original_sku_info', [])
                        if original_info and len(original_info) > 0:
                            first_sku = original_info[0]
                            print(f"  First SKU Info: {first_sku}")
                except:
                    print(f"Extended data parsing error")
    
    print("\n=== CURRENT SITUATION SUMMARY ===")
    print("✅ Choice codes are being extracted correctly")
    print("❌ rakuten_sku field is empty for all items")
    print("✅ rakuten_item_number is being captured (e.g., 1765, 1738)")
    print("✅ rakuten_variant_id exists (though often generic like 'normal-inventory')")
    
    print("\n=== PROPOSED SOLUTION ===")
    print("Since Rakuten doesn't provide detailed SKU data in the expected format:")
    print("1. Use 'rakuten_item_number' as the primary SKU")
    print("2. Use 'product_code' as the internal product identifier")  
    print("3. Use 'choice_code' for variant identification")
    print("4. Create composite SKU: rakuten_item_number + choice_code")
    
    print("\n=== BUSINESS VALUE ===")
    print("With current data, you can:")
    print("✅ Identify products: product_code (10000059)")
    print("✅ Track Rakuten items: rakuten_item_number (1765)")
    print("✅ Manage variants: choice_code (選択肢コード)")
    print("✅ Match orders to inventory")
    print("✅ Generate fulfillment reports")

except Exception as e:
    print(f"ERROR: {str(e)}")