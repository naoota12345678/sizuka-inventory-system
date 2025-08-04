#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
選択肢コードから実際の商品コードを抽出する機能
"""

import re
from typing import List, Dict, Set

def extract_product_codes_from_choice(choice_code: str) -> List[str]:
    """
    選択肢コードから実際の商品コード（R05, R13等）を抽出
    
    Args:
        choice_code: 楽天の選択肢コード文字列
        
    Returns:
        List[str]: 抽出された商品コードのリスト
    """
    if not choice_code:
        return []
    
    # Rで始まる数字のパターンを抽出（R05, R13, R14, R08等）
    # パターン: R + 2桁以上の数字
    pattern = r'R\d{2,}'
    
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

def analyze_choice_code_detailed(choice_code: str) -> Dict:
    """
    選択肢コードを詳細分析
    
    Args:
        choice_code: 楽天の選択肢コード文字列
        
    Returns:
        Dict: 分析結果
    """
    if not choice_code:
        return {
            "product_codes": [],
            "choice_count": 0,
            "raw_choices": [],
            "analysis": "Empty choice code"
        }
    
    # 商品コード抽出
    product_codes = extract_product_codes_from_choice(choice_code)
    
    # 選択肢を行ごとに分割
    lines = choice_code.split('\n')
    choices = []
    
    for line in lines:
        line = line.strip()
        if line and ('◆' in line or '★' in line or '【' in line):
            choices.append(line)
    
    return {
        "product_codes": product_codes,
        "choice_count": len(product_codes),
        "raw_choices": choices,
        "analysis": f"Found {len(product_codes)} product codes: {', '.join(product_codes)}"
    }

def create_inventory_updates(choice_code: str, quantity: int = 1) -> List[Dict]:
    """
    選択肢コードから在庫更新データを作成
    
    Args:
        choice_code: 楽天の選択肢コード
        quantity: 注文数量（デフォルト1）
        
    Returns:
        List[Dict]: 在庫更新用のデータリスト
    """
    product_codes = extract_product_codes_from_choice(choice_code)
    
    updates = []
    for code in product_codes:
        updates.append({
            "product_code": code,
            "quantity_to_reduce": quantity,
            "source": "rakuten_choice_selection"
        })
    
    return updates

# テスト用のサンプルデータ
def test_choice_code_parser():
    """テスト実行"""
    
    # ユーザーが提供したサンプル
    sample_choice = """◆１:R05 エゾ鹿レバー30g
◆２:R13 鶏砂肝ジャーキー30g
◆３:R14 豚ハツスライス30g
◆４（※レトルトはこちら◇からお選びください）:R08 ひとくちサーモン30g
【ご注意】37〜44のレトルトは、お選びいただく４袋中、1袋のみ選択可能。:確認済
★メール便のため同梱不可です:了承済み"""
    
    print("=== Choice Code Parser Test ===")
    print(f"Input Choice Code:")
    print(sample_choice)
    print()
    
    # 商品コード抽出テスト
    codes = extract_product_codes_from_choice(sample_choice)
    print(f"Extracted Product Codes: {codes}")
    print()
    
    # 詳細分析テスト
    analysis = analyze_choice_code_detailed(sample_choice)
    print(f"Detailed Analysis:")
    for key, value in analysis.items():
        print(f"  {key}: {value}")
    print()
    
    # 在庫更新データ作成テスト
    updates = create_inventory_updates(sample_choice, quantity=2)
    print(f"Inventory Updates (quantity=2):")
    for update in updates:
        print(f"  - {update}")

if __name__ == "__main__":
    test_choice_code_parser()