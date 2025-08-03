# -*- coding: utf-8 -*-
"""
Supabaseに直接SQLスクリプトを適用するツール
"""
import os
from supabase import create_client, Client

def apply_sql_file(filename):
    """SQLファイルをSupabaseに適用"""
    try:
        # Supabase接続
        supabase_url = "https://mgswnwrkufayotlqqjxf.supabase.co"
        supabase_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1nc3dud3JrdWZheW90bHFxanhmIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzQ4NzM4ODIsImV4cCI6MjA1MDQ0OTg4Mn0.QfH9CpW5L--DqLLXyP7sIBCOZLSUEOv9HvUgHGGNj5o"
        
        supabase: Client = create_client(supabase_url, supabase_key)
        
        # SQLファイルを読み込み
        with open(filename, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        print(f"ファイル読み込み: {filename}")
        print(f"SQLサイズ: {len(sql_content)} 文字")
        
        # SQLを行ごとに分割して実行
        sql_statements = []
        current_statement = ""
        
        for line in sql_content.split('\n'):
            line = line.strip()
            if line.startswith('--') or line == '':
                continue
            
            current_statement += line + ' '
            
            if line.endswith(';'):
                if current_statement.strip():
                    sql_statements.append(current_statement.strip())
                current_statement = ""
        
        print(f"実行予定のSQL文: {len(sql_statements)}個")
        
        # 各SQL文を順次実行
        success_count = 0
        for i, sql in enumerate(sql_statements):
            try:
                if sql.upper().startswith('SELECT'):
                    # SELECT文の場合
                    response = supabase.rpc('execute_sql', {'sql': sql}).execute()
                elif sql.upper().startswith(('CREATE', 'ALTER', 'INSERT', 'DROP')):
                    # DDL/DML文の場合 - 直接実行は制限されるので、RPC経由で実行
                    response = supabase.rpc('execute_sql', {'sql': sql}).execute()
                else:
                    print(f"スキップ: {sql[:50]}...")
                    continue
                
                success_count += 1
                print(f"OK ({i+1}/{len(sql_statements)}): {sql[:50]}...")
                
            except Exception as e:
                print(f"エラー ({i+1}/{len(sql_statements)}): {str(e)}")
                print(f"SQL: {sql[:100]}...")
        
        print(f"\n結果: {success_count}/{len(sql_statements)} 個のSQL文が成功")
        return success_count > 0
        
    except Exception as e:
        print(f"ファイル処理エラー: {str(e)}")
        return False

def check_table_exists(table_name):
    """テーブルの存在確認"""
    try:
        supabase_url = "https://mgswnwrkufayotlqqjxf.supabase.co"
        supabase_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1nc3dud3JrdWZheW90bHFxanhmIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzQ4NzM4ODIsImV4cCI6MjA1MDQ0OTg4Mn0.QfH9CpW5L--DqLLXyP7sIBCOZLSUEOv9HvUgHGGNj5o"
        
        supabase: Client = create_client(supabase_url, supabase_key)
        
        response = supabase.table(table_name).select('*').limit(1).execute()
        columns = list(response.data[0].keys()) if response.data else []
        
        print(f"テーブル {table_name}:")
        print(f"  存在: YES")
        print(f"  カラム数: {len(columns)}")
        print(f"  カラム: {', '.join(columns[:5])}{'...' if len(columns) > 5 else ''}")
        
        return True, columns
        
    except Exception as e:
        print(f"テーブル {table_name}: 存在しません ({str(e)})")
        return False, []

if __name__ == "__main__":
    print("=== Supabase SQLスクリプト適用ツール ===\n")
    
    # 1. 現在のテーブル状況確認
    print("1. 現在のテーブル状況:")
    exists_order_items, order_items_columns = check_table_exists('order_items')
    exists_product_mapping, _ = check_table_exists('product_mapping_master')
    
    # 2. 楽天関連カラムの確認
    if exists_order_items:
        expected_columns = ['choice_code', 'rakuten_sku', 'rakuten_item_number']
        existing_rakuten = [col for col in expected_columns if col in order_items_columns]
        missing_rakuten = [col for col in expected_columns if col not in order_items_columns]
        
        print(f"\n2. order_itemsの楽天関連カラム:")
        print(f"  存在: {existing_rakuten}")
        print(f"  欠落: {missing_rakuten}")
        
        enhancement_needed = len(missing_rakuten) > 0
    else:
        enhancement_needed = True
    
    # 3. SQLスクリプトの適用
    print(f"\n3. SQLスクリプト適用:")
    
    if enhancement_needed:
        print("02_rakuten_enhancement.sql を適用中...")
        apply_sql_file("supabase/02_rakuten_enhancement.sql")
    else:
        print("02_rakuten_enhancement.sql は適用済みです")
    
    if not exists_product_mapping:
        print("03_product_mapping_master.sql を適用中...")
        apply_sql_file("supabase/03_product_mapping_master.sql")
    else:
        print("03_product_mapping_master.sql は適用済みです")
    
    print("\n=== 完了 ===")