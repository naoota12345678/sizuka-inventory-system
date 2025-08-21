#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
製造データExcelファイル分析スクリプト
"""

import pandas as pd

def analyze_manufacturing_excel():
    """製造Excelファイルを分析"""
    file_path = r'C:\Users\naoot\Downloads\製造.xlsx'
    print('=== 製造データ分析 ===')

    try:
        # シート一覧確認
        xl_file = pd.ExcelFile(file_path)
        print(f'シート一覧: {xl_file.sheet_names}')
        
        # 各シートの内容確認
        for sheet_name in xl_file.sheet_names:
            print(f'\n--- {sheet_name} ---')
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            print(f'行数: {len(df)}')
            print(f'列数: {len(df.columns)}')
            print(f'列名: {list(df.columns)}')
            
            # 最初の5行を表示
            print('\n最初の5行:')
            print(df.head().to_string())
            
            # 日付・数量・商品名らしき列があるかチェック
            date_cols = [col for col in df.columns if any(keyword in str(col).lower() for keyword in ['日付', 'date', '年', '月', '日'])]
            quantity_cols = [col for col in df.columns if any(keyword in str(col).lower() for keyword in ['数量', 'quantity', '個数', '製造', '生産'])]
            product_cols = [col for col in df.columns if any(keyword in str(col).lower() for keyword in ['商品', 'product', '品名', 'name'])]
            
            if date_cols:
                print(f'\n日付関連列: {date_cols}')
            if quantity_cols:
                print(f'数量関連列: {quantity_cols}')
            if product_cols:
                print(f'商品関連列: {product_cols}')
                
            # データの統計情報
            if len(df) > 0 and not df.empty:
                print(f'\nデータサンプル（製造記録）:')
                for i, row in df.head(10).iterrows():
                    row_data = []
                    for col in df.columns:
                        value = row[col]
                        if pd.notna(value) and str(value).strip() and str(value) != 'nan':
                            row_data.append(f'{col}={value}')
                    if row_data:
                        print(f'  行{i+1}: {" | ".join(row_data[:3])}')  # 最初の3つの値のみ表示
            
            print('\n' + '='*50)
            
    except Exception as e:
        print(f'エラー: {str(e)}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    analyze_manufacturing_excel()