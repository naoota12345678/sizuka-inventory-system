#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
楽天API文字エンコード修正のテスト
既存の文字化けデータから選択肢コード抽出テスト
"""

import os
import re
from supabase import create_client

# 環境変数を設定
os.environ['SUPABASE_URL'] = 'https://equrcpeifogdrxoldkpe.supabase.co'
os.environ['SUPABASE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ'

SUPABASE_URL = "https://equrcpeifogdrxoldkpe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ"

def fix_encoding(text):
    """文字化け修正を試行"""
    if not text:
        return text
    
    try:
        # latin1 → utf-8 変換を試行
        fixed_text = text.encode('latin1').decode('utf-8', errors='ignore')
        return fixed_text
    except Exception as e:
        print(f"エンコード変換エラー: {e}")
        return text

def extract_choice_codes(text):
    """選択肢コードを抽出"""
    if not text:
        return []
    
    pattern = r'[A-Z]\d{2}'
    matches = re.findall(pattern, text)
    return matches

def test_encoding_fix():
    """文字化け修正テスト"""
    print("文字化け修正テスト")
    print("=" * 50)
    
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # 文字化けしている可能性のあるレコードを取得
    result = supabase.table("order_items").select(
        "id, choice_code, product_name"
    ).not_.like("product_code", "TEST%").limit(20).execute()
    
    print(f"テスト対象: {len(result.data)}件\n")
    
    improved_count = 0
    total_tested = 0
    
    for item in result.data:
        choice_code = item.get('choice_code', '')
        product_name = item.get('product_name', '')
        item_id = item.get('id')
        
        if choice_code:
            total_tested += 1
            
            # 修正前の選択肢コード抽出
            original_codes = extract_choice_codes(choice_code)
            
            # エンコード修正後の選択肢コード抽出
            fixed_choice_code = fix_encoding(choice_code)
            fixed_codes = extract_choice_codes(fixed_choice_code)
            
            print(f"ID {item_id}:")
            print(f"  元データ: {choice_code}")
            print(f"  修正後  : {fixed_choice_code}")
            print(f"  元抽出  : {original_codes}")
            print(f"  修正抽出: {fixed_codes}")
            
            # 改善があったかチェック
            if len(fixed_codes) > len(original_codes) or (fixed_codes and not original_codes):
                print(f"  ✅ 改善: {len(original_codes)} → {len(fixed_codes)}件")
                improved_count += 1
            elif fixed_choice_code != choice_code:
                print(f"  📝 文字修正: 選択肢コード変化")
            else:
                print(f"  ➖ 変化なし")
            print()
    
    print("=" * 50)
    print(f"テスト結果:")
    print(f"  テスト件数: {total_tested}")
    print(f"  改善件数: {improved_count}")
    print(f"  改善率: {improved_count/total_tested*100:.1f}%" if total_tested > 0 else "0%")

def test_specific_corrupted_text():
    """特定の文字化けパターンをテスト"""
    print("\n特定文字化けパターンテスト")
    print("=" * 30)
    
    # 実際のDBから取得した文字化けテキスト例
    test_cases = [
        "注文への配送不可です:変更出来",
        "注文へのため配送不可です:変更出来", 
        "R08配送不可",
        "選択肢C01です",
        "",
        "normal R05 code"
    ]
    
    for text in test_cases:
        original_codes = extract_choice_codes(text)
        fixed_text = fix_encoding(text)
        fixed_codes = extract_choice_codes(fixed_text)
        
        print(f"入力: '{text}'")
        print(f"修正: '{fixed_text}'")
        print(f"抽出: {original_codes} → {fixed_codes}")
        print()

if __name__ == "__main__":
    test_encoding_fix()
    test_specific_corrupted_text()