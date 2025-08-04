#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Google Sheets同期機能のテスト
"""

import os
from supabase import create_client

# Supabase接続
SUPABASE_URL = "https://equrcpeifogdrxoldkpe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ"

print("=== Google Sheets Sync Status Check ===")

try:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # choice_code_mappingテーブルの現在の状況
    result = supabase.table('choice_code_mapping').select('*', count='exact').execute()
    print(f"choice_code_mapping table: {result.count} records")
    
    if result.data:
        print("Existing mappings:")
        for item in result.data:
            print(f"   {item.get('choice_code')} -> {item.get('common_code')}")
    else:
        print("No choice code mappings found - need to import from spreadsheet")
        
except Exception as e:
    print(f"ERROR: {str(e)}")

print("\n=== NEXT ACTION ===")
print("スプレッドシートから選択肢コード対応表をインポートする必要があります。")
print("Google認証情報の設定またはCSVエクスポートが必要です。")