#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
必要なテーブルを作成
"""

from supabase import create_client

SUPABASE_URL = "https://equrcpeifogdrxoldkpe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ"

print("=== Setting up required tables ===")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# choice_code_mappingテーブルの作成SQL
create_choice_mapping_sql = """
CREATE TABLE IF NOT EXISTS choice_code_mapping (
    id SERIAL PRIMARY KEY,
    choice_code VARCHAR(10) UNIQUE NOT NULL,
    common_code VARCHAR(10) NOT NULL,
    jan_code VARCHAR(13),
    rakuten_sku VARCHAR(50),
    product_name VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
"""

try:
    # SQLエディタでテーブル作成を実行
    print("Creating choice_code_mapping table...")
    print("SQL:")
    print(create_choice_mapping_sql)
    
    print("\nPlease execute this SQL in Supabase SQL Editor manually:")
    print("1. Go to Supabase Dashboard -> SQL Editor")
    print("2. Paste the SQL above")  
    print("3. Click 'Run'")
    
    # テーブルの存在確認
    try:
        result = supabase.table('choice_code_mapping').select('*').limit(1).execute()
        print("\n✓ choice_code_mapping table exists")
    except Exception as e:
        print(f"\n✗ choice_code_mapping table needs to be created: {str(e)}")
    
except Exception as e:
    print(f"ERROR: {str(e)}")

print("\n=== After creating the table ===")
print("Run create_sample_mappings.py to populate test data")