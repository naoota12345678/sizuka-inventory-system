#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
楽天データの未マッピング選択肢コードを全て抽出
Google Sheets追加用のCSVファイルを作成
"""

import os
import sys
import pandas as pd
from supabase import create_client
from collections import Counter, defaultdict
import time

# 環境変数設定
os.environ['SUPABASE_URL'] = 'https://equrcpeifogdrxoldkpe.supabase.co'
os.environ['SUPABASE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ'

# Supabase接続
supabase = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_KEY'])

def get_all_rakuten_choice_codes():
    """
    楽天データの全選択肢コードを取得
    """
    print("楽天データの選択肢コードを全件取得中...")
    
    all_choice_codes = []
    page_size = 1000
    offset = 0
    
    while True:
        try:
            # 楽天データの選択肢コードのみ取得
            result = supabase.table('order_items').select(
                'choice_code, quantity, orders!inner(platform_id)'
            ).eq('orders.platform_id', 1).range(offset, offset + page_size - 1).execute()
            
            if not result.data:
                break
            
            for item in result.data:
                choice_code = item.get('choice_code', '') or ''
                quantity = item.get('quantity', 0)
                
                if choice_code.strip():
                    all_choice_codes.append({
                        'choice_code': choice_code.strip(),
                        'quantity': quantity
                    })
            
            print(f"  取得済み: {len(all_choice_codes)}件の選択肢コード")
            
            if len(result.data) < page_size:
                break
            
            offset += page_size
            time.sleep(0.1)
            
        except Exception as e:
            print(f"データ取得エラー (offset: {offset}): {str(e)}")
            break
    
    print(f"選択肢コード取得完了: {len(all_choice_codes)}件")
    return all_choice_codes

def extract_unmapped_choice_codes():
    """
    未マッピング選択肢コードを抽出してCSV出力
    """
    print("=" * 60)
    print("楽天未マッピング選択肢コード抽出開始")
    print("=" * 60)
    
    try:
        # Step 1: 既存のマッピング済み選択肢コード取得
        print("Step 1: 既存マッピング済み選択肢コード取得中...")
        
        ccm_data = supabase.table('choice_code_mapping').select('choice_info, common_code, product_name').execute()
        existing_choice_codes = set()
        
        for item in ccm_data.data:
            choice_info = item.get('choice_info', {})
            if isinstance(choice_info, dict) and 'choice_code' in choice_info:
                choice_code = choice_info['choice_code']
                existing_choice_codes.add(choice_code)
        
        print(f"  - 既存マッピング済み選択肢コード: {len(existing_choice_codes)}件")
        
        # Step 2: 楽天データの全選択肢コード取得
        print("\nStep 2: 楽天データの選択肢コード取得中...")
        all_choice_codes = get_all_rakuten_choice_codes()
        
        # Step 3: 選択肢コード別に集計
        print("\nStep 3: 選択肢コード集計中...")
        choice_code_stats = defaultdict(int)
        
        for item in all_choice_codes:
            choice_code = item['choice_code']
            quantity = item['quantity']
            choice_code_stats[choice_code] += quantity
        
        print(f"  - ユニーク選択肢コード数: {len(choice_code_stats)}件")
        
        # Step 4: 未マッピング選択肢コードを特定
        print("\nStep 4: 未マッピング選択肢コード特定中...")
        
        unmapped_choice_codes = []
        for choice_code, total_quantity in choice_code_stats.items():
            if choice_code not in existing_choice_codes:
                unmapped_choice_codes.append({
                    'choice_code': choice_code,
                    'total_quantity': total_quantity,
                    'frequency': len([c for c in all_choice_codes if c['choice_code'] == choice_code])
                })
        
        # 数量の多い順にソート
        unmapped_choice_codes.sort(key=lambda x: x['total_quantity'], reverse=True)
        
        print(f"  - 未マッピング選択肢コード: {len(unmapped_choice_codes)}件")
        print(f"  - 未マッピング総数量: {sum(item['total_quantity'] for item in unmapped_choice_codes):,}個")
        
        # Step 5: Google Sheets追加用CSVファイル作成
        print("\nStep 5: CSV出力中...")
        
        # Google Sheets形式に変換
        google_sheets_data = []
        
        for i, item in enumerate(unmapped_choice_codes, 1):
            choice_code = item['choice_code']
            total_quantity = item['total_quantity']
            
            # 共通コード自動生成（CM500番台）
            new_common_code = f"CM{500 + i:03d}"
            
            # 商品名を選択肢コードから推測
            product_name = extract_product_name_from_choice_code(choice_code)
            
            google_sheets_data.append({
                'choice_code': choice_code,
                'choice_name': f"選択肢_{i}",
                'choice_value': product_name,
                'category': 'auto_extracted',
                'common_code': new_common_code,
                'product_name': product_name,
                'rakuten_sku': f"CHOICE_{new_common_code}",
                'total_quantity': total_quantity,
                'frequency': item['frequency']
            })
        
        # CSVファイル出力
        df = pd.DataFrame(google_sheets_data)
        csv_filename = 'unmapped_choice_codes_for_google_sheets.csv'
        df.to_csv(csv_filename, index=False, encoding='utf-8-sig')
        
        print(f"CSV出力完了: {csv_filename}")
        print(f"  - 出力レコード数: {len(google_sheets_data)}件")
        
        # Step 6: サマリー表示
        print(f"\n" + "=" * 60)
        print("未マッピング選択肢コード抽出完了")
        print("=" * 60)
        
        print(f"総選択肢コード数: {len(choice_code_stats)}件")
        print(f"既存マッピング済み: {len(existing_choice_codes)}件")
        print(f"未マッピング: {len(unmapped_choice_codes)}件")
        print(f"マッピング率: {len(existing_choice_codes) / len(choice_code_stats) * 100:.1f}%")
        
        print(f"\n未マッピング上位10件:")
        for i, item in enumerate(unmapped_choice_codes[:10], 1):
            choice_preview = item['choice_code'][:50] + '...' if len(item['choice_code']) > 50 else item['choice_code']
            print(f"{i:2d}. {choice_preview} ({item['total_quantity']}個)")
        
        print(f"\n次の手順:")
        print(f"1. {csv_filename} をGoogle Sheetsにインポート")
        print(f"2. 商品名とcommon_codeを適切に調整")
        print(f"3. choice_code_mappingテーブルを同期更新")
        print(f"4. 楽天データ在庫減少処理を再実行")
        
        return True, {
            'total_choice_codes': len(choice_code_stats),
            'existing_mapped': len(existing_choice_codes),
            'unmapped_count': len(unmapped_choice_codes),
            'csv_filename': csv_filename
        }
        
    except Exception as e:
        print(f"エラー: {str(e)}")
        import traceback
        traceback.print_exc()
        return False, None

def extract_product_name_from_choice_code(choice_code):
    """
    選択肢コードから商品名を推測
    """
    try:
        # R番号パターンを探す（R01, R11等）
        import re
        
        # R番号+商品名のパターンを抽出
        patterns = [
            r'R\d+\s+([^選択]+)',  # "R11 鶏ササミスライス30g"
            r':R\d+\.?([^選択\n]+)',  # ":R06.スティックサーモン 10g"
            r'R\d+\.([^選択\n]+)',   # "R06.スティックサーモン 10g"
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, choice_code)
            if matches:
                # 最初にマッチした商品名を使用
                product_name = matches[0].strip()
                if len(product_name) > 3:  # 短すぎる名前は除外
                    return product_name
        
        # パターンマッチしない場合は最初の50文字を使用
        return choice_code[:50].strip()
        
    except:
        return choice_code[:30].strip()

if __name__ == "__main__":
    try:
        success, results = extract_unmapped_choice_codes()
        
        if success:
            print(f"\n抽出サマリー:")
            print(f"  - 総選択肢コード数: {results['total_choice_codes']}件")
            print(f"  - 既存マッピング済み: {results['existing_mapped']}件") 
            print(f"  - 未マッピング: {results['unmapped_count']}件")
            print(f"  - 出力ファイル: {results['csv_filename']}")
            
            mapping_rate = results['existing_mapped'] / results['total_choice_codes'] * 100
            print(f"  - 現在のマッピング率: {mapping_rate:.1f}%")
            print(f"  - 100%達成に必要: {results['unmapped_count']}件の追加マッピング")
            
        else:
            print("\n処理でエラーが発生しました")
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n処理が中断されました")
        sys.exit(1)