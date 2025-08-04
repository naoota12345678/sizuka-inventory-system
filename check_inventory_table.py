#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
在庫テーブルの現在の状況を確認
"""

from supabase import create_client

SUPABASE_URL = "https://equrcpeifogdrxoldkpe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ"

print("=== Inventory Table Analysis ===")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

try:
    # 1. 在庫テーブルの全体状況
    print("1. Inventory table overview:")
    total_inventory = supabase.table("inventory").select("*", count="exact").execute()
    print(f"   Total inventory items: {total_inventory.count}")
    
    # 2. 既存の商品コードパターンを確認
    print("\n2. Existing product code patterns:")
    if total_inventory.data:
        sample_items = total_inventory.data[:10]
        for item in sample_items:
            print(f"   {item.get('common_code', 'N/A')} - {item.get('product_name', 'No name')[:40]}...")
    
    # 3. Rで始まる商品コードがあるか確認
    print("\n3. Checking for R-code products:")
    r_codes = supabase.table("inventory").select("*").like("common_code", "R%").execute()
    print(f"   Found {len(r_codes.data)} items with R-codes")
    
    if r_codes.data:
        for item in r_codes.data:
            print(f"   {item['common_code']} - {item.get('product_name', 'No name')}")
    
    # 4. 必要な楽天商品コードリスト
    rakuten_codes_needed = [
        'R01', 'R02', 'R03', 'R04', 'R05', 'R06', 'R07', 'R08', 'R09', 'R10',
        'R11', 'R12', 'R13', 'R14', 'R15', 'R16', 'R17', 'R18', 'R19', 'R20',
        'R21', 'R22', 'R23', 'R24', 'R25', 'R26', 'R27', 'R28', 'R30',
        'R32', 'R33', 'R34', 'R36', 'R37', 'R38', 'R40', 'R41', 'R42', 'R43', 'R44'
    ]
    
    print(f"\n4. Required Rakuten codes ({len(rakuten_codes_needed)}):")
    missing_codes = []
    existing_codes = []
    
    for code in rakuten_codes_needed:
        check = supabase.table("inventory").select("*").eq("common_code", code).execute()
        if check.data:
            existing_codes.append(code)
            print(f"   ✓ {code} - EXISTS")
        else:
            missing_codes.append(code)
            print(f"   ✗ {code} - MISSING")
    
    print(f"\n5. Summary:")
    print(f"   Existing codes: {len(existing_codes)}")
    print(f"   Missing codes: {len(missing_codes)}")
    
    if missing_codes:
        print(f"\n6. Missing codes that need to be added:")
        for i, code in enumerate(missing_codes, 1):
            print(f"   {i:2d}. {code}")
        
        print(f"\n=== NEXT ACTIONS ===")
        print(f"To complete the inventory integration:")
        print(f"1. Create inventory records for missing R-codes")
        print(f"2. Map R-codes to actual product names and details")
        print(f"3. Set initial stock levels")
        print(f"4. Test the inventory reduction system")

except Exception as e:
    print(f"ERROR: {str(e)}")