#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
データベーススキーマの完全確認
全テーブルのカラム名、データ型、サンプルデータを確認
"""

from supabase import create_client

SUPABASE_URL = "https://equrcpeifogdrxoldkpe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ"

def check_database_schema():
    """全テーブルのスキーマを確認"""
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    print("=== データベーススキーマ完全確認 ===\n")
    
    # 確認するテーブル
    tables = ["orders", "order_items", "platform_daily_sales", "inventory", "product_master"]
    
    schema_info = {}
    
    for table_name in tables:
        print(f"【{table_name}テーブル】")
        print("-" * 50)
        
        try:
            # 1件のサンプルデータを取得
            sample = supabase.table(table_name).select("*").limit(1).execute()
            
            if sample.data:
                sample_data = sample.data[0]
                schema_info[table_name] = {}
                
                print("カラム名とサンプルデータ:")
                for column_name, value in sample_data.items():
                    value_type = type(value).__name__
                    value_str = str(value)[:50] + "..." if len(str(value)) > 50 else str(value)
                    
                    schema_info[table_name][column_name] = {
                        "type": value_type,
                        "sample": value
                    }
                    
                    print(f"  {column_name:20} | {value_type:10} | {value_str}")
                
                # レコード数確認
                count_result = supabase.table(table_name).select("id", count="exact").execute()
                record_count = count_result.count if hasattr(count_result, 'count') else len(sample.data)
                print(f"\n総レコード数: {record_count}件")
                
            else:
                print("データなし")
                schema_info[table_name] = {}
                
        except Exception as e:
            print(f"エラー: {str(e)}")
            schema_info[table_name] = {"error": str(e)}
        
        print("\n")
    
    # 売上集計に必要なカラムの確認
    print("【売上集計用カラムの定義】")
    print("=" * 50)
    
    if "orders" in schema_info and schema_info["orders"]:
        print("ordersテーブル:")
        orders_schema = schema_info["orders"]
        
        # 重要なカラム
        important_columns = {
            "id": "注文ID",
            "order_date": "実際の注文日",
            "created_at": "DB登録日",
            "total_amount": "注文総額",
            "order_number": "注文番号",
            "status": "注文ステータス"
        }
        
        for col, desc in important_columns.items():
            if col in orders_schema:
                col_info = orders_schema[col]
                print(f"  ✅ {col:15} | {col_info['type']:10} | {desc}")
            else:
                print(f"  ❌ {col:15} | 存在しない | {desc}")
    
    print("\n集計用の推奨設定:")
    print("- 日付カラム: order_date (実際の注文日)")
    print("- 金額カラム: total_amount")
    print("- DB登録日: created_at (集計には使用しない)")
    
    return schema_info

def create_aggregation_config():
    """集計用設定ファイルを作成"""
    config = {
        "orders": {
            "date_column": "order_date",  # 実際の注文日
            "amount_column": "total_amount",
            "id_column": "id",
            "status_column": "status"
        },
        "platform_daily_sales": {
            "date_column": "sales_date",
            "amount_column": "total_amount", 
            "count_column": "order_count",
            "platform_column": "platform"
        }
    }
    
    print("\n【推奨集計設定】")
    print("=" * 30)
    for table, cols in config.items():
        print(f"{table}:")
        for col_type, col_name in cols.items():
            print(f"  {col_type}: {col_name}")
        print()
    
    return config

if __name__ == "__main__":
    schema = check_database_schema()
    config = create_aggregation_config()