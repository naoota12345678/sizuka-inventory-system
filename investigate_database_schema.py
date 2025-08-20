#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Supabaseデータベース構造完全調査スクリプト
全テーブル・全フィールド・全関係性を調査
"""

import os
import json
from supabase import create_client
from datetime import datetime

SUPABASE_URL = 'https://equrcpeifogdrxoldkpe.supabase.co'
SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ'

def investigate_all_tables():
    """全テーブルを調査"""
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    print("=" * 80)
    print("SUPABASE DATABASE COMPLETE SCHEMA INVESTIGATION")
    print("=" * 80)
    print(f"Investigation Time: {datetime.now()}")
    print(f"Database URL: {SUPABASE_URL}")
    print()
    
    # 想定される全テーブル名
    potential_tables = [
        # 基本テーブル
        'orders', 'order_items', 'platform', 
        'product_master', 'choice_code_mapping', 'inventory',
        
        # Amazon関連テーブル
        'amazon_orders', 'amazon_order_items', 'amazon_product_master',
        'amazon_fba_inventory', 'amazon_inventory',
        
        # その他のプラットフォーム
        'rakuten_orders', 'rakuten_order_items',
        'colorme_orders', 'airegi_orders',
        
        # システムテーブル
        'sync_log', 'package_components', 'unprocessed_sales',
        'platform_sales', 'daily_sales_summary',
        
        # ユーザー管理
        'users', 'user_profiles', 'sessions',
        
        # ログ・監査
        'audit_log', 'error_log', 'api_log'
    ]
    
    schema_data = {}
    existing_tables = []
    
    print("TABLE EXISTENCE CHECK:")
    print("-" * 40)
    
    for table_name in potential_tables:
        try:
            # テーブルの存在確認（1件取得を試行）
            result = supabase.table(table_name).select('*').limit(1).execute()
            
            existing_tables.append(table_name)
            record_count = get_table_count(supabase, table_name)
            
            print(f"OK {table_name:<25} | Records: {record_count:>8}")
            
            # フィールド構造を取得
            if result.data:
                schema_data[table_name] = {
                    'exists': True,
                    'record_count': record_count,
                    'fields': list(result.data[0].keys()),
                    'sample_data': result.data[0]
                }
            else:
                # データが空でもテーブルは存在
                schema_data[table_name] = {
                    'exists': True,
                    'record_count': 0,
                    'fields': [],
                    'sample_data': None
                }
            
        except Exception as e:
            error_msg = str(e)
            if 'does not exist' in error_msg or 'relation' in error_msg:
                print(f"❌ {table_name:<25} | NOT EXISTS")
                schema_data[table_name] = {
                    'exists': False,
                    'error': error_msg[:100]
                }
            else:
                print(f"⚠️  {table_name:<25} | ERROR: {error_msg[:50]}")
                schema_data[table_name] = {
                    'exists': 'unknown',
                    'error': error_msg[:100]
                }
    
    print(f"\n📊 SUMMARY: {len(existing_tables)}/{len(potential_tables)} tables exist")
    print()
    
    # 詳細なテーブル構造調査
    print("=" * 80)
    print("DETAILED TABLE STRUCTURE ANALYSIS")
    print("=" * 80)
    
    for table_name in existing_tables:
        analyze_table_structure(supabase, table_name, schema_data[table_name])
        print()
    
    # スキーマサマリー
    print("=" * 80)
    print("DATABASE SCHEMA SUMMARY")
    print("=" * 80)
    
    # プラットフォーム関連テーブル
    platform_tables = [t for t in existing_tables if any(p in t for p in ['platform', 'amazon', 'rakuten', 'colorme', 'airegi'])]
    order_tables = [t for t in existing_tables if 'order' in t]
    inventory_tables = [t for t in existing_tables if 'inventory' in t or 'product' in t]
    system_tables = [t for t in existing_tables if t not in platform_tables + order_tables + inventory_tables]
    
    print(f"🏪 PLATFORM TABLES ({len(platform_tables)}):")
    for table in platform_tables:
        print(f"   - {table} ({schema_data[table]['record_count']} records)")
    
    print(f"\n📦 ORDER TABLES ({len(order_tables)}):")
    for table in order_tables:
        print(f"   - {table} ({schema_data[table]['record_count']} records)")
    
    print(f"\n📋 INVENTORY/PRODUCT TABLES ({len(inventory_tables)}):")
    for table in inventory_tables:
        print(f"   - {table} ({schema_data[table]['record_count']} records)")
    
    print(f"\n🔧 SYSTEM TABLES ({len(system_tables)}):")
    for table in system_tables:
        print(f"   - {table} ({schema_data[table]['record_count']} records)")
    
    # Amazon統合の現状分析
    print("\n" + "=" * 80)
    print("AMAZON INTEGRATION ANALYSIS")
    print("=" * 80)
    
    amazon_dedicated = [t for t in existing_tables if t.startswith('amazon_')]
    unified_approach = 'orders' in existing_tables and 'order_items' in existing_tables
    
    print(f"🔍 Amazon Dedicated Tables: {len(amazon_dedicated)}")
    if amazon_dedicated:
        for table in amazon_dedicated:
            print(f"   - {table}: {schema_data[table]['record_count']} records")
    else:
        print("   - No Amazon-specific tables found")
    
    print(f"\n🔍 Unified Table Approach: {'YES' if unified_approach else 'NO'}")
    if unified_approach:
        # platform_idでAmazonデータを確認
        amazon_orders = count_platform_records(supabase, 'orders', 2)  # Amazon = platform_id 2
        print(f"   - orders with platform_id=2 (Amazon): {amazon_orders}")
        
        amazon_items = count_amazon_items(supabase)
        print(f"   - order_items with Amazon indicators: {amazon_items}")
    
    # 推奨アプローチの提案
    print(f"\n💡 RECOMMENDED APPROACH:")
    if amazon_dedicated and any(schema_data[t]['record_count'] > 0 for t in amazon_dedicated):
        print("   ✅ USE AMAZON DEDICATED TABLES (they contain data)")
    elif unified_approach:
        print("   ✅ USE UNIFIED TABLES with platform_id=2 for Amazon")
        print("   📝 Store Amazon-specific data in platform_data JSONB field")
    else:
        print("   ⚠️ CREATE AMAZON INTEGRATION STRATEGY")
        print("   📝 Consider creating Amazon tables or extending unified tables")
    
    return schema_data

def get_table_count(supabase, table_name):
    """テーブルの行数を取得"""
    try:
        result = supabase.table(table_name).select('id', count='exact').limit(1).execute()
        return result.count if hasattr(result, 'count') else 0
    except:
        return 0

def analyze_table_structure(supabase, table_name, table_info):
    """個別テーブルの詳細分析"""
    print(f"🔍 TABLE: {table_name}")
    print(f"   Records: {table_info['record_count']:,}")
    print(f"   Fields ({len(table_info['fields'])}): {', '.join(table_info['fields'])}")
    
    if table_info['sample_data']:
        print("   Sample Data Types:")
        for field, value in list(table_info['sample_data'].items())[:10]:  # 最初の10フィールドのみ
            value_type = type(value).__name__
            if isinstance(value, str) and len(value) > 50:
                display_value = value[:47] + "..."
            else:
                display_value = value
            print(f"     {field:<20}: {value_type:<10} = {display_value}")
    
    # 特殊フィールドの確認
    special_fields = []
    if 'platform_id' in table_info['fields']:
        special_fields.append('platform_id (foreign key)')
    if 'platform_data' in table_info['fields']:
        special_fields.append('platform_data (JSONB)')
    if any('amazon' in f.lower() for f in table_info['fields']):
        amazon_fields = [f for f in table_info['fields'] if 'amazon' in f.lower()]
        special_fields.append(f"Amazon fields: {', '.join(amazon_fields)}")
    
    if special_fields:
        print(f"   Special Fields: {'; '.join(special_fields)}")

def count_platform_records(supabase, table_name, platform_id):
    """特定のプラットフォームIDのレコード数を取得"""
    try:
        result = supabase.table(table_name).select('id', count='exact').eq('platform_id', platform_id).execute()
        return result.count if hasattr(result, 'count') else 0
    except:
        return 0

def count_amazon_items(supabase):
    """order_itemsでAmazonと思われるアイテム数を取得"""
    try:
        # product_codeにAmazon ASINの特徴（B0で始まる）があるかチェック
        result = supabase.table('order_items').select('id', count='exact').ilike('product_code', 'B0%').execute()
        return result.count if hasattr(result, 'count') else 0
    except:
        return 0

if __name__ == "__main__":
    try:
        schema_data = investigate_all_tables()
        
        # 結果をファイルに保存
        with open('supabase_schema_analysis.json', 'w', encoding='utf-8') as f:
            json.dump(schema_data, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"\n💾 Schema analysis saved to: supabase_schema_analysis.json")
        
    except Exception as e:
        print(f"❌ Investigation failed: {str(e)}")
        import traceback
        traceback.print_exc()