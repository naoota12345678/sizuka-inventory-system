#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
完全在庫減少適用スクリプト
ページネーションを使用して全16,676件の売上データを処理
"""

import os
import sys
import logging
from datetime import datetime, timezone
from supabase import create_client
from collections import defaultdict
import time

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

def get_all_sales_data_paginated():
    """
    ページネーションを使用して全売上データを取得
    """
    print("全売上データをページネーションで取得中...")
    
    all_sales_data = []
    page_size = 1000
    offset = 0
    
    while True:
        try:
            # ページネーションでデータ取得
            result = supabase.table('order_items').select(
                'quantity, product_code, choice_code, product_name'
            ).range(offset, offset + page_size - 1).execute()
            
            if not result.data:
                break
            
            all_sales_data.extend(result.data)
            print(f"  取得済み: {len(all_sales_data)}件 (今回: {len(result.data)}件)")
            
            # 最大件数まで取得したらbreak
            if len(result.data) < page_size:
                break
            
            offset += page_size
            
            # APIレート制限対策
            time.sleep(0.1)
            
        except Exception as e:
            print(f"データ取得エラー (offset: {offset}): {str(e)}")
            break
    
    print(f"取得完了: {len(all_sales_data)}件")
    return all_sales_data

def complete_inventory_reduction():
    """
    完全在庫減少処理
    全16,676件の売上データを処理
    """
    print("=" * 60)
    print("完全在庫減少処理開始")
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
        
        # Step 2: 全売上データの取得
        print("\nStep 2: 売上データ取得中...")
        all_sales_data = get_all_sales_data_paginated()
        
        # Step 3: 在庫減少量を計算
        print("\nStep 3: 在庫減少量計算中...")
        
        inventory_reductions = defaultdict(int)
        mapped_count = 0
        unmapped_count = 0
        unmapped_details = defaultdict(int)
        
        for item in all_sales_data:
            quantity = int(item.get('quantity', 0))
            if quantity <= 0:
                continue
            
            product_code = item.get('product_code', '')
            choice_code = item.get('choice_code', '')
            
            common_code = None
            
            # 高速マッピング
            if choice_code and choice_code in choice_mapping:
                common_code = choice_mapping[choice_code]
                mapped_count += 1
            elif product_code and product_code in sku_mapping:
                common_code = sku_mapping[product_code]
                mapped_count += 1
            else:
                unmapped_count += 1
                # 未マッピング詳細記録
                key = f"choice:{choice_code}" if choice_code else f"product:{product_code}"
                unmapped_details[key] += quantity
            
            if common_code:
                inventory_reductions[common_code] += quantity
        
        print(f"  - 総売上アイテム数: {len(all_sales_data)}件")
        print(f"  - マッピング成功: {mapped_count}件")
        print(f"  - マッピング失敗: {unmapped_count}件")
        print(f"  - 対象商品数: {len(inventory_reductions)}商品")
        
        # 未マッピング詳細（上位10件）
        if unmapped_details:
            print("\n未マッピング詳細（上位10件）:")
            sorted_unmapped = sorted(unmapped_details.items(), key=lambda x: x[1], reverse=True)
            for key, qty in sorted_unmapped[:10]:
                print(f"  - {key}: {qty}個")
        
        # Step 4: 在庫減少の適用
        print("\nStep 4: 在庫減少適用中...")
        
        success_count = 0
        total_reduced = 0
        reduction_details = []
        
        for common_code, reduction_amount in inventory_reductions.items():
            try:
                # 現在の在庫を取得
                existing = supabase.table('inventory').select('current_stock, product_name').eq('common_code', common_code).execute()
                
                if existing.data:
                    current_stock = existing.data[0]['current_stock'] or 0
                    product_name = existing.data[0].get('product_name', '')
                    new_stock = max(0, current_stock - reduction_amount)
                    
                    # 在庫更新
                    supabase.table('inventory').update({
                        'current_stock': new_stock,
                        'last_updated': datetime.now(timezone.utc).isoformat()
                    }).eq('common_code', common_code).execute()
                    
                    success_count += 1
                    total_reduced += reduction_amount
                    
                    reduction_details.append({
                        'common_code': common_code,
                        'product_name': product_name,
                        'before': current_stock,
                        'after': new_stock,
                        'reduction': reduction_amount
                    })
                    
                    print(f"  - {common_code} ({product_name[:20]}): {current_stock} -> {new_stock} (-{reduction_amount})")
                
            except Exception as e:
                logger.error(f"在庫更新エラー ({common_code}): {str(e)}")
        
        print(f"\n" + "=" * 60)
        print("完全在庫減少処理完了")
        print("=" * 60)
        print(f"処理商品数: {success_count}件")
        print(f"総減少量: {total_reduced:,}個")
        
        # 最終在庫確認
        final_inventory = supabase.table('inventory').select('current_stock').execute()
        final_total = sum(item['current_stock'] or 0 for item in final_inventory.data)
        
        print(f"\n最終在庫数: {final_total:,}個")
        
        # 大幅減少した商品の詳細表示
        print("\n大幅減少商品（上位10件）:")
        sorted_reductions = sorted(reduction_details, key=lambda x: x['reduction'], reverse=True)
        for item in sorted_reductions[:10]:
            print(f"  - {item['common_code']}: {item['before']} -> {item['after']} (-{item['reduction']}) {item['product_name'][:30]}")
        
        print("\n完全在庫減少処理が完了しました！")
        
        return True, {
            'total_items': len(all_sales_data),
            'mapped_items': mapped_count,
            'unmapped_items': unmapped_count,
            'products_updated': success_count,
            'total_reduction': total_reduced,
            'final_inventory': final_total
        }
        
    except Exception as e:
        print(f"エラー: {str(e)}")
        import traceback
        traceback.print_exc()
        return False, None

if __name__ == "__main__":
    try:
        success, results = complete_inventory_reduction()
        
        if success:
            print(f"\n処理サマリー:")
            print(f"  - 総売上アイテム数: {results['total_items']:,}件")
            print(f"  - マッピング成功率: {results['mapped_items'] / results['total_items'] * 100:.1f}%")
            print(f"  - 在庫更新商品数: {results['products_updated']}商品")
            print(f"  - 総減少量: {results['total_reduction']:,}個")
            print(f"  - 最終在庫数: {results['final_inventory']:,}個")
            
            print("\nダッシュボードで変更を確認してください。")
        else:
            print("\n処理でエラーが発生しました")
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n処理が中断されました")
        sys.exit(1)