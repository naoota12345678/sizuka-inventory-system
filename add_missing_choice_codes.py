#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
P01/S01/S02を選択肢コード対応表に追加
適切な基本コード（CM形式）にマッピング
"""

import os
from supabase import create_client
from datetime import datetime, timezone

# 環境変数を設定
os.environ['SUPABASE_URL'] = 'https://equrcpeifogdrxoldkpe.supabase.co'
os.environ['SUPABASE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ'

SUPABASE_URL = "https://equrcpeifogdrxoldkpe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ"

def check_choice_code_structure():
    """選択肢コード対応表の構造を確認"""
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    print("=== 選択肢コード対応表の構造確認 ===")
    
    # 既存のレコードを数件取得してJSONB構造を確認
    result = supabase.table('choice_code_mapping').select('*').limit(3).execute()
    
    if result.data:
        print("既存レコードの例:")
        for i, item in enumerate(result.data):
            print(f"  レコード{i+1}:")
            print(f"    choice_info: {item.get('choice_info')}")
            print(f"    common_code: {item.get('common_code')}")
            print(f"    product_name: {item.get('product_name', 'N/A')}")
            print()
        
        # choice_infoの構造例を表示
        first_choice_info = result.data[0].get('choice_info', {})
        print(f"choice_info構造例: {first_choice_info}")
        
        if isinstance(first_choice_info, dict):
            print("choice_infoフィールド:")
            for key, value in first_choice_info.items():
                print(f"  {key}: {value}")
    else:
        print("選択肢コード対応表にデータがありません")
    
    return result.data[0] if result.data else None

def find_next_available_cm_codes():
    """次に利用可能なCMコードを探す"""
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    print("\n=== 利用可能なCMコード確認 ===")
    
    # 既存のCMコードを取得
    result = supabase.table('product_master').select('common_code').not_.is_('common_code', 'null').execute()
    
    existing_cm_codes = set()
    for item in result.data:
        code = item.get('common_code', '')
        if code.startswith('CM'):
            existing_cm_codes.add(code)
    
    print(f"既存CMコード数: {len(existing_cm_codes)}件")
    
    # CM200番台から空きを探す（P01=PC系、S01/S02=Special系と想定）
    suggestions = []
    for i in range(200, 300):
        candidate = f"CM{i:03d}"
        if candidate not in existing_cm_codes:
            suggestions.append(candidate)
            if len(suggestions) >= 3:
                break
    
    print(f"提案する新CMコード: {suggestions}")
    return suggestions

def add_missing_choice_codes(dry_run=True):
    """P01、S01、S02を選択肢コード対応表に追加"""
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    print(f"\n=== 選択肢コード追加 (DRY_RUN={dry_run}) ===")
    
    # 利用可能なCMコードを取得
    available_codes = find_next_available_cm_codes()
    
    if len(available_codes) < 3:
        print("エラー: 十分な空きCMコードがありません")
        return False
    
    # 追加する選択肢コードのマッピング
    missing_choice_codes = [
        {
            'choice_code': 'P01',
            'common_code': available_codes[0],
            'product_name': 'プレミアム商品 P01',
            'description': 'P01選択肢コード - プレミアムカテゴリ'
        },
        {
            'choice_code': 'S01',
            'common_code': available_codes[1], 
            'product_name': 'スペシャル商品 S01',
            'description': 'S01選択肢コード - スペシャルカテゴリ'
        },
        {
            'choice_code': 'S02',
            'common_code': available_codes[2],
            'product_name': 'スペシャル商品 S02', 
            'description': 'S02選択肢コード - スペシャルカテゴリ'
        }
    ]
    
    success_count = 0
    
    for choice_data in missing_choice_codes:
        choice_code = choice_data['choice_code']
        common_code = choice_data['common_code']
        
        print(f"\n{choice_code} → {common_code} の追加:")
        
        # 既存チェック
        existing = supabase.table('choice_code_mapping').select('id').filter('choice_info->>choice_code', 'eq', choice_code).execute()
        
        if existing.data:
            print(f"  既存: {choice_code} は既に登録済み")
            continue
        
        # 新しいレコードを準備
        new_record = {
            'choice_info': {
                'choice_code': choice_code,
                'choice_name': f'{choice_code}選択肢',
                'choice_value': choice_data['description'],
                'category': 'manual_addition'
            },
            'common_code': common_code,
            'product_name': choice_data['product_name'],
            'created_at': datetime.now(timezone.utc).isoformat(),
            'updated_at': datetime.now(timezone.utc).isoformat()
        }
        
        if not dry_run:
            try:
                result = supabase.table('choice_code_mapping').insert(new_record).execute()
                if result.data:
                    print(f"  成功: {choice_code} → {common_code} を追加")
                    success_count += 1
                else:
                    print(f"  失敗: {choice_code} の追加に失敗")
            except Exception as e:
                print(f"  エラー: {choice_code} - {str(e)}")
        else:
            print(f"  DRY RUN: {choice_code} → {common_code} を追加予定")
            print(f"    choice_info: {new_record['choice_info']}")
            success_count += 1
    
    print(f"\n完了: {success_count}件の選択肢コードを{'追加予定' if dry_run else '追加'}しました")
    
    return success_count > 0

def verify_addition():
    """追加結果を検証"""
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    print("\n=== 追加結果検証 ===")
    
    choice_codes_to_check = ['P01', 'S01', 'S02']
    
    for code in choice_codes_to_check:
        result = supabase.table('choice_code_mapping').select('*').filter('choice_info->>choice_code', 'eq', code).execute()
        
        if result.data:
            item = result.data[0]
            print(f"✅ {code}: → {item.get('common_code')} ({item.get('product_name')})")
        else:
            print(f"❌ {code}: マッピングなし")

if __name__ == "__main__":
    print("=== P01/S01/S02 選択肢コード追加ツール ===")
    
    # 1. 構造確認
    sample_record = check_choice_code_structure()
    
    if not sample_record:
        print("エラー: 選択肢コード対応表にデータがありません")
        exit(1)
    
    # 2. ドライラン実行
    print("\n" + "="*50)
    print("ドライラン実行中...")
    add_missing_choice_codes(dry_run=True)
    
    # 3. ユーザー確認
    print("\n" + "="*50)
    confirm = input("実際に選択肢コードを追加しますか？ (y/N): ")
    
    if confirm.lower() == 'y':
        print("\n実際の追加を実行中...")
        success = add_missing_choice_codes(dry_run=False)
        
        if success:
            print("\n検証中...")
            verify_addition()
            
            print("\n✅ 完了: P01/S01/S02が選択肢コード対応表に追加されました")
            print("これでマッピングシステムが正常に動作します")
        else:
            print("\n❌ 失敗: 選択肢コードの追加に問題が発生しました")
    else:
        print("\nキャンセル: 変更は行われませんでした")