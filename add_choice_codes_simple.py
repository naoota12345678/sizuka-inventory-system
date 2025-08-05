#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
P01/S01/S02を選択肢コード対応表に追加（シンプル版）
"""

import os
from supabase import create_client
from datetime import datetime, timezone

# 環境変数を設定
os.environ['SUPABASE_URL'] = 'https://equrcpeifogdrxoldkpe.supabase.co'
os.environ['SUPABASE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ'

SUPABASE_URL = "https://equrcpeifogdrxoldkpe.supabase.co" 
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ"

def add_missing_choice_codes():
    """P01、S01、S02を選択肢コード対応表に追加"""
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    print("P01/S01/S02 choice code addition")
    
    # 利用可能なCMコードを確認
    result = supabase.table('product_master').select('common_code').not_.is_('common_code', 'null').execute()
    existing_codes = {item['common_code'] for item in result.data if item['common_code'].startswith('CM')}
    
    # 新しいCMコード（200番台）
    new_codes = []
    for i in range(200, 300):
        candidate = f"CM{i:03d}"
        if candidate not in existing_codes:
            new_codes.append(candidate)
            if len(new_codes) >= 3:
                break
    
    print(f"Available CM codes: {new_codes}")
    
    # 追加するマッピング
    mappings = [
        {'choice_code': 'P01', 'common_code': new_codes[0], 'product_name': 'Premium Product P01'},
        {'choice_code': 'S01', 'common_code': new_codes[1], 'product_name': 'Special Product S01'},
        {'choice_code': 'S02', 'common_code': new_codes[2], 'product_name': 'Special Product S02'}
    ]
    
    success_count = 0
    
    for mapping in mappings:
        try:
            # 既存チェック
            existing = supabase.table('choice_code_mapping').select('id').filter('choice_info->>choice_code', 'eq', mapping['choice_code']).execute()
            
            if existing.data:
                print(f"Already exists: {mapping['choice_code']}")
                continue
            
            # 新レコード作成
            new_record = {
                'choice_info': {
                    'choice_code': mapping['choice_code'],
                    'choice_name': f"{mapping['choice_code']} Choice",
                    'choice_value': mapping['product_name'],
                    'category': 'manual_addition'
                },
                'common_code': mapping['common_code'],
                'product_name': mapping['product_name'],
                'rakuten_sku': f"CHOICE_{mapping['choice_code']}"  # 選択肢コード専用のダミーSKU
            }
            
            # 挿入実行
            result = supabase.table('choice_code_mapping').insert(new_record).execute()
            
            if result.data:
                print(f"Success: {mapping['choice_code']} -> {mapping['common_code']}")
                success_count += 1
            else:
                print(f"Failed: {mapping['choice_code']}")
                
        except Exception as e:
            print(f"Error: {mapping['choice_code']} - {str(e)}")
    
    print(f"Total added: {success_count} choice codes")
    
    # 検証
    print("\nVerification:")
    for mapping in mappings:
        result = supabase.table('choice_code_mapping').select('*').filter('choice_info->>choice_code', 'eq', mapping['choice_code']).execute()
        if result.data:
            item = result.data[0]
            print(f"OK: {mapping['choice_code']} -> {item.get('common_code')} ({item.get('product_name')})")
        else:
            print(f"NG: {mapping['choice_code']} not found")

if __name__ == "__main__":
    add_missing_choice_codes()