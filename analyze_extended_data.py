#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
楽天APIの拡張データを詳細分析してSKU取得方法を見つける
"""

from supabase import create_client
import json

SUPABASE_URL = "https://equrcpeifogdrxoldkpe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ"

print("=== Extended Rakuten Data Analysis ===")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

try:
    # 楽天商品で拡張データがある商品を取得
    rakuten_items = supabase.table("order_items").select("*").like("product_code", "10000%").is_("extended_rakuten_data", "not.null").limit(5).execute()
    
    if rakuten_items.data:
        print(f"Found {len(rakuten_items.data)} items with extended data:")
        
        for i, item in enumerate(rakuten_items.data, 1):
            print(f"\n--- Item {i}: {item['product_code']} ---")
            print(f"Product Name: {item['product_name'][:50]}...")
            print(f"Current rakuten_sku: {item.get('rakuten_sku', 'EMPTY')}")
            print(f"Rakuten Item Number: {item.get('rakuten_item_number', 'None')}")
            print(f"Rakuten Variant ID: {item.get('rakuten_variant_id', 'None')}")
            
            # extended_rakuten_dataの詳細を表示
            if item.get('extended_rakuten_data'):
                try:
                    extended = item['extended_rakuten_data']
                    if isinstance(extended, dict):
                        print(f"Extended Data Structure:")
                        
                        # raw_sku_dataを詳しく見る
                        if 'raw_sku_data' in extended:
                            raw_sku = extended['raw_sku_data']
                            print(f"  Raw SKU Data:")
                            print(f"    Extraction Method: {raw_sku.get('extraction_method', 'None')}")
                            print(f"    Extracted SKU: {raw_sku.get('extracted_sku', 'None')}")
                            
                            # original_sku_infoの内容を確認
                            original_info = raw_sku.get('original_sku_info', [])
                            print(f"    Original SKU Info ({len(original_info)} items):")
                            
                            for j, sku_info in enumerate(original_info):
                                print(f"      SKU {j+1}:")
                                if isinstance(sku_info, dict):
                                    for key, value in sku_info.items():
                                        print(f"        {key}: {value}")
                                else:
                                    print(f"        {sku_info}")
                        
                        # その他の有用な情報
                        print(f"  Other Extended Data:")
                        for key, value in extended.items():
                            if key != 'raw_sku_data':
                                print(f"    {key}: {value}")
                        
                except Exception as e:
                    print(f"  Error parsing extended data: {str(e)}")
            else:
                print("  No extended data")
        
        print("\n=== SKU EXTRACTION STRATEGY ===")
        print("Based on the analysis above, we should:")
        print("1. Check if variantId can be used as SKU")
        print("2. Use rakuten_item_number as primary SKU if variantId is generic")
        print("3. Combine product_code + choice_code as unique identifier")
        print("4. Update the SKU extraction logic in rakuten_api.py")
        
    else:
        print("No items with extended data found")

except Exception as e:
    print(f"ERROR: {str(e)}")

# SKU代替案の提案
print("\n=== RECOMMENDED SKU STRATEGY ===")
print("For Rakuten product management, use this combination:")
print("1. Primary SKU = rakuten_item_number (e.g., 1765, 1738)")
print("2. Variant ID = rakuten_variant_id (if available)")
print("3. Choice identifier = choice_code")
print("4. Unique product key = product_code + choice_code")
print("")
print("This approach provides all necessary information for:")
print("- Product identification")
print("- Variant management") 
print("- Inventory tracking")
print("- Order fulfillment")