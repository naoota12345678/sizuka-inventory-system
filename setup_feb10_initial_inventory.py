#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
2024年2月10日時点の初期在庫設定
完全な在庫管理システムを構築するための基準日設定

実行手順:
1. DRY RUN で現在の在庫を確認
2. 2024年2月10日の初期在庫数を設定
3. 2月10日以降の売上データを在庫変動に反映
"""

from supabase import create_client
from datetime import datetime, timezone
import logging

# ロギング設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Supabase設定
SUPABASE_URL = "https://equrcpeifogdrxoldkpe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ"

def setup_feb10_initial_inventory(dry_run=True):
    """2024年2月10日基準の初期在庫を設定"""
    
    logger.info("=== 2024年2月10日初期在庫設定 ===")
    logger.info(f"DRY RUN: {dry_run}")
    
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # 現在の在庫状況を確認
    current_inventory = supabase.table('inventory').select('*').execute()
    
    logger.info("現在の在庫状況:")
    for item in current_inventory.data:
        logger.info(f"- {item['common_code']}: {item['current_stock']}個")
    
    # 2024年2月10日～2025年8月3日の売上による在庫変動を計算
    logger.info("\n=== 2024/2/10以降の売上による在庫変動計算 ===")
    
    # この期間の売上データを取得し、在庫変動を逆算
    sales_impact = calculate_sales_impact_since_feb10(supabase)
    
    # 2024年2月10日の推定初期在庫を計算
    logger.info("\n=== 2024/2/10推定初期在庫 ===")
    feb10_inventory = {}
    
    for item in current_inventory.data:
        common_code = item['common_code']
        current_stock = item['current_stock']
        sales_reduction = sales_impact.get(common_code, 0)
        
        # 初期在庫 = 現在在庫 + 売上による減少分
        estimated_initial = current_stock + sales_reduction
        feb10_inventory[common_code] = estimated_initial
        
        logger.info(f"- {common_code}: {estimated_initial}個 (現在{current_stock} + 売上減{sales_reduction})")
    
    if not dry_run:
        # 実際に在庫テーブルを更新（基準日を2024/2/10に設定）
        logger.info("\n=== 在庫テーブル更新実行 ===")
        
        for common_code, initial_stock in feb10_inventory.items():
            result = supabase.table('inventory').update({
                'current_stock': initial_stock,
                'created_at': '2024-02-10T00:00:00+00:00',  # 基準日を2024/2/10に設定
                'reference_date': '2024-02-10'  # 基準日記録用フィールド
            }).eq('common_code', common_code).execute()
            
            if result.data:
                logger.info(f"✅ {common_code}を{initial_stock}個に更新")
            else:
                logger.error(f"❌ {common_code}の更新に失敗")
    
    return feb10_inventory

def calculate_sales_impact_since_feb10(supabase):
    """2024年2月10日以降の売上による在庫変動を計算"""
    
    # 2024年2月10日以降の注文データを取得
    orders_result = supabase.table('order_items').select(
        'product_code, quantity, choice_code, created_at'
    ).gte('created_at', '2024-02-10T00:00:00').execute()
    
    logger.info(f"2024/2/10以降の注文アイテム: {len(orders_result.data)}件")
    
    # 簡易版: 楽天マッピングによる在庫影響を計算
    # 実際の運用では improved_mapping_system.py を使用
    
    sales_impact = {}
    mapped_count = 0
    
    for item in orders_result.data:
        # choice_codeやproduct_codeから共通コードを推定
        # 簡易版実装: 実際はマッピングシステムを使用
        estimated_common_code = estimate_common_code(item)
        
        if estimated_common_code:
            quantity = item.get('quantity', 0)
            sales_impact[estimated_common_code] = sales_impact.get(estimated_common_code, 0) + quantity
            mapped_count += 1
    
    logger.info(f"マッピング成功: {mapped_count}件")
    logger.info("売上による在庫減少:")
    for code, reduction in sales_impact.items():
        logger.info(f"- {code}: -{reduction}個")
    
    return sales_impact

def estimate_common_code(item):
    """簡易版共通コード推定（実際はマッピングシステムを使用）"""
    
    # choice_codeからの推定例
    choice_code = item.get('choice_code', '')
    if 'CM' in choice_code:
        # CMで始まるコードを抽出
        import re
        match = re.search(r'CM\d{3}', choice_code)
        if match:
            return match.group()
    
    return None

def main():
    """メイン実行関数"""
    print("=== 2024年2月10日初期在庫設定ツール ===")
    print()
    print("このツールは以下の処理を行います:")
    print("1. 現在の在庫状況を確認")
    print("2. 2024/2/10以降の売上データから在庫変動を逆算")  
    print("3. 2024/2/10時点の推定初期在庫を計算")
    print("4. 在庫テーブルの基準日を2024/2/10に設定")
    print()
    
    while True:
        choice = input("実行モードを選択してください:\n1. DRY RUN (確認のみ)\n2. 実際の更新\n3. 終了\n選択 (1-3): ")
        
        if choice == '1':
            setup_feb10_initial_inventory(dry_run=True)
            break
        elif choice == '2':
            confirm = input("⚠️ 実際に在庫を更新します。よろしいですか？ (yes/no): ")
            if confirm.lower() == 'yes':
                setup_feb10_initial_inventory(dry_run=False)
            else:
                print("キャンセルしました。")
            break
        elif choice == '3':
            print("終了します。")
            break
        else:
            print("1, 2, または3を選択してください。")

if __name__ == "__main__":
    main()