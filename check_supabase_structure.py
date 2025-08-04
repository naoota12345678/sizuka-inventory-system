#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Supabaseの製品情報構造確認
各テーブルの内容と関係性を調査
"""

from supabase import create_client
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SUPABASE_URL = "https://equrcpeifogdrxoldkpe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ"

def main():
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    print("=== Supabase製品情報構造確認 ===\n")
    
    # 1. inventoryテーブル（在庫管理）
    try:
        inventory = supabase.table("inventory").select("*").limit(5).execute()
        print("📦 inventoryテーブル（在庫管理）")
        print(f"   総件数: {len(inventory.data)}件")
        if inventory.data:
            print("   サンプルデータ:")
            for item in inventory.data[:3]:
                print(f"     - {item.get('common_code')}: {item.get('product_name')} (在庫: {item.get('current_stock')})")
        print()
    except Exception as e:
        print(f"   エラー: {str(e)}\n")
    
    # 2. product_masterテーブル（商品マスター）
    try:
        product_master = supabase.table("product_master").select("*").limit(5).execute()
        print("🏷️ product_masterテーブル（商品マスター）")
        print(f"   総件数: {len(product_master.data)}件")
        if product_master.data:
            print("   サンプルデータ:")
            for item in product_master.data[:3]:
                print(f"     - 楽天SKU: {item.get('rakuten_sku')} → 共通コード: {item.get('common_code')}")
                print(f"       商品名: {item.get('product_name')}")
        print()
    except Exception as e:
        print(f"   エラー: {str(e)}\n")
    
    # 3. choice_code_mappingテーブル（選択肢コードマッピング）
    try:
        choice_mapping = supabase.table("choice_code_mapping").select("*").limit(5).execute()
        print("🔀 choice_code_mappingテーブル（選択肢コードマッピング）")
        print(f"   総件数: {len(choice_mapping.data)}件")
        if choice_mapping.data:
            print("   サンプルデータ:")
            for item in choice_mapping.data[:3]:
                choice_info = item.get('choice_info', {})
                print(f"     - 選択肢コード: {choice_info.get('choice_code')} → 共通コード: {item.get('common_code')}")
                print(f"       販売タイプ: {choice_info.get('sale_type')}")
        print()
    except Exception as e:
        print(f"   エラー: {str(e)}\n")
    
    # 4. order_itemsテーブル（注文データ）
    try:
        order_items = supabase.table("order_items").select("*").limit(3).execute()
        print("📋 order_itemsテーブル（楽天注文データ）")
        print(f"   総件数: {len(order_items.data)}件")
        if order_items.data:
            print("   サンプルデータ:")
            for item in order_items.data[:2]:
                print(f"     - 楽天SKU: {item.get('rakuten_item_number')} / 商品コード: {item.get('product_code')}")
                print(f"       商品名: {item.get('product_name', '')[:30]}...")
                print(f"       選択肢: {item.get('choice_code', 'なし')}")
        print()
    except Exception as e:
        print(f"   エラー: {str(e)}\n")
    
    # 5. package_componentsテーブル（まとめ商品構成）
    try:
        package_components = supabase.table("package_components").select("*").limit(5).execute()
        print("📦 package_componentsテーブル（まとめ商品構成）")
        print(f"   総件数: {len(package_components.data)}件")
        if package_components.data:
            print("   サンプルデータ:")
            for item in package_components.data[:3]:
                print(f"     - パッケージ: {item.get('package_code')} → 構成品: {item.get('component_code')}")
                print(f"       数量: {item.get('quantity', 1)}")
        print()
    except Exception as e:
        print(f"   エラー: {str(e)}\n")
    
    # 6. データの関係性確認
    print("🔗 データ関係性の確認")
    try:
        # 楽天SKUマッピング状況
        total_product_master = supabase.table("product_master").select("id", count="exact").execute()
        with_rakuten_sku = supabase.table("product_master").select("id", count="exact").not_.is_("rakuten_sku", "null").execute()
        
        print(f"   楽天SKUマッピング: {with_rakuten_sku.count}/{total_product_master.count} 件")
        
        # 在庫データとマッピングの一致状況
        inventory_count = supabase.table("inventory").select("id", count="exact").execute()
        print(f"   在庫管理商品数: {inventory_count.count} 件")
        
        # 選択肢コードマッピング
        choice_count = supabase.table("choice_code_mapping").select("id", count="exact").execute()
        print(f"   選択肢コードマッピング: {choice_count.count} 件")
        
    except Exception as e:
        print(f"   エラー: {str(e)}")
    
    print("\n=== 構造確認完了 ===")
    print("製品情報は以下のテーブルに分散して管理されています：")
    print("• inventory: 在庫数量管理")
    print("• product_master: 楽天SKU⇔共通コードマッピング")  
    print("• choice_code_mapping: 選択肢コード⇔共通コードマッピング")
    print("• order_items: 楽天注文データ")
    print("• package_components: まとめ商品の構成管理")

if __name__ == "__main__":
    main()