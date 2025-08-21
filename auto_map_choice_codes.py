#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
選択肢コードから自動マッピングを実行
R番号、N番号等の商品コードを抽出して既存マッピングに対応付け
"""

import os
import sys
import re
from supabase import create_client
from collections import defaultdict
import time

# 環境変数設定
os.environ['SUPABASE_URL'] = 'https://equrcpeifogdrxoldkpe.supabase.co'
os.environ['SUPABASE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ'

# Supabase接続
supabase = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_KEY'])

def extract_product_codes_from_choice_code(choice_code):
    """
    選択肢コードからR番号、N番号等を抽出
    """
    product_codes = []
    
    # パターン1: R番号（R01, R11等）
    r_codes = re.findall(r'R(\d+)', choice_code)
    for code in r_codes:
        product_codes.append(f"R{code}")
    
    # パターン2: N番号（N01, N03等）
    n_codes = re.findall(r'N(\d+)', choice_code)
    for code in n_codes:
        product_codes.append(f"N{code}")
    
    # パターン3: M番号（M01等）
    m_codes = re.findall(r'M(\d+)', choice_code)
    for code in m_codes:
        product_codes.append(f"M{code}")
    
    # パターン4: C番号（C01等）
    c_codes = re.findall(r'C(\d+)', choice_code)
    for code in c_codes:
        product_codes.append(f"C{code}")
    
    return list(set(product_codes))  # 重複除去

def create_choice_code_mappings():
    """
    未マッピング選択肢コードの自動マッピングを実行
    """
    print("=" * 60)
    print("選択肢コード自動マッピング開始")
    print("=" * 60)
    
    try:
        # Step 1: 既存の選択肢マッピングを取得
        print("Step 1: 既存マッピング取得中...")
        
        ccm_data = supabase.table('choice_code_mapping').select('choice_info, common_code, product_name').execute()
        existing_choice_codes = {}
        existing_product_codes = {}
        
        for item in ccm_data.data:
            choice_info = item.get('choice_info', {})
            if isinstance(choice_info, dict) and 'choice_code' in choice_info:
                choice_code = choice_info['choice_code']
                existing_choice_codes[choice_code] = item['common_code']
                
                # 既存のR番号等もマッピング
                product_codes = extract_product_codes_from_choice_code(choice_code)
                for prod_code in product_codes:
                    existing_product_codes[prod_code] = item['common_code']
        
        print(f"  - 既存選択肢マッピング: {len(existing_choice_codes)}件")
        print(f"  - 抽出済み商品コード: {len(existing_product_codes)}件")
        
        # Step 2: 楽天未マッピング選択肢コード取得
        print("\nStep 2: 未マッピング選択肢コード取得中...")
        
        # 楽天データから選択肢コード取得
        choice_result = supabase.table('order_items').select(
            'choice_code, quantity, orders!inner(platform_id)'
        ).eq('orders.platform_id', 1).execute()
        
        unmapped_choice_codes = []
        choice_quantities = defaultdict(int)
        
        for item in choice_result.data:
            choice_code = item.get('choice_code', '') or ''
            quantity = item.get('quantity', 0)
            
            if choice_code.strip() and choice_code not in existing_choice_codes:
                choice_quantities[choice_code] += quantity
        
        # 数量順でソート
        for choice_code, total_qty in sorted(choice_quantities.items(), key=lambda x: x[1], reverse=True):
            unmapped_choice_codes.append({
                'choice_code': choice_code,
                'total_quantity': total_qty
            })
        
        print(f"  - 未マッピング選択肢コード: {len(unmapped_choice_codes)}件")
        
        # Step 3: 自動マッピング実行
        print("\nStep 3: 自動マッピング実行中...")
        
        auto_mapped = 0
        non_product_choices = 0
        new_mappings = []
        
        for item in unmapped_choice_codes:
            choice_code = item['choice_code']
            total_quantity = item['total_quantity']
            
            # 商品コードを抽出
            product_codes = extract_product_codes_from_choice_code(choice_code)
            
            if product_codes:
                # 最初に見つかった商品コードを使用
                primary_product_code = product_codes[0]
                
                if primary_product_code in existing_product_codes:
                    # 既存商品コードにマッピング
                    common_code = existing_product_codes[primary_product_code]
                    
                    new_mapping = {
                        'choice_info': {
                            'choice_code': choice_code,
                            'choice_name': f'Auto: {primary_product_code}',
                            'choice_value': f'自動マッピング: {primary_product_code}商品',
                            'category': 'auto_mapped',
                            'extracted_codes': product_codes
                        },
                        'common_code': common_code,
                        'product_name': f'自動マッピング商品 ({primary_product_code})',
                        'rakuten_sku': f'AUTO_{primary_product_code}_{auto_mapped + 1:04d}'
                    }
                    
                    new_mappings.append(new_mapping)
                    auto_mapped += 1
                    
                    if auto_mapped <= 10:  # 上位10件のみ表示
                        print(f"  - {choice_code[:50]}... -> {common_code} ({primary_product_code})")
                else:
                    # 新商品コードの場合は新しい共通コードを割り当て
                    new_common_code = f"CM{600 + auto_mapped:03d}"
                    
                    new_mapping = {
                        'choice_info': {
                            'choice_code': choice_code,
                            'choice_name': f'New: {primary_product_code}',
                            'choice_value': f'新商品: {primary_product_code}',
                            'category': 'auto_new_product',
                            'extracted_codes': product_codes
                        },
                        'common_code': new_common_code,
                        'product_name': f'新商品 ({primary_product_code})',
                        'rakuten_sku': f'NEW_{primary_product_code}_{auto_mapped + 1:04d}'
                    }
                    
                    new_mappings.append(new_mapping)
                    existing_product_codes[primary_product_code] = new_common_code
                    auto_mapped += 1
            else:
                # 商品コードが見つからない場合（連絡事項等）
                non_product_choices += 1
                
                if non_product_choices <= 50:  # 最大50件の非商品選択肢
                    new_common_code = f"CM{800 + non_product_choices:03d}"
                    
                    new_mapping = {
                        'choice_info': {
                            'choice_code': choice_code,
                            'choice_name': f'Non-Product {non_product_choices}',
                            'choice_value': '非商品選択肢',
                            'category': 'non_product',
                            'extracted_codes': []
                        },
                        'common_code': new_common_code,
                        'product_name': '非商品選択肢',
                        'rakuten_sku': f'NONPROD_{non_product_choices:04d}'
                    }
                    
                    new_mappings.append(new_mapping)
        
        print(f"  - 自動マッピング作成数: {len(new_mappings)}件")
        print(f"    - 既存商品コード対応: {auto_mapped - len([m for m in new_mappings if 'NEW_' in m['rakuten_sku']])}件")
        print(f"    - 新商品コード: {len([m for m in new_mappings if 'NEW_' in m['rakuten_sku']])}件")
        print(f"    - 非商品選択肢: {min(non_product_choices, 50)}件")
        
        # Step 4: choice_code_mappingテーブルに一括挿入
        print(f"\nStep 4: choice_code_mappingテーブル更新中...")
        
        if new_mappings:
            # 50件ずつバッチ挿入
            batch_size = 50
            inserted_count = 0
            
            for i in range(0, len(new_mappings), batch_size):
                batch = new_mappings[i:i + batch_size]
                
                try:
                    result = supabase.table('choice_code_mapping').insert(batch).execute()
                    inserted_count += len(batch)
                    print(f"  - 挿入完了: {inserted_count}/{len(new_mappings)}件")
                    time.sleep(0.5)  # API制限対策
                    
                except Exception as e:
                    print(f"  - バッチ挿入エラー: {str(e)}")
                    break
            
            print(f"choice_code_mapping更新完了: {inserted_count}件追加")
        
        print(f"\n" + "=" * 60)
        print("選択肢コード自動マッピング完了")
        print("=" * 60)
        
        return True, {
            'unmapped_count': len(unmapped_choice_codes),
            'auto_mapped': auto_mapped,
            'non_product': min(non_product_choices, 50),
            'inserted': len(new_mappings)
        }
        
    except Exception as e:
        print(f"エラー: {str(e)}")
        import traceback
        traceback.print_exc()
        return False, None

if __name__ == "__main__":
    try:
        success, results = create_choice_code_mappings()
        
        if success:
            print(f"\n自動マッピングサマリー:")
            print(f"  - 未マッピング総数: {results['unmapped_count']}件")
            print(f"  - 自動マッピング済み: {results['auto_mapped']}件")
            print(f"  - 非商品選択肢: {results['non_product']}件")
            print(f"  - データベース挿入: {results['inserted']}件")
            
            print(f"\n次の手順:")
            print(f"1. 楽天データ在庫減少処理を再実行")
            print(f"2. マッピング成功率を確認")
            print(f"3. 必要に応じて追加調整")
        else:
            print("\n処理でエラーが発生しました")
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n処理が中断されました")
        sys.exit(1)