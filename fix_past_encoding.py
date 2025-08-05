#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
過去の文字化けchoice_codeデータを修正
"""

import os
import re
from supabase import create_client

# 環境変数を設定
os.environ['SUPABASE_URL'] = 'https://equrcpeifogdrxoldkpe.supabase.co'
os.environ['SUPABASE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ'

SUPABASE_URL = "https://equrcpeifogdrxoldkpe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ"

def fix_corrupted_choice_codes():
    """文字化けしたchoice_codeを修正"""
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    print("=== 文字化けchoice_code修正 ===")
    
    # 文字化けパターンを含むレコードを取得
    corrupted_pattern = "注文への配送不可です:変更出来"
    
    # すべてのorder_itemsを取得して文字化けパターンを探す
    result = supabase.table("order_items").select("id, choice_code, product_name").execute()
    
    corrupted_count = 0
    fixed_count = 0
    
    for item in result.data:
        choice_code = item.get('choice_code', '')
        
        # 文字化けパターンが含まれているか確認
        if corrupted_pattern in choice_code:
            corrupted_count += 1
            
            # product_nameから選択肢コードを抽出
            product_name = item.get('product_name', '')
            
            # 正規表現で選択肢コードパターンを抽出
            pattern = r'[A-Z]\d{2}'
            matches = re.findall(pattern, product_name)
            
            if matches:
                # 最初に見つかった選択肢コードを使用
                new_choice_code = matches[0]
                
                # choice_codeを更新
                try:
                    update_result = supabase.table("order_items").update({
                        'choice_code': new_choice_code
                    }).eq('id', item['id']).execute()
                    
                    if update_result.data:
                        print(f"修正: ID {item['id']}: '{choice_code[:20]}...' → '{new_choice_code}'")
                        fixed_count += 1
                except Exception as e:
                    print(f"エラー: ID {item['id']}: {str(e)}")
            else:
                print(f"選択肢コード抽出失敗: ID {item['id']} - {product_name[:50]}")
    
    print(f"\n=== 結果 ===")
    print(f"文字化けレコード: {corrupted_count}件")
    print(f"修正成功: {fixed_count}件")
    
    return fixed_count > 0

if __name__ == "__main__":
    fix_corrupted_choice_codes()