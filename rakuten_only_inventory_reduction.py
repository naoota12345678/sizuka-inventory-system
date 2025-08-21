#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
楽天データのみを対象とした在庫減少処理
platform_id=1（楽天）のデータのみ処理
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

def get_rakuten_only_sales_data():
    """
    楽天データのみを取得（platform_id=1のorder_items）
    """
    print("楽天データのみを取得中...")
    
    all_sales_data = []
    page_size = 1000
    offset = 0
    
    while True:
        try:
            # 楽天データのみ取得（orders.platform_id = 1）
            result = supabase.table('order_items').select(
                'quantity, product_code, choice_code, product_name, rakuten_item_number, orders!inner(platform_id)'
            ).eq('orders.platform_id', 1).range(offset, offset + page_size - 1).execute()
            
            if not result.data:
                break
            
            all_sales_data.extend(result.data)
            print(f"  取得済み: {len(all_sales_data)}件 (今回: {len(result.data)}件)")
            
            if len(result.data) < page_size:
                break
            
            offset += page_size
            time.sleep(0.1)
            
        except Exception as e:
            print(f"データ取得エラー (offset: {offset}): {str(e)}")
            break
    
    print(f"楽天データ取得完了: {len(all_sales_data)}件")
    return all_sales_data

def rakuten_only_inventory_reduction():
    """
    楽天データのみの在庫減少処理
    """
    print("=" * 60)
    print("楽天データ限定在庫減少処理開始")
    print("=" * 60)
    
    try:
        # Step 1: マッピングテーブル取得
        print("Step 1: マッピングデータ取得中...")
        
        # product_masterから4桁SKU → 共通コードマッピング
        pm_data = supabase.table('product_master').select('rakuten_sku, common_code, product_name').execute()
        sku_mapping = {}
        for item in pm_data.data:
            sku = item.get('rakuten_sku')
            if sku and len(str(sku)) == 4:
                sku_mapping[str(sku)] = item['common_code']
        
        # choice_code_mappingの全データを取得
        ccm_data = supabase.table('choice_code_mapping').select('choice_info, common_code, product_name').execute()
        choice_mapping = {}
        for item in ccm_data.data:
            choice_info = item.get('choice_info', {})
            if isinstance(choice_info, dict) and 'choice_code' in choice_info:
                choice_code = choice_info['choice_code']
                choice_mapping[choice_code] = item['common_code']
        
        print(f"  - 4桁SKUマッピング: {len(sku_mapping)}件")
        print(f"  - 選択肢コードマッピング: {len(choice_mapping)}件")
        
        # Step 2: 楽天データのみ取得
        print("\nStep 2: 楽天売上データ取得中...")
        rakuten_sales_data = get_rakuten_only_sales_data()
        
        # Step 3: 在庫減少量計算
        print("\nStep 3: 楽天データのみで在庫減少量計算中...")
        
        inventory_reductions = defaultdict(int)
        mapped_count = 0
        unmapped_count = 0
        unmapped_details = defaultdict(int)
        
        sku_mapped = 0
        choice_mapped = 0
        
        for item in rakuten_sales_data:
            quantity = int(item.get('quantity', 0))
            if quantity <= 0:
                continue
            
            # 楽天フィールドを使用
            rakuten_item_number = item.get('rakuten_item_number', '')
            choice_code = item.get('choice_code', '')
            product_code = item.get('product_code', '')
            
            common_code = None
            
            # マッピング優先順位
            if choice_code and choice_code in choice_mapping:
                common_code = choice_mapping[choice_code]
                mapped_count += 1
                choice_mapped += 1
            elif rakuten_item_number and str(rakuten_item_number) in sku_mapping:
                common_code = sku_mapping[str(rakuten_item_number)]
                mapped_count += 1
                sku_mapped += 1
            else:
                unmapped_count += 1
                # 未マッピング詳細記録
                if choice_code:
                    key = f"choice:{choice_code}"
                elif rakuten_item_number:
                    key = f"sku:{rakuten_item_number}"
                else:
                    key = f"product:{product_code}"
                unmapped_details[key] += quantity
            
            if common_code:
                inventory_reductions[common_code] += quantity
        
        print(f"  - 楽天売上アイテム数: {len(rakuten_sales_data)}件")
        print(f"  - マッピング成功: {mapped_count}件")
        print(f"    - 選択肢コードマッピング: {choice_mapped}件")
        print(f"    - SKUマッピング: {sku_mapped}件")
        print(f"  - マッピング失敗: {unmapped_count}件")
        print(f"  - 対象商品数: {len(inventory_reductions)}商品")
        
        # マッピング成功率計算
        success_rate = mapped_count / len(rakuten_sales_data) * 100 if rakuten_sales_data else 0
        print(f"  - 楽天データマッピング成功率: {success_rate:.1f}%")
        
        # 未マッピング詳細（上位5件のみ）
        if unmapped_details:
            print("\n楽天データ未マッピング詳細（上位5件）:")
            sorted_unmapped = sorted(unmapped_details.items(), key=lambda x: x[1], reverse=True)
            for key, qty in sorted_unmapped[:5]:
                print(f"  - {key}: {qty}個")
        
        # Step 4: 在庫減少の適用
        print("\nStep 4: 楽天データ基準で在庫減少適用中...")
        
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
                    
                    if reduction_amount > 10:  # 大幅減少のみ表示
                        print(f"  - {common_code} ({product_name[:20]}): {current_stock} -> {new_stock} (-{reduction_amount})")
                
            except Exception as e:
                logger.error(f"在庫更新エラー ({common_code}): {str(e)}")
        
        print(f"\n" + "=" * 60)
        print("楽天データ限定在庫減少処理完了")
        print("=" * 60)
        print(f"処理商品数: {success_count}件")
        print(f"総減少量: {total_reduced:,}個")
        
        # 最終在庫確認
        final_inventory = supabase.table('inventory').select('current_stock').execute()
        final_total = sum(item['current_stock'] or 0 for item in final_inventory.data)
        
        print(f"\n最終在庫数: {final_total:,}個")
        
        # 在庫減少商品詳細
        if reduction_details:
            print("\n楽天売上による在庫減少（上位10件）:")
            sorted_reductions = sorted(reduction_details, key=lambda x: x['reduction'], reverse=True)
            for item in sorted_reductions[:10]:
                print(f"  - {item['common_code']}: {item['before']} -> {item['after']} (-{item['reduction']}) {item['product_name'][:30]}")
        
        print("\n楽天データ限定在庫減少処理が完了しました！")
        
        return True, {
            'rakuten_items': len(rakuten_sales_data),
            'mapped_items': mapped_count,
            'choice_mapped': choice_mapped,
            'sku_mapped': sku_mapped,
            'unmapped_items': unmapped_count,
            'products_updated': success_count,
            'total_reduction': total_reduced,
            'final_inventory': final_total,
            'success_rate': success_rate
        }
        
    except Exception as e:
        print(f"エラー: {str(e)}")
        import traceback
        traceback.print_exc()
        return False, None

if __name__ == "__main__":
    try:
        success, results = rakuten_only_inventory_reduction()
        
        if success:
            print(f"\n楽天限定処理サマリー:")
            print(f"  - 楽天売上アイテム数: {results['rakuten_items']:,}件")
            print(f"  - マッピング成功率: {results['success_rate']:.1f}%")
            print(f"    - 選択肢コード: {results['choice_mapped']:,}件")
            print(f"    - 4桁SKU: {results['sku_mapped']:,}件")
            print(f"  - 在庫更新商品数: {results['products_updated']}商品")
            print(f"  - 総減少量: {results['total_reduction']:,}個")
            print(f"  - 最終在庫数: {results['final_inventory']:,}個")
            
            if results['success_rate'] >= 95:
                print("\n楽天データのマッピングは正常です！")
            else:
                print(f"\n楽天データでも未マッピングが{100-results['success_rate']:.1f}%あります。")
        else:
            print("\n処理でエラーが発生しました")
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n処理が中断されました")
        sys.exit(1)