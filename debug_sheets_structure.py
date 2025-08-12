#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Google Sheetsの実際のデータ構造を詳細調査
"""

import requests
import csv
from io import StringIO
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SPREADSHEET_ID = "1mLg1N0a1wubEIdKSouiW_jDaWUnuFLBxj8greczuS3E"
MAPPING_GID = "1290908701"  # 商品番号マッピング基本表

def analyze_sheets_structure():
    """Google Sheetsの構造を詳細分析"""
    try:
        csv_url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid={MAPPING_GID}"
        
        print("=== Google Sheets実際のデータ構造確認 ===")
        response = requests.get(csv_url, timeout=30)
        response.raise_for_status()
        
        # UTF-8エンコーディング強制
        if response.encoding != 'utf-8':
            response.encoding = 'utf-8'
        
        csv_data = StringIO(response.text)
        reader = csv.DictReader(csv_data)
        data = list(reader)
        
        print(f"Google Sheetsから取得: {len(data)}行")
        
        if not data:
            print("データが空です")
            return
        
        # 列名一覧
        print("\n=== 列名一覧 ===")
        columns = list(data[0].keys())
        for i, col in enumerate(columns):
            print(f"{i}: {col}")
        
        # 最初の5行のサンプルデータ
        print("\n=== 最初の5行のデータサンプル ===")
        for i, row in enumerate(data[:5]):
            print(f"\n--- 行{i+1} ---")
            for key, value in row.items():
                if value and str(value).strip():
                    print(f"  {key}: {value}")
                else:
                    print(f"  {key}: (空)")
        
        # 楽天SKU列を探す
        print("\n=== 楽天SKU列の検索 ===")
        rakuten_cols = []
        for col in columns:
            col_lower = col.lower()
            if any(keyword in col_lower for keyword in ['楽天', 'rakuten', 'sku']) or '楽天' in col:
                rakuten_cols.append(col)
        
        print(f"楽天SKU候補列: {rakuten_cols}")
        
        # Amazon列を探す  
        print("\n=== Amazon列の検索 ===")
        amazon_cols = []
        for col in columns:
            col_lower = col.lower()
            if 'amazon' in col_lower or 'asin' in col_lower:
                amazon_cols.append(col)
        
        print(f"Amazon候補列: {amazon_cols}")
        
        # カラーミー列を探す
        print("\n=== カラーミー列の検索 ===")
        colorMe_cols = []
        for col in columns:
            if 'カラーミー' in col or 'colorme' in col.lower():
                colorMe_cols.append(col)
        
        print(f"カラーミー候補列: {colorMe_cols}")
        
        # 各列の値を詳細確認
        if rakuten_cols:
            rakuten_col = rakuten_cols[0]
            print(f"\n=== 楽天SKU列 '{rakuten_col}' の値分析 ===")
            rakuten_values = []
            empty_count = 0
            for i, row in enumerate(data[:20]):
                value = row.get(rakuten_col, '').strip()
                if value:
                    rakuten_values.append(value)
                    print(f"行{i+1}: {value}")
                else:
                    empty_count += 1
                    print(f"行{i+1}: (空)")
            
            print(f"\n楽天SKU統計:")
            print(f"  有効値: {len(rakuten_values)}個")
            print(f"  空値: {empty_count}個")
            
            if rakuten_values:
                print(f"  サンプル値: {rakuten_values[:10]}")
        
        if amazon_cols:
            amazon_col = amazon_cols[0]
            print(f"\n=== Amazon列 '{amazon_col}' の値分析 ===")
            amazon_values = []
            for i, row in enumerate(data[:10]):
                value = row.get(amazon_col, '').strip()
                if value:
                    amazon_values.append(value)
                    print(f"行{i+1}: {value}")
                else:
                    print(f"行{i+1}: (空)")
            
            if amazon_values:
                print(f"Amazon値サンプル: {amazon_values}")
        
        # 共通コード列も確認
        print("\n=== 共通コード列の検索 ===")
        common_cols = []
        for col in columns:
            if '共通' in col or 'common' in col.lower() or 'コード' in col:
                common_cols.append(col)
        
        print(f"共通コード候補列: {common_cols}")
        
        if common_cols:
            common_col = common_cols[0]
            print(f"\n=== 共通コード列 '{common_col}' の値分析 ===")
            common_values = []
            for i, row in enumerate(data[:10]):
                value = row.get(common_col, '').strip()
                if value:
                    common_values.append(value)
                    print(f"行{i+1}: {value}")
            
            if common_values:
                print(f"共通コード値サンプル: {common_values}")
        
        return data, columns, rakuten_cols, amazon_cols
        
    except Exception as e:
        print(f"エラー: {str(e)}")
        import traceback
        traceback.print_exc()
        return None, None, None, None

if __name__ == "__main__":
    analyze_sheets_structure()