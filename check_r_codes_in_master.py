#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
product_master内のRコード確認
"""

from supabase import create_client

SUPABASE_URL = "https://equrcpeifogdrxoldkpe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ"

def check_r_codes():
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    print("=== choice_code内のRコード確認 ===")
    
    # 人気の高いRコードリスト
    popular_r_codes = ['R01', 'R12', 'R11', 'R08', 'R03', 'R02', 'R07', 'R16', 'R10', 'R14']
    
    print("人気Rコードのproduct_master登録状況:")
    print("-" * 50)
    
    for r_code in popular_r_codes:
        # product_masterで検索
        response = supabase.table("product_master").select("rakuten_sku, common_code, product_name").eq("rakuten_sku", r_code).execute()
        
        if response.data:
            item = response.data[0]
            print(f"✓ {r_code}: {item['common_code']} - {item['product_name'][:40]}")
        else:
            print(f"✗ {r_code}: 未登録")
    
    print("\n" + "=" * 60)
    
    # product_master内の全Rコードを確認
    print("\nproduct_master内のRコード一覧:")
    print("-" * 30)
    
    # Rで始まるrakuten_skuを検索
    response = supabase.table("product_master").select("rakuten_sku, common_code, product_name").like("rakuten_sku", "R%").execute()
    
    if response.data:
        print(f"登録済みRコード: {len(response.data)}件")
        for item in response.data[:20]:  # 最初の20件表示
            print(f"  {item['rakuten_sku']}: {item['common_code']} - {item['product_name'][:40]}")
        if len(response.data) > 20:
            print(f"  ... 他{len(response.data) - 20}件")
    else:
        print("Rコードが1件も見つかりません")
    
    print("\n" + "=" * 60)
    
    # 楽天SKUのサンプル確認
    print("\nrakuten_skuサンプル（最新20件）:")
    print("-" * 30)
    
    response = supabase.table("product_master").select("rakuten_sku, common_code, product_name").limit(20).execute()
    
    if response.data:
        for item in response.data:
            print(f"  {item['rakuten_sku']}: {item['common_code']} - {item['product_name'][:40]}")
    
if __name__ == "__main__":
    check_r_codes()