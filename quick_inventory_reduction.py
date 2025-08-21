#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
高速在庫減少適用スクリプト
効率的なバッチ処理で売上による在庫減少を適用
"""

import os
import sys
import logging
from datetime import datetime, timezone
from supabase import create_client
from collections import defaultdict

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 環境変数設定
os.environ['SUPABASE_URL'] = 'https://equrcpeifogdrxoldkpe.supabase.co'
os.environ['SUPABASE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ'

# Supabase接続
supabase = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_KEY'])

def quick_inventory_reduction():
    """
    高速在庫減少処理
    主要な売上データのみを対象に効率的に処理
    """
    print("=" * 60)
    print("高速在庫減少処理開始")
    print("=" * 60)
    
    try:
        # Step 1: 既存マッピングテーブルからの高速マッピング
        print("Step 1: 既存マッピングデータ取得中...")
        
        # product_masterの全データを取得
        pm_data = supabase.table('product_master').select('rakuten_sku, common_code, product_name').execute()
        sku_mapping = {item['rakuten_sku']: item['common_code'] for item in pm_data.data if item['rakuten_sku']}
        
        # choice_code_mappingの全データを取得
        ccm_data = supabase.table('choice_code_mapping').select('choice_info, common_code, product_name').execute()
        choice_mapping = {}
        for item in ccm_data.data:
            choice_info = item.get('choice_info', {})
            if isinstance(choice_info, dict) and 'choice_code' in choice_info:
                choice_code = choice_info['choice_code']
                choice_mapping[choice_code] = item['common_code']
        
        print(f"  - 楽天SKUマッピング: {len(sku_mapping)}件")
        print(f"  - 選択肢コードマッピング: {len(choice_mapping)}件")
        
        # Step 2: 売上データの高速処理
        print("\nStep 2: 売上データ処理中...")
        
        # 売上データを一括取得
        sales_result = supabase.table('order_items').select(
            'quantity, product_code, choice_code'
        ).execute()
        
        print(f"  - 売上アイテム数: {len(sales_result.data)}件")
        
        # Step 3: 在庫減少量を高速計算
        print("\nStep 3: 在庫減少量計算中...")
        
        inventory_reductions = defaultdict(int)
        mapped_count = 0
        unmapped_count = 0
        
        for item in sales_result.data:
            quantity = int(item.get('quantity', 0))
            if quantity <= 0:
                continue
            
            product_code = item.get('product_code', '')
            choice_code = item.get('choice_code', '')
            
            common_code = None
            
            # 高速マッピング（事前読み込みデータを使用）
            if choice_code and choice_code in choice_mapping:
                common_code = choice_mapping[choice_code]
            elif product_code and product_code in sku_mapping:
                common_code = sku_mapping[product_code]
            
            if common_code:
                inventory_reductions[common_code] += quantity
                mapped_count += 1
            else:
                unmapped_count += 1
        
        print(f"  - マッピング成功: {mapped_count}件")
        print(f"  - マッピング失敗: {unmapped_count}件")
        print(f"  - 対象商品数: {len(inventory_reductions)}商品")
        
        # Step 4: 在庫減少の適用
        print("\nStep 4: 在庫減少適用中...")
        
        success_count = 0
        total_reduced = 0
        
        for common_code, reduction_amount in inventory_reductions.items():
            try:
                # 現在の在庫を取得
                existing = supabase.table('inventory').select('current_stock').eq('common_code', common_code).execute()
                
                if existing.data:
                    current_stock = existing.data[0]['current_stock'] or 0
                    new_stock = max(0, current_stock - reduction_amount)
                    
                    # 在庫更新
                    supabase.table('inventory').update({
                        'current_stock': new_stock,
                        'last_updated': datetime.now(timezone.utc).isoformat()
                    }).eq('common_code', common_code).execute()
                    
                    success_count += 1
                    total_reduced += reduction_amount
                    
                    print(f"  - {common_code}: {current_stock} -> {new_stock} (-{reduction_amount})")
                
            except Exception as e:
                logger.error(f"在庫更新エラー ({common_code}): {str(e)}")
        
        print(f"\n" + "=" * 60)
        print("高速在庫減少処理完了")
        print("=" * 60)
        print(f"処理商品数: {success_count}件")
        print(f"総減少量: {total_reduced:,}個")
        
        # 最終在庫確認
        final_inventory = supabase.table('inventory').select('current_stock').execute()
        final_total = sum(item['current_stock'] or 0 for item in final_inventory.data)
        
        print(f"\n最終在庫数: {final_total:,}個")
        print("在庫減少処理が完了しました！")
        
        return True
        
    except Exception as e:
        print(f"エラー: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    try:
        success = quick_inventory_reduction()
        
        if success:
            print("\n高速在庫減少処理が正常に完了しました！")
            print("ダッシュボードで変更を確認してください。")
        else:
            print("\n処理でエラーが発生しました")
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n処理が中断されました")
        sys.exit(1)