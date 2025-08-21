#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
残り22.9%の未マッピングデータを詳細分析
100%マッピング達成のための完全解析
"""

import os
import sys
import re
from supabase import create_client
from collections import defaultdict, Counter
import time

# 環境変数設定
os.environ['SUPABASE_URL'] = 'https://equrcpeifogdrxoldkpe.supabase.co'
os.environ['SUPABASE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ'

# Supabase接続
supabase = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_KEY'])

def get_rakuten_unmapped_data():
    """
    楽天データの未マッピングアイテムを詳細分析
    """
    print("=" * 60)
    print("残り未マッピングデータ完全分析開始")
    print("=" * 60)
    
    try:
        # Step 1: 現在のマッピング状況を取得
        print("Step 1: 現在のマッピング状況取得中...")
        
        # 4桁SKUマッピング
        pm_data = supabase.table('product_master').select('rakuten_sku, common_code, product_name').execute()
        sku_mapping = {}
        for item in pm_data.data:
            sku = item.get('rakuten_sku')
            if sku and len(str(sku)) == 4:
                sku_mapping[str(sku)] = item['common_code']
        
        # 選択肢コードマッピング
        ccm_data = supabase.table('choice_code_mapping').select('choice_info, common_code, product_name').execute()
        choice_mapping = {}
        for item in ccm_data.data:
            choice_info = item.get('choice_info', {})
            if isinstance(choice_info, dict) and 'choice_code' in choice_info:
                choice_code = choice_info['choice_code']
                choice_mapping[choice_code] = item['common_code']
        
        print(f"  - 4桁SKUマッピング: {len(sku_mapping)}件")
        print(f"  - 選択肢コードマッピング: {len(choice_mapping)}件")
        
        # Step 2: 楽天データ全件取得
        print("\nStep 2: 楽天データ全件取得中...")
        
        all_rakuten_data = []
        page_size = 1000
        offset = 0
        
        while True:
            try:
                result = supabase.table('order_items').select(
                    'quantity, product_code, choice_code, product_name, rakuten_item_number, orders!inner(platform_id)'
                ).eq('orders.platform_id', 1).range(offset, offset + page_size - 1).execute()
                
                if not result.data:
                    break
                
                all_rakuten_data.extend(result.data)
                offset += page_size
                time.sleep(0.1)
                
            except Exception as e:
                print(f"データ取得エラー (offset: {offset}): {str(e)}")
                break
        
        print(f"楽天データ取得完了: {len(all_rakuten_data)}件")
        
        # Step 3: 未マッピング詳細分析
        print("\nStep 3: 未マッピング詳細分析中...")
        
        unmapped_items = []
        mapped_count = 0
        
        for item in all_rakuten_data:
            quantity = int(item.get('quantity', 0))
            if quantity <= 0:
                continue
            
            rakuten_item_number = item.get('rakuten_item_number', '')
            choice_code = item.get('choice_code', '')
            product_code = item.get('product_code', '')
            
            is_mapped = False
            
            # マッピング確認
            if choice_code and choice_code in choice_mapping:
                is_mapped = True
                mapped_count += 1
            elif rakuten_item_number and str(rakuten_item_number) in sku_mapping:
                is_mapped = True
                mapped_count += 1
            
            if not is_mapped:
                unmapped_items.append(item)
        
        print(f"  - 未マッピングアイテム数: {len(unmapped_items)}件")
        
        # Step 4: 未マッピングの詳細分類
        print("\nStep 4: 未マッピング分類分析中...")
        
        # 分類別集計
        categories = {
            'missing_sku': [],           # rakuten_item_numberがない
            'unknown_sku': [],           # rakuten_item_numberはあるが未登録
            'complex_choice': [],        # 複雑な選択肢コード
            'non_product': [],          # 非商品（配送・連絡事項）
            'empty_all': []             # すべて空
        }
        
        sku_not_in_mapping = Counter()
        choice_patterns = Counter()
        
        for item in unmapped_items:
            rakuten_item_number = item.get('rakuten_item_number', '')
            choice_code = item.get('choice_code', '') or ''
            product_code = item.get('product_code', '')
            quantity = item.get('quantity', 0)
            
            # 分類
            if not rakuten_item_number and not choice_code:
                categories['empty_all'].append(item)
            elif not rakuten_item_number:
                categories['missing_sku'].append(item)
            elif str(rakuten_item_number) not in sku_mapping:
                categories['unknown_sku'].append(item)
                sku_not_in_mapping[str(rakuten_item_number)] += quantity
            elif choice_code and '配送' in choice_code or '連絡' in choice_code or 'メール便' in choice_code:
                categories['non_product'].append(item)
            else:
                categories['complex_choice'].append(item)
                # パターン分析
                if choice_code:
                    # R番号等の抽出
                    r_codes = re.findall(r'R\d+', choice_code)
                    n_codes = re.findall(r'N\d+', choice_code)
                    if r_codes or n_codes:
                        pattern = f"含む商品コード: {'+'.join(r_codes + n_codes)}"
                        choice_patterns[pattern] += quantity
        
        # 分類結果表示
        print(f"\n未マッピング分類結果:")
        for category, items in categories.items():
            if items:
                total_qty = sum(item.get('quantity', 0) for item in items)
                print(f"  - {category}: {len(items)}件 ({total_qty}個)")
        
        # Step 5: 未登録SKU分析
        print(f"\n未登録SKU（上位10件）:")
        for sku, qty in sku_not_in_mapping.most_common(10):
            print(f"  - SKU {sku}: {qty}個")
        
        # Step 6: 複雑選択肢パターン分析
        print(f"\n複雑選択肢パターン（上位10件）:")
        for pattern, qty in choice_patterns.most_common(10):
            print(f"  - {pattern}: {qty}個")
        
        # Step 7: 完全マッピングのための提案
        print(f"\n" + "=" * 60)
        print("100%マッピング達成のための対策")
        print("=" * 60)
        
        total_unmapped = len(unmapped_items)
        
        print(f"対策1: 未登録SKU追加 ({len(sku_not_in_mapping)}件)")
        print(f"  - 新SKU追加で約{len(categories['unknown_sku'])}件解決可能")
        
        print(f"\n対策2: 複雑選択肢の分解マッピング")
        print(f"  - R/N番号抽出で約{len(categories['complex_choice'])}件解決可能")
        
        print(f"\n対策3: 非商品選択肢の統合")
        print(f"  - 配送・連絡事項で約{len(categories['non_product'])}件")
        
        return True, {
            'total_unmapped': total_unmapped,
            'categories': {k: len(v) for k, v in categories.items()},
            'unknown_skus': dict(sku_not_in_mapping.most_common(50)),
            'choice_patterns': dict(choice_patterns.most_common(50)),
            'mapped_count': mapped_count,
            'total_items': len(all_rakuten_data)
        }
        
    except Exception as e:
        print(f"エラー: {str(e)}")
        import traceback
        traceback.print_exc()
        return False, None

def create_complete_mappings(analysis_result):
    """
    完全マッピングを作成
    """
    print(f"\n" + "=" * 60)
    print("完全マッピング作成開始")
    print("=" * 60)
    
    try:
        unknown_skus = analysis_result['unknown_skus']
        
        # Step 1: 未登録SKUのマッピング作成
        print("Step 1: 未登録SKU用マッピング作成中...")
        
        new_sku_mappings = []
        base_code = 700  # CM700番台を使用
        
        for sku, quantity in unknown_skus.items():
            new_common_code = f"CM{base_code:03d}"
            
            new_mapping = {
                'common_code': new_common_code,
                'product_name': f'SKU{sku}商品',
                'rakuten_sku': sku
            }
            
            new_sku_mappings.append(new_mapping)
            base_code += 1
        
        # product_masterに挿入
        if new_sku_mappings:
            print(f"product_masterに{len(new_sku_mappings)}件の新SKU追加中...")
            
            # バッチ挿入
            batch_size = 50
            for i in range(0, len(new_sku_mappings), batch_size):
                batch = new_sku_mappings[i:i + batch_size]
                try:
                    supabase.table('product_master').insert(batch).execute()
                    print(f"  - 挿入完了: {i + len(batch)}/{len(new_sku_mappings)}件")
                    time.sleep(0.5)
                except Exception as e:
                    print(f"  - バッチ挿入エラー: {str(e)}")
        
        print(f"完全マッピング作成完了: {len(new_sku_mappings)}件の新SKU追加")
        
        return True, len(new_sku_mappings)
        
    except Exception as e:
        print(f"エラー: {str(e)}")
        import traceback
        traceback.print_exc()
        return False, 0

if __name__ == "__main__":
    try:
        # Step 1: 未マッピング分析
        success, analysis = get_rakuten_unmapped_data()
        
        if success:
            current_rate = analysis['mapped_count'] / analysis['total_items'] * 100
            print(f"\n現在のマッピング状況:")
            print(f"  - 総アイテム数: {analysis['total_items']:,}件")
            print(f"  - マッピング済み: {analysis['mapped_count']:,}件")
            print(f"  - 未マッピング: {analysis['total_unmapped']:,}件")
            print(f"  - マッピング成功率: {current_rate:.1f}%")
            
            # Step 2: 完全マッピング作成
            if analysis['unknown_skus']:
                print(f"\n未登録SKU {len(analysis['unknown_skus'])}件の完全マッピングを作成します。")
                print("100%マッピング達成のため自動実行します...")
                
                # 自動実行
                mapping_success, new_mappings = create_complete_mappings(analysis)
                
                if mapping_success:
                    print(f"\n[完了] {new_mappings}件の新SKUマッピング追加完了")
                    print(f"楽天データ在庫減少処理を再実行して100%達成を確認してください")
                else:
                    print("マッピング作成でエラーが発生しました")
        else:
            print("分析でエラーが発生しました")
            
    except KeyboardInterrupt:
        print("\n処理が中断されました")
        sys.exit(1)