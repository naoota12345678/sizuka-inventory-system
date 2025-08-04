#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Check order_items table structure and discount-related data
"""

from supabase import create_client
import json

SUPABASE_URL = "https://equrcpeifogdrxoldkpe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ"

print("=== Order Items Table Structure Analysis ===")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

try:
    # Get sample data to understand structure
    sample_response = supabase.table("order_items").select("*").limit(3).execute()
    
    if sample_response.data:
        print(f"Found {len(sample_response.data)} sample records")
        
        # Get all column names from first record
        first_record = sample_response.data[0]
        print(f"\nAvailable columns ({len(first_record)} total):")
        for i, column in enumerate(sorted(first_record.keys()), 1):
            print(f"{i:2d}. {column}")
        
        print("\n=== DISCOUNT/PRICE RELATED COLUMNS ===")
        price_related_columns = []
        for col in first_record.keys():
            if any(keyword in col.lower() for keyword in ['price', 'discount', 'coupon', 'point', 'amount', 'cost', 'fee']):
                price_related_columns.append(col)
                
        if price_related_columns:
            print("Found price-related columns:")
            for col in price_related_columns:
                print(f"  - {col}")
        else:
            print("No obvious price-related columns found")
        
        print("\n=== SAMPLE DATA ANALYSIS ===")
        for i, record in enumerate(sample_response.data, 1):
            print(f"\n--- Record {i} ---")
            print(f"Product Code: {record.get('product_code', 'N/A')}")
            print(f"Product Name: {record.get('product_name', 'N/A')[:50]}...")
            print(f"Price/Unit Price: {record.get('price', record.get('unit_price', 'N/A'))}")
            print(f"Quantity: {record.get('quantity', 'N/A')}")
            
            # Check for extended_rakuten_data
            if 'extended_rakuten_data' in record:
                extended_data = record['extended_rakuten_data']
                if extended_data:
                    print("Extended Rakuten Data found:")
                    if isinstance(extended_data, dict):
                        # Look for price/discount related fields
                        price_fields = {}
                        for key, value in extended_data.items():
                            if any(keyword in key.lower() for keyword in ['price', 'discount', 'coupon', 'point', 'amount', 'cost']):
                                price_fields[key] = value
                        
                        if price_fields:
                            print("  Price-related fields in extended data:")
                            for key, value in price_fields.items():
                                print(f"    {key}: {value}")
                        else:
                            print("  No price-related fields in extended data")
                            print("  Available fields:", list(extended_data.keys()))
                    else:
                        print(f"  Extended data type: {type(extended_data)}")
                else:
                    print("  Extended data is null/empty")
            else:
                print("  No extended_rakuten_data column")
        
        print("\n=== ORDER-LEVEL DISCOUNT DATA ===")
        # Check orders table for discount information
        orders_response = supabase.table("orders").select("*").limit(3).execute()
        
        if orders_response.data:
            first_order = orders_response.data[0]
            print(f"Available columns in orders table ({len(first_order)} total):")
            
            discount_columns = []
            for col in first_order.keys():
                if any(keyword in col.lower() for keyword in ['coupon', 'point', 'discount', 'campaign', 'promotion']):
                    discount_columns.append(col)
            
            if discount_columns:
                print("Found discount-related columns in orders:")
                for col in discount_columns:
                    print(f"  - {col}")
                    
                # Show sample data for discount columns
                print("\nSample discount data from orders:")
                for i, order in enumerate(orders_response.data, 1):
                    print(f"  Order {i}:")
                    for col in discount_columns:
                        print(f"    {col}: {order.get(col, 'N/A')}")
            else:
                print("No discount-related columns found in orders table")
                print("Available columns:", list(first_order.keys()))
        else:
            print("No orders found")
            
    else:
        print("No order items found")

except Exception as e:
    print(f"ERROR: {str(e)}")

print("\n=== RECOMMENDATIONS ===")
print("Based on this analysis, the system should:")
print("1. Capture discount data at order level (coupon_amount, point_amount)")
print("2. Store original_price and discount_price in extended_rakuten_data")
print("3. Calculate effective discount = original_price - actual_price")
print("4. Track campaign/promotion information in platform_data")
print("5. Consider adding discount-specific columns to order_items if needed")