#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from supabase import create_client

SUPABASE_URL = "https://equrcpeifogdrxoldkpe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ"

def check_master():
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    print("人気Rコードの登録確認:")
    
    r_codes = ['R01', 'R12', 'R11', 'R08', 'R03']
    
    for r_code in r_codes:
        response = supabase.table("product_master").select("rakuten_sku, common_code, product_name").eq("rakuten_sku", r_code).execute()
        
        if response.data:
            item = response.data[0]
            print(f"OK {r_code}: {item['common_code']} - {item['product_name']}")
        else:
            print(f"NG {r_code}: 未登録")
    
    print("\nrakuten_skuサンプル:")
    response = supabase.table("product_master").select("rakuten_sku, common_code").limit(10).execute()
    
    if response.data:
        for item in response.data:
            print(f"  {item['rakuten_sku']}: {item['common_code']}")

if __name__ == "__main__":
    check_master()