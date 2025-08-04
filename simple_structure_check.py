#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Supabaseの製品情報構造確認（シンプル版）
"""

from supabase import create_client

SUPABASE_URL = "https://equrcpeifogdrxoldkpe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ"

def main():
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    print("=== Supabase製品情報構造確認 ===")
    print()
    
    # 1. inventoryテーブル
    try:
        inventory = supabase.table("inventory").select("*").limit(5).execute()
        print("【1】inventoryテーブル（在庫管理）")
        print(f"総件数: {len(inventory.data)}件")
        if inventory.data:
            print("サンプルデータ:")
            for i, item in enumerate(inventory.data[:3]):
                print(f"  {i+1}. 共通コード: {item.get('common_code')}")
                print(f"     商品名: {item.get('product_name')}")
                print(f"     現在在庫: {item.get('current_stock')}個")
                print(f"     最低在庫: {item.get('minimum_stock')}個")
                print()
    except Exception as e:
        print(f"inventoryテーブルエラー: {str(e)}")
    
    # 2. product_masterテーブル
    try:
        product_master = supabase.table("product_master").select("*").limit(5).execute()
        print("【2】product_masterテーブル（楽天SKUマッピング）")
        print(f"総件数: {len(product_master.data)}件")
        if product_master.data:
            print("サンプルデータ:")
            for i, item in enumerate(product_master.data[:3]):
                print(f"  {i+1}. 楽天SKU: {item.get('rakuten_sku')}")
                print(f"     共通コード: {item.get('common_code')}")
                print(f"     商品名: {item.get('product_name')}")
                print(f"     商品タイプ: {item.get('product_type')}")
                print()
    except Exception as e:
        print(f"product_masterテーブルエラー: {str(e)}")
    
    # 3. choice_code_mappingテーブル
    try:
        choice_mapping = supabase.table("choice_code_mapping").select("*").limit(5).execute()
        print("【3】choice_code_mappingテーブル（選択肢コードマッピング）")
        print(f"総件数: {len(choice_mapping.data)}件")
        if choice_mapping.data:
            print("サンプルデータ:")
            for i, item in enumerate(choice_mapping.data[:3]):
                choice_info = item.get('choice_info', {})
                print(f"  {i+1}. 選択肢コード: {choice_info.get('choice_code')}")
                print(f"     共通コード: {item.get('common_code')}")
                print(f"     販売タイプ: {choice_info.get('sale_type')}")
                print(f"     楽天SKU: {choice_info.get('rakuten_sku', 'なし')}")
                print()
    except Exception as e:
        print(f"choice_code_mappingテーブルエラー: {str(e)}")
    
    # 4. 統計情報
    try:
        print("【4】統計情報")
        
        # 在庫データ
        inventory_count = supabase.table("inventory").select("id", count="exact").execute()
        print(f"在庫管理商品数: {inventory_count.count}件")
        
        # 楽天SKUマッピング
        total_product_master = supabase.table("product_master").select("id", count="exact").execute()
        with_rakuten_sku = supabase.table("product_master").select("id", count="exact").not_.is_("rakuten_sku", "null").execute()
        print(f"楽天SKUマッピング: {with_rakuten_sku.count}/{total_product_master.count}件")
        
        # 選択肢コードマッピング
        choice_count = supabase.table("choice_code_mapping").select("id", count="exact").execute()
        print(f"選択肢コードマッピング: {choice_count.count}件")
        
        # 楽天注文データ
        order_count = supabase.table("order_items").select("id", count="exact").execute()
        print(f"楽天注文データ: {order_count.count}件")
        
    except Exception as e:
        print(f"統計情報エラー: {str(e)}")
    
    print()
    print("=== まとめ ===")
    print("製品情報は以下のテーブルに分散管理されています：")
    print()
    print("◆ inventory")
    print("  - 役割: 在庫数量の管理")
    print("  - キー: common_code（共通商品コード）")
    print("  - 内容: 現在在庫、最低在庫、発注点など")
    print()
    print("◆ product_master") 
    print("  - 役割: 楽天SKU ⇔ 共通コードのマッピング")
    print("  - 内容: 楽天の商品コードを内部管理コードに変換")
    print()
    print("◆ choice_code_mapping")
    print("  - 役割: 選択肢コード ⇔ 共通コードのマッピング")
    print("  - 内容: R05、N03などの選択肢を商品コードに変換")
    print()
    print("◆ order_items")
    print("  - 役割: 楽天注文データの保存")
    print("  - 内容: 注文情報、在庫減算の元データ")

if __name__ == "__main__":
    main()