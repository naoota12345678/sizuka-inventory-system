#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Check for real Rakuten order data with discount information
"""

from supabase import create_client
import json

SUPABASE_URL = "https://equrcpeifogdrxoldkpe.supabase.co"  
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ"

print("=== Real Rakuten Data Analysis ===")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

try:
    # Look for orders with non-zero coupon or point amounts
    discount_orders = supabase.table("orders").select("*").or_("coupon_amount.gt.0,point_amount.gt.0").limit(5).execute()
    
    print(f"Found {len(discount_orders.data)} orders with discounts/points")
    
    if discount_orders.data:
        for i, order in enumerate(discount_orders.data, 1):
            print(f"\n--- Discount Order {i} ---")
            print(f"Order Number: {order.get('order_number', 'N/A')}")
            print(f"Total Amount: {order.get('total_amount', 'N/A')}")
            print(f"Coupon Amount: {order.get('coupon_amount', 'N/A')}")
            print(f"Point Amount: {order.get('point_amount', 'N/A')}")
            print(f"Order Date: {order.get('order_date', 'N/A')}")
            
            # Check if platform_data contains discount info
            platform_data = order.get('platform_data')
            if platform_data:
                try:
                    if isinstance(platform_data, str):
                        platform_json = json.loads(platform_data)
                    else:
                        platform_json = platform_data
                    
                    # Look for discount-related fields in platform data
                    discount_fields = {}
                    def extract_discount_fields(obj, prefix=""):
                        if isinstance(obj, dict):
                            for key, value in obj.items():
                                if any(keyword in key.lower() for keyword in ['coupon', 'point', 'discount', 'campaign', 'promotion', 'deal']):
                                    discount_fields[f"{prefix}{key}"] = value
                                elif isinstance(value, dict):
                                    extract_discount_fields(value, f"{prefix}{key}.")
                    
                    extract_discount_fields(platform_json)
                    
                    if discount_fields:
                        print("  Discount fields in platform_data:")
                        for key, value in discount_fields.items():
                            print(f"    {key}: {value}")
                    else:
                        print("  No discount fields found in platform_data")
                        
                except Exception as e:
                    print(f"  Error parsing platform_data: {e}")
            else:
                print("  No platform_data available")
    
    # Look for order items with extended_rakuten_data containing price info
    print("\n=== ORDER ITEMS WITH PRICE DATA ===")
    items_with_extended = supabase.table("order_items").select("*").not_.is_("extended_rakuten_data", "null").limit(10).execute()
    
    print(f"Found {len(items_with_extended.data)} items with extended data")
    
    for i, item in enumerate(items_with_extended.data, 1):
        print(f"\n--- Item {i} ---")
        print(f"Product Code: {item.get('product_code', 'N/A')}")
        print(f"Current Price: {item.get('price', 'N/A')}")
        
        extended_data = item.get('extended_rakuten_data')
        if extended_data:
            try:
                if isinstance(extended_data, dict):
                    # Look for price-related fields
                    price_fields = {}
                    for key, value in extended_data.items():
                        if any(keyword in key.lower() for keyword in ['price', 'discount', 'coupon', 'point', 'amount', 'cost', 'deal']):
                            price_fields[key] = value
                    
                    if price_fields:
                        print("  Price-related fields in extended_rakuten_data:")
                        for key, value in price_fields.items():
                            print(f"    {key}: {value}")
                    else:
                        print("  No price-related fields in extended_rakuten_data")
                        print(f"  Available fields: {list(extended_data.keys())}")
                else:
                    print(f"  Extended data is not a dict: {type(extended_data)}")
            except Exception as e:
                print(f"  Error parsing extended_rakuten_data: {e}")
    
    # Check for orders from platform_id = 1 (Rakuten)
    print("\n=== RAKUTEN PLATFORM ORDERS ===")
    rakuten_orders = supabase.table("orders").select("*").eq("platform_id", 1).order("created_at", desc=True).limit(5).execute()
    
    print(f"Found {len(rakuten_orders.data)} recent Rakuten orders")
    
    for i, order in enumerate(rakuten_orders.data, 1):
        print(f"\n--- Rakuten Order {i} ---")
        print(f"Order Number: {order.get('order_number', 'N/A')}")
        print(f"Total Amount: {order.get('total_amount', 'N/A')}")
        print(f"Coupon Amount: {order.get('coupon_amount', 'N/A')}")
        print(f"Point Amount: {order.get('point_amount', 'N/A')}")
        
        # Get items for this order
        order_items = supabase.table("order_items").select("product_code,price,extended_rakuten_data").eq("order_id", order['id']).execute()
        
        print(f"  Items in order: {len(order_items.data)}")
        for item in order_items.data:
            extended = item.get('extended_rakuten_data')
            if extended and isinstance(extended, dict):
                original_price = extended.get('original_price', 'N/A')
                discount_price = extended.get('discount_price', 'N/A')
                if original_price != 'N/A' or discount_price != 'N/A':
                    print(f"    {item['product_code']}: current={item['price']}, original={original_price}, discount={discount_price}")

except Exception as e:
    print(f"ERROR: {str(e)}")

print("\n=== SUMMARY ===")
print("Current discount/campaign handling capabilities:")
print("1. Order-level: coupon_amount, point_amount fields exist")
print("2. Item-level: original_price, discount_price in extended_rakuten_data")
print("3. Platform data: Raw Rakuten API response stored in platform_data")
print("4. Missing: Campaign names, promotion codes, discount types")