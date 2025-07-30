#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
テスト用CSVインポートスクリプト
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from product_master.csv_import import CSVImporter
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """テストデータをインポート"""
    importer = CSVImporter()
    
    # テストデータのパス
    test_data_dir = os.path.join(os.path.dirname(__file__), 'test_data')
    
    csv_files = {
        'product_master': os.path.join(test_data_dir, '商品番号マッピング基本表.csv'),
        'choice_codes': os.path.join(test_data_dir, '選択肢コード対応表.csv'),
        'package_components': os.path.join(test_data_dir, 'まとめ商品内訳テーブル.csv')
    }
    
    results = {}
    
    # 商品マスター
    logger.info("=" * 50)
    logger.info("商品マスターのインポート開始")
    logger.info("=" * 50)
    if os.path.exists(csv_files['product_master']):
        success, error = importer.import_product_master(csv_files['product_master'])
        results['product_master'] = {'success': success, 'error': error}
    
    # 選択肢コード
    logger.info("\n" + "=" * 50)
    logger.info("選択肢コードのインポート開始")
    logger.info("=" * 50)
    if os.path.exists(csv_files['choice_codes']):
        success, error = importer.import_choice_codes(csv_files['choice_codes'])
        results['choice_codes'] = {'success': success, 'error': error}
    
    # まとめ商品内訳
    logger.info("\n" + "=" * 50)
    logger.info("まとめ商品内訳のインポート開始")
    logger.info("=" * 50)
    if os.path.exists(csv_files['package_components']):
        success, error = importer.import_package_components(csv_files['package_components'])
        results['package_components'] = {'success': success, 'error': error}
    
    logger.info("\n" + "=" * 50)
    logger.info("インポート結果サマリー")
    logger.info("=" * 50)
    for table, result in results.items():
        logger.info(f"{table}: 成功 {result['success']}件, エラー {result['error']}件")

if __name__ == "__main__":
    main()
