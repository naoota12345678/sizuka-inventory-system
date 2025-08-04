#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
楽天注文→選択肢コード抽出→マッピング→在庫変動の統合テスト
"""

from supabase import create_client
import re
import json

SUPABASE_URL = "https://equrcpeifogdrxoldkpe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ"

def extract_choice_codes(choice_code_text):
    """選択肢コードからR05, N03等を抽出"""
    if not choice_code_text:
        return []
    
    pattern = r'[A-Z]\d{2}'
    matches = re.findall(pattern, choice_code_text)
    
    # 重複除去
    seen = set()
    result = []
    for match in matches:
        if match not in seen:
            seen.add(match)
            result.append(match)
    
    return result

def get_mapping_for_choice_codes(choice_codes, supabase):
    """選択肢コードのマッピング情報を取得"""
    mappings = []
    
    for code in choice_codes:
        try:
            # choice_info.choice_code でJSONB検索
            result = supabase.table("choice_code_mapping").select("*").contains("choice_info", {"choice_code": code}).execute()
            
            if result.data:
                mapping = result.data[0]
                mappings.append({
                    "choice_code": code,
                    "common_code": mapping["common_code"],
                    "product_name": mapping["product_name"],
                    "mapping_found": True
                })
            else:
                mappings.append({
                    "choice_code": code,
                    "common_code": None,
                    "product_name": None,
                    "mapping_found": False
                })
        except Exception as e:
            print(f"   Mapping error for {code}: {str(e)}")
            mappings.append({
                "choice_code": code,
                "common_code": None,
                "product_name": None,
                "mapping_found": False,
                "error": str(e)
            })
    
    return mappings

def test_full_integration():
    """完全統合テスト"""
    print("=== Full Integration Test ===")
    
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # 1. 楽天注文データから選択肢コードがある商品を取得
    print("\n1. Fetching Rakuten orders with choice codes...")
    
    orders = supabase.table("order_items").select("*").like("product_code", "10000%").limit(5).execute()
    
    if not orders.data:
        print("   No Rakuten orders found")
        return
    
    print(f"   Found {len(orders.data)} order items")
    
    # 2. 各注文アイテムの処理
    for i, item in enumerate(orders.data, 1):
        print(f"\n--- Order Item {i} ---")
        print(f"Product Code: {item['product_code']}")
        print(f"Product Name: {item['product_name'][:50]}...")
        print(f"Quantity: {item['quantity']}")
        
        choice_code = item.get('choice_code', '')
        if choice_code:
            print(f"Choice Code Text: {choice_code[:100]}...")
            
            # 選択肢コード抽出
            extracted_codes = extract_choice_codes(choice_code)
            print(f"Extracted Codes: {extracted_codes}")
            
            if extracted_codes:
                # マッピング取得
                mappings = get_mapping_for_choice_codes(extracted_codes, supabase)
                
                print(f"Mappings:")
                for mapping in mappings:
                    if mapping["mapping_found"]:
                        print(f"   ✓ {mapping['choice_code']} -> {mapping['common_code']} ({mapping['product_name']})")
                    else:
                        print(f"   ✗ {mapping['choice_code']} -> NOT MAPPED")
                
                # 在庫変動計算
                inventory_changes = []
                for mapping in mappings:
                    if mapping["mapping_found"]:
                        inventory_changes.append({
                            "common_code": mapping["common_code"],
                            "quantity_to_reduce": item['quantity'],
                            "reason": f"Rakuten order {item['id']}"
                        })
                
                if inventory_changes:
                    print(f"Inventory Changes Needed:")
                    for change in inventory_changes:
                        print(f"   - {change['common_code']}: -{change['quantity_to_reduce']} units")
                else:
                    print("   No inventory changes (no mappings found)")
            else:
                print("   No choice codes extracted")
        else:
            print("   No choice code in this item")
    
    # 3. マッピング状況の概要
    print(f"\n=== MAPPING SUMMARY ===")
    
    # 全マッピング数
    total_mappings = supabase.table("choice_code_mapping").select("*", count="exact").execute()
    print(f"Total mappings available: {total_mappings.count}")
    
    # サンプルマッピング表示
    if total_mappings.data:
        print(f"Sample mappings:")
        for mapping in total_mappings.data[:5]:
            choice_info = mapping.get("choice_info", {})
            choice_code = choice_info.get("choice_code", "Unknown")
            print(f"   {choice_code} -> {mapping['common_code']} ({mapping['product_name'][:30]}...)")
    
    print(f"\n=== NEXT STEPS ===")
    print(f"1. 在庫変動処理の実装")
    print(f"2. 未マッピング商品の例外処理")
    print(f"3. バッチ処理での自動実行")

if __name__ == "__main__":
    test_full_integration()