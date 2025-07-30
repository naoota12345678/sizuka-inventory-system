#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
簡易テストデータインポート（pandasなし版）
"""

import os
import sys
import csv
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

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

def import_product_master_simple():
    """商品マスターの簡易インポート"""
    logger.info("\n[1/4] 商品マスターのインポート")
    logger.info("-" * 40)
    
    success_count = 0
    
    # ハードコードされたテストデータ
    products = [
        {
            'common_code': 'CM001',
            'jan_code': '4573265581011',
            'product_name': 'エゾ鹿スライスジャーキー 30g',
            'product_type': '単品',
            'rakuten_sku': '1701'
        },
        {
            'common_code': 'CM003',
            'jan_code': '4573265581028',
            'product_name': 'エゾ鹿ミンチジャーキー 30g',
            'product_type': '単品',
            'rakuten_sku': '1703'
        },
        {
            'common_code': 'CM020',
            'jan_code': '4573265581158',
            'product_name': 'スライスサーモン 30g',
            'product_type': '単品',
            'rakuten_sku': '1715'
        },
        {
            'common_code': 'PC001',
            'jan_code': '4573265581943',
            'product_name': 'サスティナブルパック150g シリーズ',
            'product_type': 'まとめ(複合)',
            'rakuten_sku': '1851'
        }
    ]
    
    for product in products:
        try:
            product['is_active'] = True
            product['created_at'] = datetime.now(timezone.utc).isoformat()
            product['updated_at'] = datetime.now(timezone.utc).isoformat()
            
            result = supabase.table('product_master').upsert(
                product,
                on_conflict='common_code'
            ).execute()
            
            success_count += 1
            logger.info(f"✓ {product['common_code']}: {product['product_name']}")
            
        except Exception as e:
            logger.error(f"✗ {product['common_code']}: {str(e)}")
    
    logger.info(f"結果: 成功 {success_count}件")
    return success_count

def import_choice_codes_simple():
    """選択肢コードの簡易インポート"""
    logger.info("\n[2/4] 選択肢コードのインポート")
    logger.info("-" * 40)
    
    success_count = 0
    
    choices = [
        {'choice_code': 'R01', 'common_code': 'CM001', 'product_name': 'エゾ鹿スライスジャーキー 30g'},
        {'choice_code': 'R02', 'common_code': 'CM003', 'product_name': 'エゾ鹿ミンチジャーキー 30g'},
        {'choice_code': 'R06', 'common_code': 'CM020', 'product_name': 'スライスサーモン 30g'},
    ]
    
    for choice in choices:
        try:
            choice['created_at'] = datetime.now(timezone.utc).isoformat()
            choice['updated_at'] = datetime.now(timezone.utc).isoformat()
            
            result = supabase.table('choice_code_mapping').upsert(
                choice,
                on_conflict='choice_code'
            ).execute()
            
            success_count += 1
            logger.info(f"✓ {choice['choice_code']} -> {choice['common_code']}")
            
        except Exception as e:
            logger.error(f"✗ {choice['choice_code']}: {str(e)}")
    
    logger.info(f"結果: 成功 {success_count}件")
    return success_count

def import_package_components_simple():
    """まとめ商品内訳の簡易インポート"""
    logger.info("\n[3/4] まとめ商品内訳のインポート")
    logger.info("-" * 40)
    
    # 既存データを削除
    supabase.table('package_components').delete().neq('id', 0).execute()
    
    success_count = 0
    
    components = [
        {
            'detail_id': 1,
            'package_code': 'PC001',
            'package_name': 'サスティナブルパック150g エゾ鹿スライス',
            'component_code': 'CM001',
            'quantity': 1
        },
        {
            'detail_id': 2,
            'package_code': 'PC001',
            'package_name': 'サスティナブルパック150g ころころエゾ鹿ミンチ',
            'component_code': 'CM003',
            'quantity': 1
        },
        {
            'detail_id': 3,
            'package_code': 'PC001',
            'package_name': 'サスティナブルパック150g スライスサーモン',
            'component_code': 'CM020',
            'quantity': 1
        }
    ]
    
    for comp in components:
        try:
            comp['created_at'] = datetime.now(timezone.utc).isoformat()
            comp['updated_at'] = datetime.now(timezone.utc).isoformat()
            
            result = supabase.table('package_components').insert(comp).execute()
            
            success_count += 1
            logger.info(f"✓ {comp['package_code']} <- {comp['component_code']} x {comp['quantity']}")
            
        except Exception as e:
            logger.error(f"✗ エラー: {str(e)}")
    
    logger.info(f"結果: 成功 {success_count}件")
    return success_count

def create_test_inventory():
    """テスト用在庫データの作成"""
    logger.info("\n[4/4] テスト用在庫データの作成")
    logger.info("-" * 40)
    
    # 楽天プラットフォームのIDを取得
    platform = supabase.table('platform').select('*').eq('platform_code', 'rakuten').execute()
    if not platform.data:
        logger.error("楽天プラットフォームが見つかりません")
        return
    
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

def main():
    logger.info("テストデータのインポートを開始します...")
    
    # 各データをインポート
    import_product_master_simple()
    import_choice_codes_simple()
    import_package_components_simple()
    create_test_inventory()
    
    logger.info("\n" + "=" * 50)
    logger.info("インポート完了！")
    logger.info("=" * 50)
    
    # データ確認
    logger.info("\n確認用URL:")
    logger.info("- 単品商品: http://localhost:8000/product-stock/CM001")
    logger.info("- まとめ商品: http://localhost:8000/product-stock/PC001")
    logger.info("\nPC001は3つの商品で構成されています:")
    logger.info("- CM001 (在庫100個) x 1")
    logger.info("- CM003 (在庫50個) x 1")
    logger.info("- CM020 (在庫75個) x 1")
    logger.info("→ PC001の作成可能数: 50セット（最小在庫の商品に依存）")

if __name__ == "__main__":
    main()
