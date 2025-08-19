#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Amazon商品マッピング設定スクリプト
楽天と同じ共通コードにマッピング
"""

import os
from supabase import create_client
import logging

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Supabase接続
SUPABASE_URL = os.getenv('SUPABASE_URL', 'https://equrcpeifogdrxoldkpe.supabase.co')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ')

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def setup_amazon_product_mapping():
    """
    Amazon商品と共通コードのマッピングを設定
    楽天と同じ商品は同じ共通コードを使用
    """
    
    # マッピングデータ（例）
    # 実際のマッピングはユーザーが設定
    amazon_mappings = [
        # Amazon SKU, 共通コード, 商品名, ASIN
        ('ECHO-DOT-4', 'CM001', 'Echo Dot 第4世代', 'B084DWX1PV'),
        ('FIRE-TV-4K', 'CM002', 'Fire TV Stick 4K', 'B079QRQTCR'),
        ('KINDLE-PAPER', 'CM003', 'Kindle Paperwhite', 'B08N41Y4Q2'),
        
        # 楽天と同じ商品の場合、同じ共通コードを使用
        ('AMZ-ITEM-001', 'CM018', '共通商品A', 'B001EXAMPLE'),
        ('AMZ-ITEM-002', 'CM034', '共通商品B', 'B002EXAMPLE'),
        
        # Amazon限定商品
        ('AMZ-EXCLUSIVE-001', 'AM001', 'Amazon限定商品1', 'B901EXAMPLE'),
        ('AMZ-EXCLUSIVE-002', 'AM002', 'Amazon限定商品2', 'B902EXAMPLE'),
    ]
    
    success_count = 0
    error_count = 0
    
    for amazon_sku, common_code, product_name, asin in amazon_mappings:
        try:
            # 既存チェック
            existing = supabase.table('amazon_product_master').select('id').eq('amazon_sku', amazon_sku).execute()
            
            if existing.data:
                # 更新
                result = supabase.table('amazon_product_master').update({
                    'common_code': common_code,
                    'product_name': product_name,
                    'asin': asin
                }).eq('amazon_sku', amazon_sku).execute()
                
                logger.info(f"更新: {amazon_sku} → {common_code}")
            else:
                # 新規作成
                result = supabase.table('amazon_product_master').insert({
                    'amazon_sku': amazon_sku,
                    'common_code': common_code,
                    'product_name': product_name,
                    'asin': asin
                }).execute()
                
                logger.info(f"追加: {amazon_sku} → {common_code}")
            
            success_count += 1
            
        except Exception as e:
            logger.error(f"エラー: {amazon_sku} - {str(e)}")
            error_count += 1
    
    logger.info(f"\n完了: 成功 {success_count}件, エラー {error_count}件")
    
    return success_count, error_count

def import_from_csv(csv_file_path):
    """
    CSVファイルからマッピングをインポート
    
    CSVフォーマット:
    amazon_sku,common_code,product_name,asin
    """
    import csv
    
    mappings = []
    
    try:
        with open(csv_file_path, 'r', encoding='utf-8-sig') as file:
            reader = csv.DictReader(file)
            for row in reader:
                mappings.append([
                    row['amazon_sku'],
                    row['common_code'],
                    row['product_name'],
                    row.get('asin', '')
                ])
        
        logger.info(f"CSVから{len(mappings)}件のマッピングを読み込みました")
        
        # データベースに保存
        success_count = 0
        for mapping in mappings:
            try:
                result = supabase.table('amazon_product_master').upsert({
                    'amazon_sku': mapping[0],
                    'common_code': mapping[1],
                    'product_name': mapping[2],
                    'asin': mapping[3]
                }, on_conflict='amazon_sku').execute()
                
                success_count += 1
                
            except Exception as e:
                logger.error(f"エラー: {mapping[0]} - {str(e)}")
        
        logger.info(f"インポート完了: {success_count}/{len(mappings)}件")
        
    except FileNotFoundError:
        logger.error(f"CSVファイルが見つかりません: {csv_file_path}")
    except Exception as e:
        logger.error(f"CSVインポートエラー: {str(e)}")

def check_mapping_coverage():
    """
    マッピングのカバレッジを確認
    """
    # Amazon注文商品の全SKUを取得
    items = supabase.table('amazon_order_items').select('product_code').execute()
    unique_skus = set(item['product_code'] for item in (items.data or []))
    
    # マッピング済みSKUを取得
    mapped = supabase.table('amazon_product_master').select('amazon_sku').execute()
    mapped_skus = set(item['amazon_sku'] for item in (mapped.data or []))
    
    # 統計
    total_skus = len(unique_skus)
    mapped_count = len(unique_skus & mapped_skus)
    unmapped_skus = unique_skus - mapped_skus
    
    logger.info(f"\n=== マッピングカバレッジ ===")
    logger.info(f"総SKU数: {total_skus}")
    logger.info(f"マッピング済み: {mapped_count} ({mapped_count/total_skus*100:.1f}%)")
    logger.info(f"未マッピング: {len(unmapped_skus)}")
    
    if unmapped_skus:
        logger.info(f"\n未マッピングSKU（上位10件）:")
        for sku in list(unmapped_skus)[:10]:
            logger.info(f"  - {sku}")
    
    return {
        'total': total_skus,
        'mapped': mapped_count,
        'unmapped': list(unmapped_skus)
    }

def main():
    """メイン処理"""
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == 'import' and len(sys.argv) > 2:
            # CSVインポート
            import_from_csv(sys.argv[2])
        elif sys.argv[1] == 'check':
            # カバレッジ確認
            check_mapping_coverage()
        else:
            print("使用方法:")
            print("  python setup_amazon_mapping.py          # サンプルマッピング設定")
            print("  python setup_amazon_mapping.py import <CSVファイル>  # CSVインポート")
            print("  python setup_amazon_mapping.py check    # カバレッジ確認")
    else:
        # デフォルト: サンプルマッピング設定
        setup_amazon_product_mapping()

if __name__ == "__main__":
    main()