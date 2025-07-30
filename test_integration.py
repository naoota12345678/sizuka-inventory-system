#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ローカル環境での統合テスト
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from supabase import create_client
from dotenv import load_dotenv
import logging
from datetime import datetime, timezone
import json

# 環境変数の読み込み
load_dotenv()

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Supabase接続
supabase = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_KEY')
)

def test_database_setup():
    """データベースセットアップの確認"""
    logger.info("=== データベースセットアップの確認 ===")
    
    from product_master.db_setup import verify_tables
    
    table_status = verify_tables()
    
    for table, exists in table_status.items():
        status = "✓ 存在" if exists else "✗ 存在しない"
        logger.info(f"{table}: {status}")
    
    return all(table_status.values())

def test_csv_import():
    """CSVインポートのテスト"""
    logger.info("\n=== CSVインポートのテスト ===")
    
    from product_master.csv_import import CSVImporter
    
    importer = CSVImporter()
    test_data_dir = 'test_data'
    
    # 商品マスターのインポート
    logger.info("\n--- 商品マスターのインポート ---")
    success, error = importer.import_product_master(
        os.path.join(test_data_dir, '商品番号マッピング基本表.csv')
    )
    logger.info(f"結果: 成功 {success}件, エラー {error}件")
    
    # インポート結果の確認
    products = supabase.table('product_master').select('*').execute()
    logger.info(f"商品マスター総数: {len(products.data)}件")
    
    # 選択肢コードのインポート
    logger.info("\n--- 選択肢コードのインポート ---")
    success, error = importer.import_choice_codes(
        os.path.join(test_data_dir, '選択肢コード対応表.csv')
    )
    logger.info(f"結果: 成功 {success}件, エラー {error}件")
    
    # まとめ商品内訳のインポート
    logger.info("\n--- まとめ商品内訳のインポート ---")
    success, error = importer.import_package_components(
        os.path.join(test_data_dir, 'まとめ商品内訳テーブル.csv')
    )
    logger.info(f"結果: 成功 {success}件, エラー {error}件")
    
    return True

def test_inventory_setup():
    """在庫データの初期設定"""
    logger.info("\n=== 在庫データの初期設定 ===")
    
    # 楽天のplatform_idを取得
    platform = supabase.table('platform').select('*').eq('platform_code', 'rakuten').execute()
    if not platform.data:
        logger.error("楽天プラットフォームが見つかりません")
        return False
    
    platform_id = platform.data[0]['id']
    
    # テスト用在庫データを作成
    test_inventory = [
        {'product_code': 'CM001', 'common_code': 'CM001', 'current_stock': 100},
        {'product_code': 'CM003', 'common_code': 'CM003', 'current_stock': 50},
        {'product_code': 'CM020', 'common_code': 'CM020', 'current_stock': 75},
    ]
    
    for item in test_inventory:
        # 既存データの確認
        existing = supabase.table('inventory').select('*').eq(
            'product_code', item['product_code']
        ).eq('platform_id', platform_id).execute()
        
        if existing.data:
            # 更新
            result = supabase.table('inventory').update({
                'common_code': item['common_code'],
                'current_stock': item['current_stock'],
                'updated_at': datetime.now(timezone.utc).isoformat()
            }).eq('id', existing.data[0]['id']).execute()
            logger.info(f"在庫更新: {item['product_code']} -> {item['current_stock']}個")
        else:
            # 新規作成
            result = supabase.table('inventory').insert({
                'product_code': item['product_code'],
                'product_name': f"テスト商品 {item['product_code']}",
                'platform_id': platform_id,
                'common_code': item['common_code'],
                'current_stock': item['current_stock'],
                'minimum_stock': 10,
                'is_active': True,
                'created_at': datetime.now(timezone.utc).isoformat(),
                'updated_at': datetime.now(timezone.utc).isoformat()
            }).execute()
            logger.info(f"在庫作成: {item['product_code']} -> {item['current_stock']}個")
    
    return True

def test_stock_calculation():
    """在庫計算のテスト"""
    logger.info("\n=== 在庫計算のテスト ===")
    
    # 単品商品の在庫確認
    logger.info("\n--- 単品商品の在庫 ---")
    single_products = ['CM001', 'CM003', 'CM020']
    
    for code in single_products:
        inventory = supabase.table('inventory').select('*').eq('common_code', code).execute()
        if inventory.data:
            logger.info(f"{code}: {inventory.data[0]['current_stock']}個")
    
    # まとめ商品の在庫計算
    logger.info("\n--- まとめ商品の在庫計算 ---")
    
    # PC001の構成品を確認
    components = supabase.table('package_components').select('*').eq('package_code', 'PC001').execute()
    
    if components.data:
        logger.info("PC001 (サスティナブルパック) の構成:")
        min_sets = float('inf')
        
        for comp in components.data:
            # 構成品の在庫を取得
            inv = supabase.table('inventory').select('*').eq(
                'common_code', comp['component_code']
            ).execute()
            
            if inv.data:
                stock = inv.data[0]['current_stock']
                quantity = comp['quantity']
                possible_sets = stock // quantity
                logger.info(f"  - {comp['component_code']}: {stock}個 ÷ {quantity}個/セット = {possible_sets}セット分")
                min_sets = min(min_sets, possible_sets)
            else:
                logger.info(f"  - {comp['component_code']}: 在庫なし")
                min_sets = 0
        
        logger.info(f"PC001の作成可能数: {int(min_sets)}セット")
    
    return True

def test_order_processing():
    """注文処理のテスト"""
    logger.info("\n=== 注文処理のテスト ===")
    
    # テスト注文を作成
    platform = supabase.table('platform').select('*').eq('platform_code', 'rakuten').execute()
    if not platform.data:
        return False
    
    platform_id = platform.data[0]['id']
    
    # 注文データを作成
    order_data = {
        'platform_id': platform_id,
        'order_number': f'TEST-{datetime.now().strftime("%Y%m%d%H%M%S")}',
        'order_date': datetime.now(timezone.utc).isoformat(),
        'total_amount': 5000,
        'order_status': 'test',
        'platform_data': json.dumps({'test': True}),
        'created_at': datetime.now(timezone.utc).isoformat(),
        'updated_at': datetime.now(timezone.utc).isoformat()
    }
    
    order_result = supabase.table('orders').insert(order_data).execute()
    if not order_result.data:
        logger.error("テスト注文の作成に失敗")
        return False
    
    order_id = order_result.data[0]['id']
    logger.info(f"テスト注文作成: {order_data['order_number']} (ID: {order_id})")
    
    # 注文商品を追加（まとめ商品PC001を1セット）
    item_data = {
        'order_id': order_id,
        'product_code': 'PC001',
        'product_name': 'サスティナブルパック150g シリーズ',
        'quantity': 1,
        'unit_price': 5000,
        'total_price': 5000,
        'created_at': datetime.now(timezone.utc).isoformat(),
        'updated_at': datetime.now(timezone.utc).isoformat()
    }
    
    item_result = supabase.table('order_items').insert(item_data).execute()
    logger.info("注文商品追加: PC001 x 1セット")
    
    # 在庫処理前の在庫を確認
    logger.info("\n--- 在庫処理前 ---")
    for code in ['CM001', 'CM003', 'CM020']:
        inv = supabase.table('inventory').select('current_stock').eq('common_code', code).execute()
        if inv.data:
            logger.info(f"{code}: {inv.data[0]['current_stock']}個")
    
    # ここで本来は注文処理を実行するが、今回は手動で在庫を減らす
    logger.info("\n--- 在庫処理をシミュレート ---")
    logger.info("PC001の構成品の在庫を1個ずつ減らします")
    
    # PC001の構成品の在庫を減らす
    components = supabase.table('package_components').select('*').eq('package_code', 'PC001').execute()
    for comp in components.data:
        inv = supabase.table('inventory').select('*').eq(
            'common_code', comp['component_code']
        ).execute()
        
        if inv.data:
            new_stock = inv.data[0]['current_stock'] - comp['quantity']
            supabase.table('inventory').update({
                'current_stock': new_stock,
                'updated_at': datetime.now(timezone.utc).isoformat()
            }).eq('id', inv.data[0]['id']).execute()
            
            # 在庫変動を記録
            movement_data = {
                'product_code': comp['component_code'],
                'platform_id': platform_id,
                'quantity': -comp['quantity'],
                'movement_type': 'order',
                'reference_id': order_id,
                'notes': f'テスト注文 - PC001の構成品',
                'movement_date': datetime.now(timezone.utc).isoformat(),
                'created_at': datetime.now(timezone.utc).isoformat(),
                'updated_at': datetime.now(timezone.utc).isoformat()
            }
            supabase.table('stock_movements').insert(movement_data).execute()
    
    # 在庫処理後の在庫を確認
    logger.info("\n--- 在庫処理後 ---")
    for code in ['CM001', 'CM003', 'CM020']:
        inv = supabase.table('inventory').select('current_stock').eq('common_code', code).execute()
        if inv.data:
            logger.info(f"{code}: {inv.data[0]['current_stock']}個")
    
    return True

def main():
    """メインテスト実行"""
    logger.info("商品マスター統合テストを開始します")
    logger.info("=" * 60)
    
    tests = [
        ("データベースセットアップ確認", test_database_setup),
        ("CSVインポート", test_csv_import),
        ("在庫初期設定", test_inventory_setup),
        ("在庫計算", test_stock_calculation),
        ("注文処理", test_order_processing),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            logger.info(f"\n### {test_name} ###")
            result = test_func()
            results.append((test_name, "成功" if result else "失敗"))
        except Exception as e:
            logger.error(f"{test_name}でエラー: {str(e)}")
            results.append((test_name, "エラー"))
    
    # テスト結果サマリー
    logger.info("\n" + "=" * 60)
    logger.info("テスト結果サマリー")
    logger.info("=" * 60)
    for test_name, result in results:
        status = "✓" if result == "成功" else "✗"
        logger.info(f"{status} {test_name}: {result}")

if __name__ == "__main__":
    main()
