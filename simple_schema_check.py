#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Supabaseデータベース構造調査（簡潔版）
"""

from supabase import create_client
from datetime import datetime

SUPABASE_URL = 'https://equrcpeifogdrxoldkpe.supabase.co'
SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ'

def check_database_schema():
    """データベーススキーマをチェック"""
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    print("=" * 60)
    print("SUPABASE DATABASE SCHEMA INVESTIGATION")
    print("=" * 60)
    print(f"Time: {datetime.now()}")
    print()
    
    # 主要テーブル
    main_tables = [
        'orders', 'order_items', 'platform', 'product_master', 
        'choice_code_mapping', 'inventory'
    ]
    
    # Amazon関連テーブル
    amazon_tables = [
        'amazon_orders', 'amazon_order_items', 'amazon_product_master',
        'amazon_fba_inventory', 'amazon_inventory'
    ]
    
    # その他テーブル
    other_tables = [
        'sync_log', 'package_components', 'unprocessed_sales',
        'platform_sales', 'daily_sales_summary'
    ]
    
    all_tables = main_tables + amazon_tables + other_tables
    
    existing_tables = []
    table_data = {}
    
    print("TABLE EXISTENCE CHECK:")
    print("-" * 30)
    
    for table in all_tables:
        try:
            result = supabase.table(table).select('*').limit(1).execute()
            count_result = supabase.table(table).select('id', count='exact').limit(1).execute()
            count = count_result.count if hasattr(count_result, 'count') else 0
            
            existing_tables.append(table)
            table_data[table] = {
                'records': count,
                'fields': list(result.data[0].keys()) if result.data else [],
                'sample': result.data[0] if result.data else None
            }
            
            print(f"[OK] {table:<25} | {count:>6} records")
            
        except Exception as e:
            if 'does not exist' in str(e):
                print(f"[NO] {table:<25} | Not exists")
            else:
                print(f"[ER] {table:<25} | {str(e)[:30]}")
    
    print(f"\nFOUND: {len(existing_tables)} tables")
    print()
    
    # 詳細構造分析
    print("=" * 60)
    print("DETAILED TABLE ANALYSIS")
    print("=" * 60)
    
    for table in existing_tables:
        data = table_data[table]
        print(f"\nTABLE: {table}")
        print(f"  Records: {data['records']:,}")
        print(f"  Fields:  {', '.join(data['fields'])}")
        
        # platform_idの確認
        if 'platform_id' in data['fields'] and data['sample']:
            platform_id = data['sample']['platform_id']
            print(f"  Platform ID: {platform_id} ({type(platform_id).__name__})")
        
        # Amazon関連フィールドの確認
        amazon_fields = [f for f in data['fields'] if 'amazon' in f.lower()]
        if amazon_fields:
            print(f"  Amazon Fields: {', '.join(amazon_fields)}")
        
        # platform_dataの確認
        if 'platform_data' in data['fields'] and data['sample']:
            platform_data = data['sample']['platform_data']
            if platform_data:
                print(f"  Platform Data: {type(platform_data).__name__}")
                if isinstance(platform_data, dict):
                    print(f"    Keys: {', '.join(platform_data.keys())}")
    
    # プラットフォーム情報の確認
    if 'platform' in existing_tables:
        print("\n" + "=" * 60)
        print("PLATFORM CONFIGURATION")
        print("=" * 60)
        platforms = supabase.table('platform').select('*').execute()
        for platform in platforms.data:
            platform_id = platform.get('id')
            name = platform.get('name', 'Unknown')
            print(f"  ID {platform_id}: {name}")
    
    # Amazon統合の現状
    print("\n" + "=" * 60)
    print("AMAZON INTEGRATION STATUS")
    print("=" * 60)
    
    amazon_dedicated = [t for t in existing_tables if t.startswith('amazon_')]
    print(f"Amazon Dedicated Tables: {len(amazon_dedicated)}")
    for table in amazon_dedicated:
        print(f"  - {table}: {table_data[table]['records']} records")
    
    if 'orders' in existing_tables:
        # Amazon注文の確認（platform_id=2）
        try:
            amazon_orders = supabase.table('orders').select('id', count='exact').eq('platform_id', 2).execute()
            amazon_count = amazon_orders.count if hasattr(amazon_orders, 'count') else 0
            print(f"Amazon Orders (platform_id=2): {amazon_count}")
        except Exception as e:
            print(f"Amazon Orders Check Error: {str(e)}")
    
    # 推奨アプローチ
    print(f"\nRECOMMENDED AMAZON APPROACH:")
    if amazon_dedicated and any(table_data[t]['records'] > 0 for t in amazon_dedicated):
        print("  -> USE Amazon dedicated tables (contains data)")
    elif 'orders' in existing_tables and 'platform' in existing_tables:
        print("  -> USE unified tables with platform_id=2")
        print("  -> Store Amazon data in platform_data JSONB field")
    else:
        print("  -> CREATE Amazon integration strategy")
    
    return existing_tables, table_data

if __name__ == "__main__":
    try:
        existing, data = check_database_schema()
        print(f"\nDatabase investigation completed successfully.")
        print(f"Found {len(existing)} tables with detailed schema information.")
    except Exception as e:
        print(f"ERROR: {str(e)}")
        import traceback
        traceback.print_exc()