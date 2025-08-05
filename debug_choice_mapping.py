#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from supabase import create_client

SUPABASE_URL = "https://equrcpeifogdrxoldkpe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ"

def debug_table():
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    try:
        # choice_code_mappingテーブルのデータを取得
        response = supabase.table("choice_code_mapping").select("*").limit(5).execute()
        
        print("choice_code_mapping テーブル構造:")
        if response.data:
            # 最初のレコードのキーを表示（列名）
            first_record = response.data[0]
            print("Columns:", list(first_record.keys()))
            
            print("\nSample data:")
            for i, record in enumerate(response.data):
                print(f"Record {i+1}: {record}")
        else:
            print("No data found")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    debug_table()