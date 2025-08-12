#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Google Sheetsの列マッピングを正確に調査
"""

import requests
import csv
from io import StringIO

SPREADSHEET_ID = "1mLg1N0a1wubEIdKSouiW_jDaWUnuFLBxj8greczuS3E"
MAPPING_GID = "1290908701"

def debug_column_mapping():
    """Google Sheetsの列構造を詳細調査"""
    try:
        csv_url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid={MAPPING_GID}"
        response = requests.get(csv_url, timeout=30)
        response.raise_for_status()
        
        if response.encoding != 'utf-8':
            response.encoding = 'utf-8'
        
        csv_data = StringIO(response.text)
        reader = csv.DictReader(csv_data)
        data = list(reader)
        
        print("=== Google Sheets列構造とデータ詳細調査 ===")
        print(f"総行数: {len(data)}行")
        
        # 列名とインデックスの対応確認
        columns = list(data[0].keys()) if data else []
        print(f"\n=== 列名とインデックス対応表 ===")
        for i, col in enumerate(columns):
            print(f"{i}: '{col}'")
        
        # 最初の3行の全データを列ごとに表示
        print(f"\n=== 最初の3行の詳細データ ===")
        for row_idx, row in enumerate(data[:3]):
            print(f"\n--- 行{row_idx+1} ---")
            for col_idx, (key, value) in enumerate(row.items()):
                display_value = value if value else "(空)"
                print(f"[{col_idx:2d}] {key}: {display_value}")
        
        # ユーザー提供データと比較
        print(f"\n=== ユーザー提供データとの照合 ===")
        expected_data = {
            "CM001": {
                "楽天SKU": "1701",
                "カラーミーID": "71898726", 
                "Amazon": "B0B2R5V8BG",
                "Yahoo": "1701",
                "メルカリ": "5LCeqpCPZVPB8jNcfXyRF4"
            },
            "CM002": {
                "楽天SKU": "1702",
                "カラーミーID": "71907306",
                "Amazon": "B0B3N9YFV8", 
                "Yahoo": "1702",
                "メルカリ": "o2oMgdV3ieTSAfcLkQpZnN"
            }
        }
        
        # CM001とCM002のデータ確認
        for target_cm in ["CM001", "CM002"]:
            for row in data[:10]:  # 最初の10行から探す
                if row.get(columns[1], '').strip() == target_cm:  # 共通コード列
                    print(f"\n{target_cm}の実際のデータ:")
                    for col_idx, (key, value) in enumerate(row.items()):
                        if value and value.strip():
                            print(f"  [{col_idx:2d}] {key}: {value}")
                    
                    # 期待データと比較
                    expected = expected_data.get(target_cm, {})
                    print(f"\n{target_cm}の期待データ:")
                    for exp_key, exp_value in expected.items():
                        print(f"  {exp_key}: {exp_value}")
                    break
        
        return columns, data
        
    except Exception as e:
        print(f"エラー: {str(e)}")
        import traceback
        traceback.print_exc()
        return None, None

if __name__ == "__main__":
    columns, data = debug_column_mapping()