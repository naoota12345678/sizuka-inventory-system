#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
製造商品の商品番号マッピング確認
inventory登録前にproduct_masterでマッピングされているかチェック
"""

from supabase import create_client

SUPABASE_URL = "https://equrcpeifogdrxoldkpe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ"

def main():
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    print("=== 製造商品の商品番号マッピング確認 ===")
    print()
    
    # 1. inventoryテーブルの商品IDを取得
    try:
        inventory = supabase.table("inventory").select("common_code, product_name, current_stock").execute()
        print(f"【1】inventoryテーブルの商品: {len(inventory.data)}件")
        
        inventory_codes = set()
        for item in inventory.data:
            inventory_codes.add(item['common_code'])
        
        print("inventoryに登録済みの商品ID例:")
        for i, item in enumerate(inventory.data[:5]):
            print(f"  - {item['common_code']}: {item['product_name']} (在庫: {item['current_stock']})")
        print()
        
    except Exception as e:
        print(f"inventoryエラー: {str(e)}")
        return
    
    # 2. product_masterで10XXX形式の商品IDをチェック
    try:
        # 10XXX形式の商品IDでproduct_masterを検索
        product_master = supabase.table("product_master").select("*").execute()
        print(f"【2】product_masterテーブル: {len(product_master.data)}件")
        
        # 10XXX形式（製造商品ID）を探す
        manufacturing_products = []
        mapped_to_inventory = []
        unmapped_products = []
        
        for item in product_master.data:
            rakuten_sku = item.get('rakuten_sku', '')
            common_code = item.get('common_code', '')
            
            # 10XXX形式の商品IDをチェック
            if rakuten_sku and rakuten_sku.startswith('10') and len(rakuten_sku) >= 5:
                manufacturing_products.append(item)
                
                # inventoryにマッピング済みかチェック
                if common_code in inventory_codes:
                    mapped_to_inventory.append(item)
                else:
                    unmapped_products.append(item)
        
        print(f"製造商品ID（10XXX形式）: {len(manufacturing_products)}件")
        print(f"  - inventoryにマッピング済み: {len(mapped_to_inventory)}件")
        print(f"  - inventoryに未マッピング: {len(unmapped_products)}件")
        print()
        
        # マッピング済み商品の例
        if mapped_to_inventory:
            print("【マッピング済み】製造商品 → inventory:")
            for item in mapped_to_inventory[:5]:
                print(f"  楽天SKU {item['rakuten_sku']} → 共通コード {item['common_code']}")
                print(f"    商品名: {item['product_name']}")
            print()
        
        # 未マッピング商品の例
        if unmapped_products:
            print("【未マッピング】製造商品（inventoryに未登録）:")
            for item in unmapped_products[:5]:
                print(f"  楽天SKU {item['rakuten_sku']} → 共通コード {item['common_code']}")
                print(f"    商品名: {item['product_name']}")
            print()
    
    except Exception as e:
        print(f"product_masterエラー: {str(e)}")
        return
    
    # 3. 今回の製造データの商品IDをチェック
    print("【3】今回製造された商品IDの状況:")
    manufactured_ids = ['10003', '10023', '10107', '10076', '10016', '10105', '10010', '10066']
    
    for product_id in manufactured_ids:
        # product_masterでマッピング確認
        mapping = supabase.table("product_master").select("*").eq("rakuten_sku", product_id).execute()
        
        if mapping.data:
            common_code = mapping.data[0]['common_code']
            product_name = mapping.data[0]['product_name']
            
            # inventoryに存在するかチェック
            in_inventory = common_code in inventory_codes
            status = "✓ inventory登録済み" if in_inventory else "✗ inventory未登録"
            
            print(f"  {product_id} → {common_code} ({product_name}) {status}")
        else:
            print(f"  {product_id} → ✗ product_masterに未登録")
    
    print()
    print("=== 結論 ===")
    print("製造商品は以下の流れで管理されています：")
    print("1. 製造商品ID（10XXX）がproduct_masterに登録")
    print("2. product_masterで楽天SKU → 共通コードにマッピング")
    print("3. 共通コードでinventoryテーブルに在庫登録")
    print()
    
    if len(mapped_to_inventory) > 0:
        print(f"現在 {len(mapped_to_inventory)}個の製造商品が正しくマッピングされています。")
    
    if len(unmapped_products) > 0:
        print(f"⚠️ {len(unmapped_products)}個の製造商品がinventoryに未登録です。")
        print("   これらは手動でinventoryに追加する必要があります。")

if __name__ == "__main__":
    main()