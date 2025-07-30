#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
簡易テストデータインポート
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from product_master.csv_import import CSVImporter
from supabase import create_client
from dotenv import load_dotenv
from datetime import datetime, timezone
import logging

# 環境変数の読み込み
load_dotenv()

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# Supabase接続
supabase = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_KEY')
)

def main():
    logger.info("テストデータのインポートを開始します...")
    
    importer = CSVImporter()
    test_data_dir = 'test_data'
    
    # 1. 商品マスターのインポート
    logger.info("\n[1/4] 商品マスターのインポート")
    logger.info("-" * 40)
    success, error = importer.import_product_master(
        os.path.join(test_data_dir, '商品番号マッピング基本表.csv')
    )
    logger.info(f"結果: 成功 {success}件, エラー {error}件")
    
    # 2. 選択肢コードのインポート
    logger.info("\n[2/4] 選択肢コードのインポート")
    logger.info("-" * 40)
    success, error = importer.import_choice_codes(
        os.path.join(test_data_dir, '選択肢コード対応表.csv')
    )
    logger.info(f"結果: 成功 {success}件, エラー {error}件")
    
    # 3. まとめ商品内訳のインポート
    logger.info("\n[3/4] まとめ商品内訳のインポート")
    logger.info("-" * 40)
    success, error = importer.import_package_components(
        os.path.join(test_data_dir, 'まとめ商品内訳テーブル.csv')
    )
    logger.info(f"結果: 成功 {success}件, エラー {error}件")
    
    # 4. テスト用在庫データの作成
    logger.info("\n[4/4] テスト用在庫データの作成")
    logger.info("-" * 40)
    
    # 楽天プラットフォームのIDを取得
    platform = supabase.table('platform').select('*').eq('platform_code', 'rakuten').execute()
    if platform.data:
        platform_id = platform.data[0]['id']
        
        # 在庫データを作成
        inventory_items = [
            {'code': 'CM001', 'name': 'エゾ鹿スライスジャーキー 30g', 'stock': 100},
            {'code': 'CM003', 'name': 'エゾ鹿ミンチジャーキー 30g', 'stock': 50},
            {'code': 'CM020', 'name': 'スライスサーモン 30g', 'stock': 75},
        ]
        
        for item in inventory_items:
            try:
                # 既存確認
                existing = supabase.table('inventory').select('*').eq(
                    'product_code', item['code']
                ).eq('platform_id', platform_id).execute()
                
                if existing.data:
                    # 更新
                    supabase.table('inventory').update({
                        'common_code': item['code'],
                        'current_stock': item['stock'],
                        'updated_at': datetime.now(timezone.utc).isoformat()
                    }).eq('id', existing.data[0]['id']).execute()
                else:
                    # 新規作成
                    supabase.table('inventory').insert({
                        'product_code': item['code'],
                        'product_name': item['name'],
                        'platform_id': platform_id,
                        'common_code': item['code'],
                        'current_stock': item['stock'],
                        'minimum_stock': 10,
                        'is_active': True,
                        'created_at': datetime.now(timezone.utc).isoformat(),
                        'updated_at': datetime.now(timezone.utc).isoformat()
                    }).execute()
                
                logger.info(f"✓ {item['code']}: 在庫 {item['stock']}個")
            except Exception as e:
                logger.error(f"✗ {item['code']}: {str(e)}")
    
    logger.info("\n" + "=" * 50)
    logger.info("インポート完了！")
    logger.info("=" * 50)
    
    # データ確認
    logger.info("\n確認用URL:")
    logger.info("- 単品商品: http://localhost:8000/product-stock/CM001")
    logger.info("- まとめ商品: http://localhost:8000/product-stock/PC001")

if __name__ == "__main__":
    main()
