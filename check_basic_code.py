#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
基本コードの列を詳細確認
"""

import requests
import csv
from io import StringIO

SPREADSHEET_ID = "1mLg1N0a1wubEIdKSouiW_jDaWUnuFLBxj8greczuS3E"
MAPPING_GID = "1290908701"

def check_basic_code_column():
    """基本コード列の詳細確認"""
    try:
        csv_url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid={MAPPING_GID}"
        response = requests.get(csv_url, timeout=30)
        response.raise_for_status()
        
        if response.encoding != 'utf-8':
            response.encoding = 'utf-8'
        
        csv_data = StringIO(response.text)
        reader = csv.DictReader(csv_data)
        data = list(reader)
        
        print("=== Google Sheets列構造の再詳細確認 ===")
        print(f"総行数: {len(data)}行")
        
        # ヘッダー行の詳細確認
        if data:
            columns = list(data[0].keys())
            print(f"\n=== 列構造詳細（全{len(columns)}列） ===")
            for i, col in enumerate(columns):
                print(f"{i:2d}: {repr(col)}")
            
            print(f"\n=== 最初の行のデータ（基本コードの確認） ===")
            first_row = data[0]
            for i, (key, value) in enumerate(first_row.items()):
                print(f"{i:2d}: {key} = {repr(value)}")
            
            # 基本コードの可能性がある列を探す
            print(f"\n=== 基本コードの可能性がある列の値確認 ===")
            for i, col in enumerate(columns):
                if "基本" in col:
                    sample_values = [row.get(col, "") for row in data[:5]]
                    print(f"{i}: {col} のサンプル値: {sample_values}")
            
            # ユーザー提供データと正確に照合
            print(f"\n=== ユーザー提供データとの正確な照合 ===")
            print("ユーザー提供:")
            print("連番    共通コード    JAN/EANコード    基本商品名    楽天SKU")
            print("1       CM001        4573265581011    エゾ鹿スライスジャーキー 30g    1701")
            
            # 実際のデータ
            first_row = data[0]
            print(f"\nGoogle Sheets実データ:")
            print(f"連番: {first_row.get('連番', '')}")
            print(f"共通コード: {first_row.get('共通コード', '')}")
            print(f"JAN/EANコード: {first_row.get('JAN/EANコード', '')}")
            print(f"基本商品名: {first_row.get('基本商品名', '')}")
            print(f"楽天SKU: {first_row.get('楽天SKU', '')}")
            
            # すべての列の値を確認（最初の行）
            print(f"\n=== CM001行の全データ ===")
            for i, (key, value) in enumerate(first_row.items()):
                if value and value.strip():
                    print(f"{i:2d}: {key} = {value}")
        
    except Exception as e:
        print(f"エラー: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_basic_code_column()