#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Supabaseのorder_itemsテーブル構造とデータを直接確認するスクリプト
"""
import os
import sys
from supabase import create_client, Client

def check_order_items_structure():
    """order_itemsテーブルの構造を確認"""
    try:
        # 環境変数の確認
        supabase_url = os.getenv("SUPABASE_URL") or "https://mgswnwrkufayotlqqjxf.supabase.co"
        supabase_key = os.getenv("SUPABASE_KEY") or "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1nc3dud3JrdWZheW90bHFxanhmIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzQ4NzM4ODIsImV4cCI6MjA1MDQ0OTg4Mn0.QfH9CpW5L--DqLLXyP7sIBCOZLSUEOv9HvUgHGGNj5o"
        
        if not supabase_url or not supabase_key:
            print("ERROR: SUPABASE_URLまたはSUPABASE_KEYが設定されていません")
            return
        
        print(f"Supabase URL: {supabase_url[:30]}...")
        
        # Supabaseクライアント作成
        supabase: Client = create_client(supabase_url, supabase_key)
        
        # 1. テーブル存在確認
        print("\norder_itemsテーブルの基本情報確認...")
        try:
            sample_response = supabase.table('order_items').select('*').limit(1).execute()
            print(f"OK: order_itemsテーブルは存在します")
            
            if sample_response.data:
                columns = list(sample_response.data[0].keys())
                print(f"カラム数: {len(columns)}")
                print(f"カラム一覧: {', '.join(columns[:10])}{'...' if len(columns) > 10 else ''}")
            else:
                print("WARNING: テーブルは存在しますが、データがありません")
                
        except Exception as e:
            print(f"ERROR: order_itemsテーブルにアクセスできません: {str(e)}")
            return
        
        # 2. 楽天関連カラムの確認
        expected_rakuten_columns = [
            'choice_code', 'parent_item_id', 'item_type', 'rakuten_variant_id',
            'rakuten_item_number', 'shop_item_code', 'jan_code', 'category_path',
            'brand_name', 'weight_info', 'size_info', 'extended_rakuten_data',
            'rakuten_sku', 'sku_type'
        ]
        
        print(f"\n楽天関連カラムの存在確認...")
        existing_rakuten_columns = []
        missing_rakuten_columns = []
        
        if sample_response.data:
            all_columns = list(sample_response.data[0].keys())
            for col in expected_rakuten_columns:
                if col in all_columns:
                    existing_rakuten_columns.append(col)
                else:
                    missing_rakuten_columns.append(col)
        
        print(f"存在する楽天カラム ({len(existing_rakuten_columns)}個):")
        for col in existing_rakuten_columns:
            print(f"   - {col}")
        
        print(f"欠落している楽天カラム ({len(missing_rakuten_columns)}個):")
        for col in missing_rakuten_columns:
            print(f"   - {col}")
        
        # 3. データ確認
        print(f"\norder_itemsテーブルのデータ確認...")
        count_response = supabase.table('order_items').select('*', count='exact').limit(0).execute()
        total_count = count_response.count if hasattr(count_response, 'count') else 0
        print(f"総レコード数: {total_count}")
        
        # 4. 楽天データの存在確認
        if sample_response.data and len(sample_response.data) > 0:
            print(f"\n楽天関連データの存在確認...")
            sample_data = supabase.table('order_items').select('*').limit(5).execute()
            
            rakuten_data_found = False
            for item in sample_data.data:
                for col in existing_rakuten_columns:
                    if item.get(col) is not None and item.get(col) != '':
                        print(f"OK: 楽天データ発見: {col} = {item.get(col)}")
                        rakuten_data_found = True
                        break
                if rakuten_data_found:
                    break
                    
            if not rakuten_data_found:
                print("WARNING: 楽天関連データは見つかりませんでした")
        
        # 5. 02_rakuten_enhancement.sqlの適用状況判定
        print(f"\n02_rakuten_enhancement.sql適用状況:")
        if len(missing_rakuten_columns) == 0:
            print("OK: 02_rakuten_enhancement.sqlは適用済みです")
        elif len(existing_rakuten_columns) > 0:
            print("PARTIAL: 02_rakuten_enhancement.sqlは部分的に適用されています")
        else:
            print("NOT_APPLIED: 02_rakuten_enhancement.sqlは未適用です")
            
        return {
            "enhancement_applied": len(missing_rakuten_columns) == 0,
            "existing_columns": existing_rakuten_columns,
            "missing_columns": missing_rakuten_columns,
            "total_records": total_count
        }
        
    except Exception as e:
        print(f"ERROR: エラーが発生しました: {str(e)}")
        return None

if __name__ == "__main__":
    result = check_order_items_structure()
    if result:
        print(f"\n結果サマリー:")
        print(f"   - 拡張適用状況: {'OK' if result['enhancement_applied'] else 'NOT_APPLIED'}")
        print(f"   - 存在カラム数: {len(result['existing_columns'])}")
        print(f"   - 欠落カラム数: {len(result['missing_columns'])}")
        print(f"   - 総レコード数: {result['total_records']}")