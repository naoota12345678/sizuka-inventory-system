#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
正しい選択肢コード抽出（大文字英語1文字 + 数字2桁）
"""

import re
from typing import List

def extract_choice_codes(choice_code: str) -> List[str]:
    """
    選択肢コードから商品コード（R05, N03等）を抽出
    パターン: 大文字英語1文字 + 数字2桁
    
    Args:
        choice_code: 楽天の選択肢コード文字列
        
    Returns:
        List[str]: 抽出された商品コードのリスト
    """
    if not choice_code:
        return []
    
    # パターン: 大文字英語1文字 + 数字2桁
    pattern = r'[A-Z]\d{2}'
    
    # 全てのマッチを取得
    matches = re.findall(pattern, choice_code)
    
    # 重複を除去して順序を保持
    seen = set()
    result = []
    for match in matches:
        if match not in seen:
            seen.add(match)
            result.append(match)
    
    return result

# テスト実行
if __name__ == "__main__":
    # テストケース
    test_cases = [
        "◆１:R05 エゾ鹿レバー30g\n◆２:R13 鶏砂肝ジャーキー30g\n◆３:R14 豚ハツスライス30g\n◆４:R08 ひとくちサーモン30g",
        "★1つ目:N03サーモンチップ10g\n★2つ目:N03.サーモンチップ10g\n★3つ目:N06チキンチップ10g",
        "◆１:R11 鶏ささみスライス30g\n◆２:R12 鶏むねスライス30g\n◆３:R01 エゾ鹿スライス30g"
    ]
    
    print("=== Choice Code Extraction Test ===")
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\nTest {i}:")
        print(f"Input: {test_case[:50]}...")
        
        codes = extract_choice_codes(test_case)
        print(f"Extracted codes: {codes}")