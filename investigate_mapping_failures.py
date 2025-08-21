#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
マッピング失敗221件の詳細分析
失敗原因の特定と対策検討
"""

import os
import logging
from datetime import datetime
from supabase import create_client
from collections import defaultdict, Counter
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

def get_all_rakuten_data():
    """楽天データ全件取得（詳細分析用）"""
    print("楽天データ全件取得中...")
    
    all_data = []
    page_size = 1000
    offset = 0
    
    while True:
        try:
            result = supabase.table('order_items').select(
                'id, quantity, product_code, choice_code, product_name, rakuten_item_number, orders!inner(platform_id, order_date)'
            ).eq('orders.platform_id', 1).range(offset, offset + page_size - 1).execute()
            
            if not result.data:
                break
            
            all_data.extend(result.data)
            print(f"  取得済み: {len(all_data)}件")
            
            if len(result.data) < page_size:
                break
            
            offset += page_size
            time.sleep(0.1)
            
        except Exception as e:
            print(f"データ取得エラー: {str(e)}")
            break
    
    print(f"楽天データ取得完了: {len(all_data)}件")
    return all_data

def investigate_mapping_failures():
    """マッピング失敗の詳細分析"""
    print("=" * 80)
    print("楽天データマッピング失敗の詳細分析")
    print("=" * 80)
    
    try:
        # Step 1: マッピングテーブル取得
        print("Step 1: マッピングテーブル取得...")
        
        # product_master取得
        pm_data = supabase.table('product_master').select('rakuten_sku, common_code, product_name').execute()
        sku_mapping = {}
        for item in pm_data.data:
            sku = item.get('rakuten_sku')
            if sku:
                sku_mapping[str(sku)] = {
                    'common_code': item['common_code'],
                    'product_name': item.get('product_name', '')
                }
        
        # choice_code_mapping取得
        ccm_data = supabase.table('choice_code_mapping').select('choice_info, common_code, product_name').execute()
        choice_mapping = {}
        for item in ccm_data.data:
            choice_info = item.get('choice_info', {})
            if isinstance(choice_info, dict) and 'choice_code' in choice_info:
                choice_code = choice_info['choice_code']
                choice_mapping[choice_code] = {
                    'common_code': item['common_code'],
                    'product_name': item.get('product_name', '')
                }
        
        print(f"  - product_master: {len(sku_mapping)}件")
        print(f"  - choice_code_mapping: {len(choice_mapping)}件")
        
        # Step 2: 楽天データ全件取得
        print("\nStep 2: 楽天データ全件取得...")
        rakuten_data = get_all_rakuten_data()
        
        # Step 3: 失敗アイテムの詳細分析
        print("\nStep 3: マッピング失敗アイテム分析...")
        
        unmapped_items = []
        failure_categories = defaultdict(list)
        choice_code_patterns = Counter()
        sku_patterns = Counter()
        product_code_patterns = Counter()
        
        for item in rakuten_data:
            quantity = int(item.get('quantity', 0))
            if quantity <= 0:
                continue
            
            choice_code = item.get('choice_code', '') or ''
            rakuten_item_number = item.get('rakuten_item_number', '') or ''
            product_code = item.get('product_code', '') or ''
            product_name = item.get('product_name', '') or ''
            
            # マッピング確認
            mapped = False
            
            if choice_code and choice_code in choice_mapping:
                mapped = True
            elif rakuten_item_number and str(rakuten_item_number) in sku_mapping:
                mapped = True
            
            if not mapped:
                # 失敗アイテムの詳細記録
                unmapped_item = {
                    'id': item['id'],
                    'quantity': quantity,
                    'choice_code': choice_code,
                    'rakuten_item_number': rakuten_item_number,
                    'product_code': product_code,
                    'product_name': product_name,
                    'order_date': item.get('orders', {}).get('order_date', '')
                }
                unmapped_items.append(unmapped_item)
                
                # カテゴリ分類
                if choice_code and rakuten_item_number:
                    failure_categories['both_present_but_unmapped'].append(unmapped_item)
                elif choice_code and not rakuten_item_number:
                    failure_categories['choice_code_only'].append(unmapped_item)
                elif not choice_code and rakuten_item_number:
                    failure_categories['sku_only'].append(unmapped_item)
                else:
                    failure_categories['neither_present'].append(unmapped_item)
                
                # パターン収集
                if choice_code:
                    choice_code_patterns[choice_code] += quantity
                if rakuten_item_number:
                    sku_patterns[str(rakuten_item_number)] += quantity
                if product_code:
                    product_code_patterns[product_code] += quantity
        
        # Step 4: 分析結果出力
        print(f"\n" + "=" * 80)
        print("マッピング失敗分析結果")
        print("=" * 80)
        print(f"総楽天アイテム数: {len(rakuten_data):,}件")
        print(f"マッピング失敗数: {len(unmapped_items):,}件")
        print(f"失敗率: {len(unmapped_items)/len(rakuten_data)*100:.2f}%")
        
        # カテゴリ別分析
        print(f"\n【失敗カテゴリ別分析】")
        for category, items in failure_categories.items():
            total_qty = sum(item['quantity'] for item in items)
            print(f"  - {category}: {len(items)}件 (数量: {total_qty}個)")
        
        # 頻出失敗パターン
        print(f"\n【頻出未マッピング choice_code (上位10)】")
        for choice_code, qty in choice_code_patterns.most_common(10):
            print(f"  - '{choice_code}': {qty}個")
        
        print(f"\n【頻出未マッピング rakuten_item_number (上位10)】")
        for sku, qty in sku_patterns.most_common(10):
            print(f"  - '{sku}': {qty}個")
        
        print(f"\n【頻出未マッピング product_code (上位10)】")
        for product_code, qty in product_code_patterns.most_common(10):
            print(f"  - '{product_code}': {qty}個")
        
        # 具体的な失敗事例
        print(f"\n【具体的な失敗事例 (上位10件)】")
        unmapped_by_qty = sorted(unmapped_items, key=lambda x: x['quantity'], reverse=True)
        for i, item in enumerate(unmapped_by_qty[:10], 1):
            print(f"  {i}. ID:{item['id']} 数量:{item['quantity']}個")
            print(f"     choice_code: '{item['choice_code']}'")
            print(f"     rakuten_item_number: '{item['rakuten_item_number']}'") 
            print(f"     product_code: '{item['product_code']}'")
            print(f"     product_name: '{item['product_name']}'")
            print(f"     order_date: {item['order_date']}")
            print()
        
        # 特殊文字や異常値の分析
        print(f"\n【特殊文字・異常値分析】")
        
        special_chars_choice = []
        special_chars_sku = []
        
        for item in unmapped_items:
            choice_code = item['choice_code']
            sku = item['rakuten_item_number']
            
            # choice_codeの特殊文字チェック
            if choice_code:
                if not choice_code.replace(' ', '').replace('-', '').replace('_', '').isalnum():
                    special_chars_choice.append(choice_code)
                if len(choice_code) > 20:
                    special_chars_choice.append(f"長すぎる: {choice_code}")
            
            # SKUの特殊文字チェック
            if sku:
                if not str(sku).replace('-', '').replace('_', '').isalnum():
                    special_chars_sku.append(str(sku))
                if len(str(sku)) > 20:
                    special_chars_sku.append(f"長すぎる: {str(sku)}")
        
        if special_chars_choice:
            print(f"  特殊文字含むchoice_code: {len(set(special_chars_choice))}種類")
            for char in list(set(special_chars_choice))[:5]:
                print(f"    - '{char}'")
        
        if special_chars_sku:
            print(f"  特殊文字含むSKU: {len(set(special_chars_sku))}種類")
            for char in list(set(special_chars_sku))[:5]:
                print(f"    - '{char}'")
        
        # 対策提案
        print(f"\n【対策提案】")
        
        top_choice_codes = [cc for cc, _ in choice_code_patterns.most_common(5)]
        top_skus = [sku for sku, _ in sku_patterns.most_common(5)]
        
        print(f"1. 頻出未マッピングデータの手動追加が必要:")
        print(f"   - choice_code: {', '.join(top_choice_codes)}")
        print(f"   - rakuten_item_number: {', '.join(top_skus)}")
        
        print(f"2. データクリーニングが必要:")
        if special_chars_choice:
            print(f"   - choice_codeの特殊文字除去")
        if special_chars_sku:
            print(f"   - SKUの正規化")
        
        print(f"3. 楽天商品データの見直し:")
        both_present = len(failure_categories['both_present_but_unmapped'])
        if both_present > 0:
            print(f"   - choice_codeとSKU両方あるのにマッピング失敗: {both_present}件")
        
        return {
            'total_items': len(rakuten_data),
            'unmapped_items': len(unmapped_items),
            'failure_rate': len(unmapped_items)/len(rakuten_data)*100,
            'categories': {k: len(v) for k, v in failure_categories.items()},
            'top_choice_codes': choice_code_patterns.most_common(10),
            'top_skus': sku_patterns.most_common(10),
            'special_chars_choice': len(set(special_chars_choice)),
            'special_chars_sku': len(set(special_chars_sku))
        }
        
    except Exception as e:
        print(f"エラー: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    try:
        results = investigate_mapping_failures()
        
        if results:
            print(f"\n" + "=" * 80)
            print("分析完了サマリー")
            print("=" * 80)
            print(f"総アイテム数: {results['total_items']:,}件")
            print(f"マッピング失敗: {results['unmapped_items']:,}件")
            print(f"失敗率: {results['failure_rate']:.2f}%")
            print(f"主要失敗原因の特定完了")
        else:
            print("分析でエラーが発生しました")
        
    except KeyboardInterrupt:
        print("\n分析が中断されました")