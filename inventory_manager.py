#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
楽天注文から在庫を自動で減らす在庫管理システム
"""

from supabase import create_client
import re
from typing import List, Dict
from datetime import datetime, timezone

SUPABASE_URL = "https://equrcpeifogdrxoldkpe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ"

def extract_product_codes_from_choice(choice_code: str) -> List[str]:
    """選択肢コードから商品コード（R05, R13等）を抽出"""
    if not choice_code:
        return []
    
    pattern = r'R\d{2,}'
    matches = re.findall(pattern, choice_code)
    
    # 重複除去
    seen = set()
    result = []
    for match in matches:
        if match not in seen:
            seen.add(match)
            result.append(match)
    
    return result

def process_rakuten_orders_for_inventory(start_date: str = "2025-08-03"):
    """
    楽天注文データを処理して在庫を減らす
    
    Args:
        start_date: 処理開始日（YYYY-MM-DD形式）
    """
    print(f"=== Rakuten Inventory Management ===")
    print(f"Processing orders from: {start_date}")
    
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    try:
        # 指定日以降の楽天注文データを取得（choice_codeがある商品のみ）
        print("\n1. Fetching Rakuten orders with choice codes...")
        
        orders = supabase.table("order_items").select("*").gte("created_at", start_date).like("product_code", "10000%").execute()
        
        if not orders.data:
            print("   No Rakuten orders found.")
            return
        
        print(f"   Found {len(orders.data)} Rakuten order items")
        
        # 在庫更新が必要なアイテムを分析
        inventory_updates = {}  # {product_code: total_quantity}
        processed_items = []
        
        for item in orders.data:
            choice_code = item.get('choice_code', '')
            quantity = item.get('quantity', 1)
            
            if choice_code:
                # 選択肢コードから商品コードを抽出
                product_codes = extract_product_codes_from_choice(choice_code)
                
                for code in product_codes:
                    if code not in inventory_updates:
                        inventory_updates[code] = 0
                    inventory_updates[code] += quantity
                
                processed_items.append({
                    'order_item_id': item['id'],
                    'product_code': item['product_code'],
                    'choice_code': choice_code,
                    'quantity': quantity,
                    'extracted_codes': product_codes
                })
        
        print(f"\n2. Analysis Results:")
        print(f"   Items with choice codes: {len(processed_items)}")
        print(f"   Unique products to update: {len(inventory_updates)}")
        
        # 詳細表示
        print(f"\n3. Inventory Updates Needed:")
        for code, total_qty in inventory_updates.items():
            print(f"   {code}: -{total_qty} units")
        
        # 実際の在庫データと照合
        print(f"\n4. Checking current inventory...")
        inventory_check = {}
        
        for code in inventory_updates.keys():
            try:
                # inventoryテーブルでcommon_codeと照合
                inventory_result = supabase.table("inventory").select("*").eq("common_code", code).execute()
                
                if inventory_result.data:
                    inv_item = inventory_result.data[0]
                    current_stock = inv_item.get('current_stock', 0)
                    required_qty = inventory_updates[code]
                    
                    inventory_check[code] = {
                        'current_stock': current_stock,
                        'required_qty': required_qty,
                        'new_stock': current_stock - required_qty,
                        'inventory_id': inv_item['id'],
                        'product_name': inv_item.get('product_name', 'Unknown')
                    }
                    
                    print(f"   {code}: {current_stock} → {current_stock - required_qty} ({inv_item.get('product_name', '')[:30]}...)")
                else:
                    print(f"   {code}: NOT FOUND in inventory")
                    inventory_check[code] = None
                    
            except Exception as e:
                print(f"   {code}: ERROR - {str(e)}")
                inventory_check[code] = None
        
        print(f"\n5. Processed Order Items:")
        for item in processed_items[:5]:  # 最初の5件のみ表示
            print(f"   Order Item ID: {item['order_item_id']}")
            print(f"   Product: {item['product_code']} (qty: {item['quantity']})")
            print(f"   Extracted: {item['extracted_codes']}")
            print(f"   Choice: {item['choice_code'][:50]}...")
            print()
        
        if len(processed_items) > 5:
            print(f"   ... and {len(processed_items) - 5} more items")
        
        return {
            'inventory_updates': inventory_updates,
            'inventory_check': inventory_check,
            'processed_items': processed_items
        }
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        return None

def apply_inventory_updates(inventory_check: Dict):
    """
    実際に在庫を更新する（テスト版）
    """
    print(f"\n=== APPLYING INVENTORY UPDATES (TEST MODE) ===")
    
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    for code, check_data in inventory_check.items():
        if check_data is None:
            print(f"   SKIP {code}: Not found in inventory")
            continue
        
        if check_data['new_stock'] < 0:
            print(f"   WARNING {code}: Would go negative ({check_data['new_stock']})")
            continue
        
        print(f"   UPDATE {code}: {check_data['current_stock']} → {check_data['new_stock']}")
        
        # 実際の更新（TEST MODEでは実行しない）
        # try:
        #     result = supabase.table("inventory").update({
        #         "current_stock": check_data['new_stock'],
        #         "last_updated": datetime.now(timezone.utc).isoformat()
        #     }).eq("id", check_data['inventory_id']).execute()
        #     
        #     if result.data:
        #         print(f"   SUCCESS: Updated {code}")
        #     else:
        #         print(f"   FAILED: Could not update {code}")
        # except Exception as e:
        #     print(f"   ERROR: {str(e)}")

if __name__ == "__main__":
    # 楽天注文データの処理
    result = process_rakuten_orders_for_inventory("2025-08-03")
    
    if result:
        # 在庫更新のテスト実行
        apply_inventory_updates(result['inventory_check'])
        
        print(f"\n=== SUMMARY ===")
        print(f"Total products to update: {len(result['inventory_updates'])}")
        print(f"Total order items processed: {len(result['processed_items'])}")
        print(f"Ready for inventory management integration!")