#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from supabase import create_client

SUPABASE_URL = "https://equrcpeifogdrxoldkpe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ"

def check_choice_mapping():
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    print("choice_code_mapping テーブル確認:")
    
    # 人気Rコードをchoice_code_mappingで検索
    r_codes = ['R01', 'R12', 'R11', 'R08', 'R03']
    
    for r_code in r_codes:
        response = supabase.table("choice_code_mapping").select("*").eq("choice_code", r_code).execute()
        
        if response.data:
            item = response.data[0]
            print(f"OK {r_code}: {item}")
        else:
            print(f"NG {r_code}: 未登録")
    
    print("\nchoice_code_mapping サンプル:")
    response = supabase.table("choice_code_mapping").select("*").limit(10).execute()
    
    if response.data:
        for item in response.data:
            print(f"  {item}")
    else:
        print("choice_code_mapping テーブルが空です")

if __name__ == "__main__":
    check_choice_mapping()