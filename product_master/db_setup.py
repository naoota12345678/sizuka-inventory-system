#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
データベーステーブルの自動セットアップスクリプト
"""

from supabase import create_client
import os
import logging
from dotenv import load_dotenv

# 環境変数の読み込み
load_dotenv()

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Supabase接続
supabase = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_KEY')
)

def check_table_exists(table_name: str) -> bool:
    """テーブルの存在確認"""
    try:
        # テーブルから1件だけ取得を試みる
        result = supabase.table(table_name).select("*").limit(1).execute()
        return True
    except Exception as e:
        if "relation" in str(e) and "does not exist" in str(e):
            return False
        # その他のエラーは再発生させる
        raise

def create_product_master_tables():
    """商品マスター関連テーブルを作成"""
    logger.info("商品マスターテーブルの作成を開始します...")
    
    # 各テーブルの作成SQLを定義
    tables_sql = [
        # 1. 商品マスターテーブル
        """
        CREATE TABLE IF NOT EXISTS product_master (
            id SERIAL PRIMARY KEY,
            common_code VARCHAR(10) UNIQUE NOT NULL,
            jan_code VARCHAR(13),
            product_name VARCHAR(255) NOT NULL,
            product_type VARCHAR(20) NOT NULL,
            rakuten_sku VARCHAR(50),
            colorme_id VARCHAR(50),
            smaregi_id VARCHAR(50),
            yahoo_id VARCHAR(50),
            amazon_asin VARCHAR(50),
            mercari_id VARCHAR(50),
            rakuten_parent_sku VARCHAR(50),
            rakuten_choice_code VARCHAR(10),
            remarks TEXT,
            is_limited BOOLEAN DEFAULT FALSE,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        """,
        
        # 2. 選択肢コード対応表
        """
        CREATE TABLE IF NOT EXISTS choice_code_mapping (
            id SERIAL PRIMARY KEY,
            choice_code VARCHAR(10) UNIQUE NOT NULL,
            common_code VARCHAR(10) NOT NULL,
            jan_code VARCHAR(13),
            rakuten_sku VARCHAR(50),
            product_name VARCHAR(255),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (common_code) REFERENCES product_master(common_code) ON DELETE CASCADE
        );
        """,
        
        # 3. セット商品構成テーブル
        """
        CREATE TABLE IF NOT EXISTS bundle_components (
            id SERIAL PRIMARY KEY,
            bundle_code VARCHAR(10) NOT NULL,
            component_code VARCHAR(10) NOT NULL,
            is_selectable BOOLEAN DEFAULT FALSE,
            selection_group VARCHAR(50),
            required_count INTEGER DEFAULT 1,
            display_order INTEGER,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (bundle_code) REFERENCES product_master(common_code) ON DELETE CASCADE,
            FOREIGN KEY (component_code) REFERENCES product_master(common_code) ON DELETE CASCADE,
            UNIQUE(bundle_code, component_code)
        );
        """,
        
        # 4. まとめ商品構成テーブル
        """
        CREATE TABLE IF NOT EXISTS package_components (
            id SERIAL PRIMARY KEY,
            detail_id INTEGER,
            package_code VARCHAR(10) NOT NULL,
            package_name VARCHAR(255),
            component_code VARCHAR(10) NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 1,
            remarks TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (package_code) REFERENCES product_master(common_code) ON DELETE CASCADE,
            FOREIGN KEY (component_code) REFERENCES product_master(common_code) ON DELETE CASCADE
        );
        """,
        
        # 5. インデックスの作成
        """
        CREATE INDEX IF NOT EXISTS idx_product_master_common_code ON product_master(common_code);
        CREATE INDEX IF NOT EXISTS idx_product_master_product_type ON product_master(product_type);
        CREATE INDEX IF NOT EXISTS idx_product_master_rakuten_sku ON product_master(rakuten_sku);
        CREATE INDEX IF NOT EXISTS idx_choice_code_mapping_choice_code ON choice_code_mapping(choice_code);
        CREATE INDEX IF NOT EXISTS idx_bundle_components_bundle_code ON bundle_components(bundle_code);
        CREATE INDEX IF NOT EXISTS idx_package_components_package_code ON package_components(package_code);
        """,
        
        # 6. 在庫テーブルの拡張
        """
        ALTER TABLE inventory 
        ADD COLUMN IF NOT EXISTS common_code VARCHAR(10);
        """,
        
        # 7. 在庫ビューの作成
        """
        CREATE OR REPLACE VIEW available_stock_view AS
        WITH component_stock AS (
            -- 単品の在庫
            SELECT 
                pm.common_code,
                pm.product_name,
                pm.product_type,
                COALESCE(i.current_stock, 0) as available_stock
            FROM product_master pm
            LEFT JOIN inventory i ON pm.common_code = i.common_code
            WHERE pm.product_type = '単品'
            
            UNION ALL
            
            -- まとめ商品の在庫（構成品の在庫から計算）
            SELECT 
                pm.common_code,
                pm.product_name,
                pm.product_type,
                CASE 
                    WHEN MIN(FLOOR(COALESCE(i.current_stock, 0) / pc.quantity)) IS NULL THEN 0
                    ELSE MIN(FLOOR(COALESCE(i.current_stock, 0) / pc.quantity))
                END as available_stock
            FROM product_master pm
            JOIN package_components pc ON pm.common_code = pc.package_code
            LEFT JOIN inventory i ON pc.component_code = i.common_code
            WHERE pm.product_type IN ('まとめ(固定)', 'まとめ(複合)')
            GROUP BY pm.common_code, pm.product_name, pm.product_type
            
            UNION ALL
            
            -- セット商品の在庫（固定構成品の最小在庫）
            SELECT 
                pm.common_code,
                pm.product_name,
                pm.product_type,
                CASE 
                    WHEN MIN(COALESCE(i.current_stock, 0)) IS NULL THEN 0
                    ELSE MIN(COALESCE(i.current_stock, 0))
                END as available_stock
            FROM product_master pm
            JOIN bundle_components bc ON pm.common_code = bc.bundle_code
            LEFT JOIN inventory i ON bc.component_code = i.common_code
            WHERE pm.product_type IN ('セット(固定)', 'セット(選択)')
              AND bc.is_selectable = FALSE
            GROUP BY pm.common_code, pm.product_name, pm.product_type
        )
        SELECT * FROM component_stock;
        """
    ]
    
    # 各SQLを実行
    for i, sql in enumerate(tables_sql, 1):
        try:
            # Supabase の RPC を使用してSQLを実行
            # 注: Supabaseでは直接SQLを実行する機能が限定的なため、
            # ダッシュボードまたはSupabase CLIでの実行を推奨
            logger.info(f"SQLスクリプト {i}/{len(tables_sql)} を実行中...")
            # ここでは実行をスキップし、SQLをログに出力
            logger.info(f"実行予定のSQL:\n{sql[:200]}...")
        except Exception as e:
            logger.error(f"SQLスクリプト {i} の実行エラー: {str(e)}")
    
    logger.info("商品マスターテーブルの作成処理を完了しました")

def verify_tables():
    """作成されたテーブルの確認"""
    tables = [
        'product_master',
        'choice_code_mapping',
        'bundle_components',
        'package_components'
    ]
    
    logger.info("テーブルの存在確認を開始します...")
    
    results = {}
    for table in tables:
        exists = check_table_exists(table)
        results[table] = exists
        logger.info(f"{table}: {'存在' if exists else '存在しない'}")
    
    return results

def initialize_database():
    """データベースの初期化（メイン関数）"""
    logger.info("データベース初期化を開始します...")
    
    # テーブルの存在確認
    existing_tables = verify_tables()
    
    # 存在しないテーブルがある場合は作成
    if not all(existing_tables.values()):
        logger.warning("一部のテーブルが存在しません。Supabaseダッシュボードで以下のSQLを実行してください：")
        create_product_master_tables()
    else:
        logger.info("すべてのテーブルが既に存在します")
    
    return existing_tables

if __name__ == "__main__":
    initialize_database()
