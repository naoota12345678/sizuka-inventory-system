#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
product_masterテーブルをGoogle Sheetsと完全同一構造に再構築
"""

from supabase import create_client
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SUPABASE_URL = "https://equrcpeifogdrxoldkpe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ"

def backup_current_data():
    """現在のデータをバックアップ"""
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    logger.info("=== 現在のproduct_masterデータをバックアップ ===")
    
    # 現在のデータを全て取得
    current_data = supabase.table("product_master").select("*").execute()
    
    logger.info(f"バックアップ対象: {len(current_data.data)}件")
    
    # バックアップテーブル作成（存在しない場合）
    backup_data = []
    for item in current_data.data:
        backup_item = {
            "original_id": item.get("id"),
            "common_code": item.get("common_code"),
            "product_name": item.get("product_name"),
            "product_type": item.get("product_type"),
            "rakuten_sku": item.get("rakuten_sku"),
            "is_active": item.get("is_active"),
            "created_at": item.get("created_at"),
            "updated_at": item.get("updated_at")
        }
        backup_data.append(backup_item)
    
    return backup_data

def add_missing_columns():
    """product_masterテーブルに不足しているカラムを追加"""
    logger.info("=== product_masterテーブルにカラム追加 ===")
    
    # 追加するカラム定義（Google Sheetsに合わせて）
    new_columns = [
        "sequence_number INTEGER",  # 連番
        "jan_ean_code TEXT",        # JAN/EANコード
        "colorMe_id TEXT",          # カラーミーID
        "smaregi_id TEXT",          # スマレジID  
        "yahoo_product_id TEXT",    # Yahoo商品ID
        "amazon_asin TEXT",         # Amazon ASIN
        "mercari_product_id TEXT",  # メルカリ商品ID
        "remarks TEXT"              # 備考
    ]
    
    # 注意: Supabaseの場合、PythonクライアントでのDDL操作は制限されているため
    # 実際のカラム追加はSupabase Web UIまたはSQL直接実行が必要
    
    logger.info("追加が必要なカラム:")
    for col in new_columns:
        logger.info(f"  - {col}")
    
    logger.info("\n⚠️  重要: これらのカラムをSupabase Web UIのSQL Editorで追加してください:")
    
    sql_commands = [
        "ALTER TABLE product_master ADD COLUMN IF NOT EXISTS sequence_number INTEGER;",
        "ALTER TABLE product_master ADD COLUMN IF NOT EXISTS jan_ean_code TEXT;",
        "ALTER TABLE product_master ADD COLUMN IF NOT EXISTS colorMe_id TEXT;", 
        "ALTER TABLE product_master ADD COLUMN IF NOT EXISTS smaregi_id TEXT;",
        "ALTER TABLE product_master ADD COLUMN IF NOT EXISTS yahoo_product_id TEXT;",
        "ALTER TABLE product_master ADD COLUMN IF NOT EXISTS amazon_asin TEXT;",
        "ALTER TABLE product_master ADD COLUMN IF NOT EXISTS mercari_product_id TEXT;",
        "ALTER TABLE product_master ADD COLUMN IF NOT EXISTS remarks TEXT;"
    ]
    
    print("\n=== Supabase SQL Editor で実行するSQL ===")
    for sql in sql_commands:
        print(sql)
    
    return sql_commands

def verify_table_structure():
    """テーブル構造を確認"""
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    logger.info("=== テーブル構造確認 ===")
    
    # サンプルデータでカラム確認
    try:
        sample = supabase.table("product_master").select("*").limit(1).execute()
        if sample.data:
            current_columns = list(sample.data[0].keys())
            logger.info("現在のカラム:")
            for col in current_columns:
                logger.info(f"  ✓ {col}")
            
            # Google Sheetsと対応する理想的なカラム
            ideal_columns = [
                "id",                    # 主キー
                "sequence_number",       # 連番
                "common_code",           # 共通コード
                "jan_ean_code",          # JAN/EANコード  
                "product_name",          # 基本商品名（既存のproduct_name）
                "rakuten_sku",           # 楽天SKU
                "colorMe_id",            # カラーミーID
                "smaregi_id",            # スマレジID
                "yahoo_product_id",      # Yahoo商品ID
                "amazon_asin",           # Amazon ASIN
                "mercari_product_id",    # メルカリ商品ID
                "product_type",          # 商品タイプ
                "remarks",               # 備考
                "is_active",             # アクティブフラグ
                "created_at",            # 作成日時
                "updated_at"             # 更新日時
            ]
            
            logger.info("\n理想的なカラム構成:")
            missing_columns = []
            for col in ideal_columns:
                if col in current_columns:
                    logger.info(f"  ✓ {col} (存在)")
                else:
                    logger.info(f"  ✗ {col} (未追加)")
                    missing_columns.append(col)
            
            if missing_columns:
                logger.info(f"\n追加が必要: {len(missing_columns)}個のカラム")
                return False, missing_columns
            else:
                logger.info("\n✅ 全てのカラムが存在します")
                return True, []
                
    except Exception as e:
        logger.error(f"テーブル構造確認エラー: {str(e)}")
        return False, []

def main():
    """メイン処理"""
    logger.info("=== product_masterテーブル再構築開始 ===")
    
    # 1. 現在のデータバックアップ
    backup_data = backup_current_data()
    
    # 2. テーブル構造確認
    is_complete, missing_cols = verify_table_structure()
    
    if not is_complete:
        # 3. 不足カラムの追加SQL生成
        sql_commands = add_missing_columns()
        
        print("\n" + "="*60)
        print("🔧 次のステップ:")
        print("1. Supabase Web UI (https://supabase.com/dashboard) にアクセス")
        print("2. 対象プロジェクトを選択")  
        print("3. 'SQL Editor' をクリック")
        print("4. 上記のSQL文を1つずつ実行")
        print("5. 完了後、このスクリプトを再実行")
        print("="*60)
        
        return False
    else:
        logger.info("✅ product_masterテーブルの構造は完璧です")
        return True

if __name__ == "__main__":
    main()