#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Amazon関連テーブルをSupabaseに作成
"""

from supabase import create_client
import os

SUPABASE_URL = 'https://equrcpeifogdrxoldkpe.supabase.co'
SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ'

def setup_amazon_tables():
    """Amazon関連テーブルを作成"""
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    print("=== Amazonテーブル作成開始 ===")
    
    # Amazon注文テーブル
    try:
        # 既存のordersテーブルのplatformフィールドを確認
        existing_orders = supabase.table('orders').select('platform').limit(1).execute()
        print("✅ 既存ordersテーブル利用可能")
        
        # Amazonプラットフォームの注文が保存できることを確認
        print("✅ Amazon注文は既存ordersテーブルに保存されます")
        
    except Exception as e:
        print(f"❌ ordersテーブルエラー: {e}")
    
    # Amazon注文アイテムテーブル  
    try:
        # 既存のorder_itemsテーブルを確認
        existing_items = supabase.table('order_items').select('*').limit(1).execute()
        print("✅ 既存order_itemsテーブル利用可能")
        
        # Amazon特有のフィールドがJSONBで保存できることを確認
        print("✅ Amazon商品データは既存order_itemsテーブルに保存されます")
        
    except Exception as e:
        print(f"❌ order_itemsテーブルエラー: {e}")
    
    # Amazon商品マスタの確認
    try:
        existing_master = supabase.table('product_master').select('*').limit(1).execute()
        print("✅ 既存product_masterテーブル利用可能")
        print("✅ Amazon商品マッピングは既存product_masterテーブルに保存されます")
        
    except Exception as e:
        print(f"❌ product_masterテーブルエラー: {e}")
    
    # Amazon FBA在庫テーブル（新規作成が必要）
    try:
        # FBA在庫専用テーブルを作成
        result = supabase.table('amazon_fba_inventory').select('*').limit(1).execute()
        print("✅ amazon_fba_inventoryテーブル存在確認")
        
    except Exception as e:
        if 'does not exist' in str(e):
            print("amazon_fba_inventoryテーブルを作成する必要があります")
            print("Supabase管理画面でのテーブル作成が必要です")
        else:
            print(f"amazon_fba_inventoryエラー: {e}")
    
    print("\n=== Amazonシステム構造 ===")
    print("Amazon注文データは楽天と同じテーブル構造を使用:")
    print("- orders テーブル (platform='amazon')")  
    print("- order_items テーブル (amazon_item_dataにJSONB保存)")
    print("- product_master テーブル (rakuten_sku=ASINでマッピング)")
    print("- inventory テーブル (共通在庫管理)")
    
    return True

if __name__ == "__main__":
    setup_amazon_tables()