#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from supabase import create_client

SUPABASE_URL = "https://equrcpeifogdrxoldkpe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ"

def check_tables():
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    print("choice_code_mapping テーブル構造:")
    response = supabase.table("choice_code_mapping").select("*").limit(5).execute()
    
    if response.data:
        print("サンプルデータ:")
        for item in response.data:
            print(f"  {item}")
    else:
        print("データなし")
    
    print("\nproduct_master テーブル構造:")
    response = supabase.table("product_master").select("*").limit(5).execute()
    
    if response.data:
        print("サンプルデータ:")
        for item in response.data:
            print(f"  {item}")

if __name__ == "__main__":
    check_tables()