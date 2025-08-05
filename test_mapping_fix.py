#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
8桁→4桁変換を含む売上集計テスト
"""

from supabase import create_client
from datetime import datetime, timedelta

SUPABASE_URL = "https://equrcpeifogdrxoldkpe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ"


def test_mapping_conversion():
    """8桁→4桁変換をテスト"""
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    print("=== 8桁→4桁変換テスト ===")
    
    # 実際の注文データから8桁コードを取得
    items = supabase.table('order_items').select('product_code, quantity, price').like('product_code', '10000%').limit(10).execute()
    
    success_count = 0
    total_count = 0
    total_sales = 0
    
    for item in items.data:
        product_code = item.get('product_code', '')
        quantity = item.get('quantity', 0)
        price = item.get('price', 0)
        sales_amount = price * quantity
        
        if product_code.startswith('10000') and len(product_code) == 8:
            total_count += 1
            
            # 10000059 → 59 のような変換
            suffix = product_code[5:]  # 末尾3桁
            predicted_4digit = str(int(suffix))  # ゼロ埋めを除去
            
            # 4桁でproduct_masterを検索
            master_response = supabase.table("product_master").select("common_code, product_name").eq("rakuten_sku", predicted_4digit).execute()
            
            if master_response.data:
                common_code = master_response.data[0].get('common_code')
                product_name = master_response.data[0].get('product_name', '')
                success_count += 1
                total_sales += sales_amount
                print(f"OK: {product_code} → {predicted_4digit} → {common_code} ({product_name[:20]}...) = {sales_amount:,.0f}円")
            else:
                print(f"NG: {product_code} → {predicted_4digit} → マッピングなし")
    
    print(f"\\n変換成功率: {success_count}/{total_count} = {success_count/total_count*100:.1f}%")
    print(f"成功分の売上合計: {total_sales:,.0f}円")
    
    return success_count, total_count


def test_full_sales_calculation():
    """全売上データで変換テスト"""
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    print("\\n=== 全売上データ変換テスト ===")
    
    # 全注文データを取得
    query = supabase.table('order_items').select('*, orders!inner(created_at)').gte('orders.created_at', '2025-07-31')
    response = query.execute()
    items = response.data if response.data else []
    
    print(f"対象注文数: {len(items)}件")
    
    # マッピング統計
    mapped_8to4 = 0  # 8桁→4桁変換成功
    mapped_direct = 0  # 直接マッピング成功
    unmapped = 0  # マッピング失敗
    
    mapped_sales = 0
    unmapped_sales = 0
    
    for item in items:
        product_code = item.get('product_code', 'unknown')
        quantity = item.get('quantity', 0)
        price = item.get('price', 0)
        sales_amount = price * quantity
        
        if product_code == 'unknown':
            unmapped += 1
            unmapped_sales += sales_amount
            continue
        
        # マッピング試行
        mapped = False
        
        # 8桁コードの場合は4桁変換を試行
        if product_code.startswith('10000') and len(product_code) == 8:
            suffix = product_code[5:]
            predicted_4digit = str(int(suffix))
            
            master_response = supabase.table("product_master").select("common_code").eq("rakuten_sku", predicted_4digit).execute()
            if master_response.data:
                mapped_8to4 += 1
                mapped_sales += sales_amount
                mapped = True
        
        # 直接マッピングを試行
        if not mapped:
            master_response = supabase.table("product_master").select("common_code").eq("rakuten_sku", product_code).execute()
            if master_response.data:
                mapped_direct += 1
                mapped_sales += sales_amount
                mapped = True
        
        # マッピング失敗
        if not mapped:
            unmapped += 1
            unmapped_sales += sales_amount
    
    total_items = mapped_8to4 + mapped_direct + unmapped
    success_rate = (mapped_8to4 + mapped_direct) / total_items * 100 if total_items > 0 else 0
    
    print(f"\\n=== 結果 ===")
    print(f"8桁→4桁変換成功: {mapped_8to4}件")
    print(f"直接マッピング成功: {mapped_direct}件")
    print(f"マッピング失敗: {unmapped}件")
    print(f"総合成功率: {success_rate:.1f}%")
    print(f"\\nマッピング成功売上: {mapped_sales:,.0f}円")
    print(f"マッピング失敗売上: {unmapped_sales:,.0f}円")
    print(f"総売上: {mapped_sales + unmapped_sales:,.0f}円")
    
    mapping_sales_rate = mapped_sales / (mapped_sales + unmapped_sales) * 100 if (mapped_sales + unmapped_sales) > 0 else 0
    print(f"売上ベース成功率: {mapping_sales_rate:.1f}%")


if __name__ == "__main__":
    test_mapping_conversion()
    test_full_sales_calculation()