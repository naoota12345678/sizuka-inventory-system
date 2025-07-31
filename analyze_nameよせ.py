#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
名寄せデータの分析とデータベース構造の検証
スプレッドシートのデータを確認してデータベース設計を最適化
"""

import os
import sys
from collections import defaultdict, Counter
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from product_master.sheets_sync import GoogleSheetsSync
from core.database import supabase

def analyze_product_master():
    """商品マスターデータの分析"""
    print("=== 商品マスターデータ分析 ===\n")
    
    try:
        # Google Sheetsからデータ取得
        sync = GoogleSheetsSync()
        data = sync.read_sheet('商品番号マッピング基本表')
        
        if not data or len(data) < 2:
            print("データが取得できませんでした")
            return
        
        headers = data[0]
        rows = data[1:]
        
        print(f"総データ数: {len(rows)}行")
        print(f"列数: {len(headers)}列")
        print(f"ヘッダー: {headers}\n")
        
        # データをDataFrameに変換
        df = pd.DataFrame(rows, columns=headers)
        
        # 基本統計
        print("=== 基本統計 ===")
        for col in headers:
            if col in df.columns:
                non_empty = df[col].dropna().str.strip().str.len() > 0
                non_empty_count = non_empty.sum() if hasattr(non_empty, 'sum') else 0
                print(f"{col}: {non_empty_count}/{len(df)} ({non_empty_count/len(df)*100:.1f}%)")
        
        # 共通コード分析
        analyze_common_codes(df)
        
        # 商品タイプ分析
        analyze_product_types(df)
        
        # プラットフォーム別商品数
        analyze_platform_coverage(df)
        
        # 重複・欠損チェック
        check_data_quality(df)
        
    except Exception as e:
        print(f"エラー: {str(e)}")

def analyze_common_codes(df):
    """共通コード体系の分析"""
    print("\n=== 共通コード分析 ===")
    
    if '共通コード' not in df.columns:
        print("共通コードが見つかりません")
        return
    
    codes = df['共通コード'].dropna().str.strip()
    codes = codes[codes.str.len() > 0]
    
    print(f"共通コード総数: {len(codes)}")
    print(f"ユニーク数: {codes.nunique()}")
    print(f"重複数: {len(codes) - codes.nunique()}")
    
    # プレフィックス分析
    prefixes = codes.str[:2].value_counts()
    print(f"\nプレフィックス分布:")
    for prefix, count in prefixes.items():
        percentage = count / len(codes) * 100
        print(f"  {prefix}: {count}件 ({percentage:.1f}%)")
    
    # 長さ分析
    lengths = codes.str.len().value_counts().sort_index()
    print(f"\nコード長分布:")
    for length, count in lengths.items():
        print(f"  {length}桁: {count}件")

def analyze_product_types(df):
    """商品タイプの分析"""
    print("\n=== 商品タイプ分析 ===")
    
    if '商品タイプ' in df.columns:
        types = df['商品タイプ'].dropna().str.strip()
        type_counts = types.value_counts()
        print("明示的な商品タイプ:")
        for type_name, count in type_counts.items():
            print(f"  {type_name}: {count}件")
    
    # 共通コードから推定される商品タイプ
    if '共通コード' in df.columns:
        codes = df['共通コード'].dropna().str.strip()
        inferred_types = codes.apply(infer_product_type)
        inferred_counts = inferred_types.value_counts()
        
        print(f"\n共通コードから推定される商品タイプ:")
        for type_name, count in inferred_counts.items():
            print(f"  {type_name}: {count}件")

def infer_product_type(code):
    """共通コードから商品タイプを推定"""
    if pd.isna(code) or len(str(code).strip()) == 0:
        return "不明"
    
    code = str(code).strip().upper()
    if code.startswith('CM'):
        return '単品'
    elif code.startswith('BC'):
        return 'セット商品'
    elif code.startswith('PC'):
        return 'まとめ商品'
    else:
        return 'その他'

def analyze_platform_coverage(df):
    """プラットフォーム別商品カバレッジ分析"""
    print("\n=== プラットフォーム別カバレッジ ===")
    
    platform_columns = [
        ('楽天SKU', '楽天'),
        ('カラーミーID', 'カラーミー'),
        ('スマレジID', 'スマレジ'),
        ('Yahoo商品ID', 'Yahoo'),
        ('Amazon ASIN', 'Amazon'),
        ('メルカリ商品ID', 'メルカリ')
    ]
    
    total_products = len(df)
    
    for col_name, platform_name in platform_columns:
        if col_name in df.columns:
            non_empty = df[col_name].dropna().str.strip()
            non_empty = non_empty[non_empty.str.len() > 0]
            coverage = len(non_empty) / total_products * 100
            print(f"{platform_name}: {len(non_empty)}/{total_products} ({coverage:.1f}%)")

def check_data_quality(df):
    """データ品質チェック"""
    print("\n=== データ品質チェック ===")
    
    issues = []
    
    # 共通コードの重複
    if '共通コード' in df.columns:
        codes = df['共通コード'].dropna().str.strip()
        codes = codes[codes.str.len() > 0]
        duplicates = codes[codes.duplicated()].unique()
        if len(duplicates) > 0:
            issues.append(f"重複する共通コード: {len(duplicates)}件")
            print(f"重複共通コード: {list(duplicates)[:5]}...")
    
    # 必須フィールドの欠損
    required_fields = ['共通コード', '基本商品名']
    for field in required_fields:
        if field in df.columns:
            empty_count = df[field].isna().sum() + (df[field].str.strip() == '').sum()
            if empty_count > 0:
                issues.append(f"{field}が空: {empty_count}件")
    
    # 商品名の重複
    if '基本商品名' in df.columns:
        names = df['基本商品名'].dropna().str.strip()
        duplicate_names = names[names.duplicated()].unique()
        if len(duplicate_names) > 0:
            issues.append(f"重複する商品名: {len(duplicate_names)}件")
    
    if issues:
        print("発見された問題:")
        for issue in issues:
            print(f"  ❌ {issue}")
    else:
        print("✅ 主要な品質問題は発見されませんでした")

def analyze_choice_codes():
    """選択肢コード対応表の分析"""
    print("\n=== 選択肢コード分析 ===")
    
    try:
        sync = GoogleSheetsSync()
        data = sync.read_sheet('選択肢コード対応表')
        
        if not data or len(data) < 2:
            print("選択肢コードデータが取得できませんでした")
            return
        
        headers = data[0]
        rows = data[1:]
        df = pd.DataFrame(rows, columns=headers)
        
        print(f"選択肢コード総数: {len(df)}件")
        
        if '選択肢コード' in df.columns and '新共通コード' in df.columns:
            choice_codes = df['選択肢コード'].dropna().str.strip()
            common_codes = df['新共通コード'].dropna().str.strip()
            
            print(f"ユニーク選択肢コード: {choice_codes.nunique()}件")
            print(f"対応する共通コード: {common_codes.nunique()}件")
            
            # 1つの共通コードに対応する選択肢コード数
            code_mapping = df.groupby('新共通コード')['選択肢コード'].count()
            print(f"\n共通コードあたりの選択肢数:")
            print(f"  平均: {code_mapping.mean():.1f}個")
            print(f"  最大: {code_mapping.max()}個")
            print(f"  最小: {code_mapping.min()}個")
        
    except Exception as e:
        print(f"選択肢コード分析エラー: {str(e)}")

def analyze_package_components():
    """まとめ商品内訳の分析"""
    print("\n=== まとめ商品内訳分析 ===")
    
    try:
        sync = GoogleSheetsSync()
        data = sync.read_sheet('まとめ商品内訳テーブル')
        
        if not data or len(data) < 2:
            print("まとめ商品データが取得できませんでした")
            return
        
        # ヘッダー行を探す
        header_row = None
        for i, row in enumerate(data):
            if any('内訳ID' in str(cell) for cell in row):
                header_row = i
                break
        
        if header_row is None:
            print("ヘッダー行が見つかりませんでした")
            return
        
        headers = data[header_row]
        rows = data[header_row + 1:]
        df = pd.DataFrame(rows, columns=headers)
        
        print(f"まとめ商品内訳総数: {len(df)}件")
        
        if 'まとめ商品共通コード' in df.columns:
            package_codes = df['まとめ商品共通コード'].dropna().str.strip()
            package_codes = package_codes[package_codes.str.len() > 0]
            
            print(f"ユニークまとめ商品: {package_codes.nunique()}件")
            
            # まとめ商品あたりの構成品数
            component_counts = df.groupby('まとめ商品共通コード').size()
            print(f"\nまとめ商品あたりの構成品数:")
            print(f"  平均: {component_counts.mean():.1f}個")
            print(f"  最大: {component_counts.max()}個")
            print(f"  最小: {component_counts.min()}個")
        
    except Exception as e:
        print(f"まとめ商品分析エラー: {str(e)}")

def check_database_consistency():
    """データベースとの整合性チェック"""
    print("\n=== データベース整合性チェック ===")
    
    try:
        # 現在のDB内容を確認
        db_products = supabase.table('product_master').select('common_code', 'product_name', 'product_type').execute()
        
        if db_products.data:
            print(f"データベース内商品数: {len(db_products.data)}件")
            
            db_codes = set(p['common_code'] for p in db_products.data)
            
            # スプレッドシートとの比較
            sync = GoogleSheetsSync()
            sheet_data = sync.read_sheet('商品番号マッピング基本表')
            
            if sheet_data and len(sheet_data) > 1:
                headers = sheet_data[0]
                rows = sheet_data[1:]
                
                if '共通コード' in headers:
                    code_idx = headers.index('共通コード')
                    sheet_codes = set()
                    for row in rows:
                        if len(row) > code_idx and row[code_idx]:
                            sheet_codes.add(str(row[code_idx]).strip())
                    
                    print(f"スプレッドシート内商品数: {len(sheet_codes)}件")
                    
                    # 差分分析
                    only_in_db = db_codes - sheet_codes
                    only_in_sheet = sheet_codes - db_codes
                    
                    if only_in_db:
                        print(f"DBのみに存在: {len(only_in_db)}件")
                    if only_in_sheet:
                        print(f"スプレッドシートのみに存在: {len(only_in_sheet)}件")
                    
                    if not only_in_db and not only_in_sheet:
                        print("✅ データベースとスプレッドシートは同期されています")
        else:
            print("データベースにデータがありません")
            
    except Exception as e:
        print(f"データベース整合性チェックエラー: {str(e)}")

def recommend_database_improvements():
    """データベース改善提案"""
    print("\n=== データベース改善提案 ===")
    
    recommendations = [
        "1. 共通コードに制約を追加（正規表現チェック）",
        "2. 商品タイプのENUM制約を追加",
        "3. プラットフォーム固有IDの重複チェック機能",
        "4. データ変更履歴テーブルの追加",
        "5. 自動バックアップ機能の実装"
    ]
    
    for rec in recommendations:
        print(f"  📋 {rec}")

if __name__ == "__main__":
    print("名寄せデータ分析開始...\n")
    
    analyze_product_master()
    analyze_choice_codes()
    analyze_package_components()
    check_database_consistency()
    recommend_database_improvements()
    
    print("\n分析完了！")