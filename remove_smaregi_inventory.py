#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Smaregi形式のinventoryレコードを削除
重複を解決して正しい共通コードのみ残す
"""

import os
from supabase import create_client

# 環境変数を設定
os.environ['SUPABASE_URL'] = 'https://equrcpeifogdrxoldkpe.supabase.co'
os.environ['SUPABASE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ'

SUPABASE_URL = "https://equrcpeifogdrxoldkpe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ"

def main():
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    print("Smaregi形式inventoryレコード削除ツール")
    print("=" * 50)
    
    # スマレジ形式のレコードを取得
    result = supabase.table("inventory").select("id, common_code, current_stock").execute()
    
    smaregi_records = []
    for item in result.data:
        if item['common_code'].startswith('10') and len(item['common_code']) >= 5:
            smaregi_records.append(item)
    
    print(f"\n削除対象のSmaregi形式レコード: {len(smaregi_records)}件")
    for record in smaregi_records:
        print(f"  ID: {record['id']}, common_code: {record['common_code']}, stock: {record['current_stock']}")
    
    if not smaregi_records:
        print("削除対象がありません")
        return
    
    response = input(f"\n{len(smaregi_records)}件のSmaregi形式レコードを削除しますか？ (y/n): ")
    if response.lower() != 'y':
        print("キャンセルしました")
        return
    
    # 削除実行
    deleted_count = 0
    for record in smaregi_records:
        try:
            delete_result = supabase.table("inventory").delete().eq("id", record['id']).execute()
            print(f"削除 ID {record['id']}: {record['common_code']}")
            deleted_count += 1
        except Exception as e:
            print(f"削除失敗 ID {record['id']}: {str(e)}")
    
    print(f"\n削除完了: {deleted_count}件")
    print("在庫ダッシュボードで正しい共通コードのみが表示されるはずです")

if __name__ == "__main__":
    main()