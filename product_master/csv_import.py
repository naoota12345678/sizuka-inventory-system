#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
CSVファイルから商品マスターデータをインポートするスクリプト
Google Sheetsが使えない場合の代替手段
"""

import pandas as pd
from supabase import create_client
import os
from datetime import datetime, timezone
import logging
from dotenv import load_dotenv
from typing import Optional

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

class CSVImporter:
    """CSVファイルからのインポート処理"""
    
    def __init__(self):
        self.supabase = supabase
    
    def clean_value(self, value):
        """データのクリーニング"""
        if pd.isna(value) or value == '':
            return None
        return str(value).strip()
    
    def determine_product_type(self, common_code, type_str=None):
        """商品タイプを判定"""
        if common_code.startswith('CM'):
            return '単品'
        elif common_code.startswith('BC'):
            if 'チョイス' in str(type_str) or '選択' in str(type_str):
                return 'セット(選択)'
            else:
                return 'セット(固定)'
        elif common_code.startswith('PC'):
            if '複合' in str(type_str):
                return 'まとめ(複合)'
            else:
                return 'まとめ(固定)'
        return '単品'
    
    def import_product_master(self, csv_file_path: str):
        """商品番号マッピング基本表をインポート"""
        logger.info(f"商品マスターデータのインポートを開始: {csv_file_path}")
        
        # CSVファイルの読み込み
        df = pd.read_csv(csv_file_path, encoding='utf-8')
        
        success_count = 0
        error_count = 0
        
        for index, row in df.iterrows():
            try:
                common_code = self.clean_value(row.get('共通コード'))
                if not common_code:
                    continue
                
                # 商品タイプの判定
                product_type = self.determine_product_type(
                    common_code, 
                    row.get('商品タイプ', '')
                )
                
                # 楽天SKUの処理
                rakuten_sku = self.clean_value(row.get('楽天SKU', ''))
                if rakuten_sku and '/' in rakuten_sku:
                    rakuten_sku = rakuten_sku.split('/')[0]
                
                # データの準備
                product_data = {
                    'common_code': common_code,
                    'jan_code': self.clean_value(row.get('JAN/EANコード')),
                    'product_name': self.clean_value(row.get('基本商品名')),
                    'product_type': product_type,
                    'rakuten_sku': rakuten_sku,
                    'colorme_id': self.clean_value(row.get('カラーミーID')),
                    'smaregi_id': self.clean_value(row.get('スマレジID')),
                    'yahoo_id': self.clean_value(row.get('Yahoo商品ID')),
                    'amazon_asin': self.clean_value(row.get('Amazon ASIN')),
                    'mercari_id': self.clean_value(row.get('メルカリ商品ID')),
                    'remarks': self.clean_value(row.get('備考')),
                    'is_limited': '限定' in str(row.get('備考', '')),
                    'is_active': True,
                    'created_at': datetime.now(timezone.utc).isoformat(),
                    'updated_at': datetime.now(timezone.utc).isoformat()
                }
                
                # Supabaseに挿入（既存データがある場合は更新）
                result = self.supabase.table('product_master').upsert(
                    product_data,
                    on_conflict='common_code'
                ).execute()
                
                success_count += 1
                logger.info(f"✓ {common_code}: {product_data['product_name']}")
                
            except Exception as e:
                error_count += 1
                logger.error(f"✗ 行 {index + 1}: {str(e)}")
        
        logger.info(f"商品マスター: 成功 {success_count}件, エラー {error_count}件")
        return success_count, error_count
    
    def import_choice_codes(self, csv_file_path: str):
        """選択肢コード対応表をインポート"""
        logger.info(f"選択肢コード対応表のインポートを開始: {csv_file_path}")
        
        df = pd.read_csv(csv_file_path, encoding='utf-8')
        
        success_count = 0
        error_count = 0
        
        for index, row in df.iterrows():
            try:
                choice_code = self.clean_value(row.get('選択肢コード'))
                common_code = self.clean_value(row.get('新共通コード'))
                
                if not choice_code or not common_code:
                    continue
                
                # データの準備
                choice_data = {
                    'choice_code': choice_code,
                    'common_code': common_code,
                    'jan_code': self.clean_value(row.get('JAN')),
                    'rakuten_sku': self.clean_value(row.get('楽天SKU管理番号')),
                    'product_name': self.clean_value(row.get('商品名')),
                    'created_at': datetime.now(timezone.utc).isoformat(),
                    'updated_at': datetime.now(timezone.utc).isoformat()
                }
                
                # Supabaseに挿入
                result = self.supabase.table('choice_code_mapping').upsert(
                    choice_data,
                    on_conflict='choice_code'
                ).execute()
                
                success_count += 1
                logger.info(f"✓ {choice_code} -> {common_code}")
                
            except Exception as e:
                error_count += 1
                logger.error(f"✗ 行 {index + 1}: {str(e)}")
        
        logger.info(f"選択肢コード: 成功 {success_count}件, エラー {error_count}件")
        return success_count, error_count
    
    def import_package_components(self, csv_file_path: str):
        """まとめ商品内訳をインポート"""
        logger.info(f"まとめ商品内訳のインポートを開始: {csv_file_path}")
        
        df = pd.read_csv(csv_file_path, encoding='utf-8')
        
        # 既存データを削除（完全入れ替え）
        self.supabase.table('package_components').delete().neq('id', 0).execute()
        
        success_count = 0
        error_count = 0
        
        for index, row in df.iterrows():
            try:
                package_code = self.clean_value(row.get('まとめ商品共通コード'))
                component_code = self.clean_value(row.get('構成品共通コード'))
                
                if not package_code or not component_code:
                    continue
                
                # データの準備
                component_data = {
                    'detail_id': int(row.get('内訳ID')) if pd.notna(row.get('内訳ID')) else None,
                    'package_code': package_code,
                    'package_name': self.clean_value(row.get('まとめ商品名')),
                    'component_code': component_code,
                    'quantity': int(row.get('数量', 1)),
                    'remarks': self.clean_value(row.get('備考')),
                    'created_at': datetime.now(timezone.utc).isoformat(),
                    'updated_at': datetime.now(timezone.utc).isoformat()
                }
                
                # Supabaseに挿入
                result = self.supabase.table('package_components').insert(
                    component_data
                ).execute()
                
                success_count += 1
                logger.info(f"✓ {package_code} <- {component_code} x {component_data['quantity']}")
                
            except Exception as e:
                error_count += 1
                logger.error(f"✗ 行 {index + 1}: {str(e)}")
        
        logger.info(f"まとめ商品内訳: 成功 {success_count}件, エラー {error_count}件")
        return success_count, error_count

def main():
    """メイン実行関数"""
    importer = CSVImporter()
    
    # CSVファイルのパスを指定
    csv_files = {
        'product_master': 'data/商品番号マッピング基本表.csv',
        'choice_codes': 'data/選択肢コード対応表.csv',
        'package_components': 'data/まとめ商品内訳テーブル.csv'
    }
    
    results = {}
    
    # 商品マスター
    if os.path.exists(csv_files['product_master']):
        success, error = importer.import_product_master(csv_files['product_master'])
        results['product_master'] = {'success': success, 'error': error}
    else:
        logger.warning(f"ファイルが見つかりません: {csv_files['product_master']}")
    
    # 選択肢コード
    if os.path.exists(csv_files['choice_codes']):
        success, error = importer.import_choice_codes(csv_files['choice_codes'])
        results['choice_codes'] = {'success': success, 'error': error}
    else:
        logger.warning(f"ファイルが見つかりません: {csv_files['choice_codes']}")
    
    # まとめ商品内訳
    if os.path.exists(csv_files['package_components']):
        success, error = importer.import_package_components(csv_files['package_components'])
        results['package_components'] = {'success': success, 'error': error}
    else:
        logger.warning(f"ファイルが見つかりません: {csv_files['package_components']}")
    
    logger.info(f"\n===== インポート完了 =====")
    logger.info(f"結果: {results}")

if __name__ == "__main__":
    main()
