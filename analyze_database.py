#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
データベース内容の分析
既存の名寄せデータを確認して構造を最適化
"""

import os
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.database import supabase

def analyze_product_master():
    """商品マスターの分析"""
    print("=== 商品マスター分析 ===\n")
    
    try:
        # 全商品データ取得
        result = supabase.table('product_master').select('*').execute()
        products = result.data
        
        if not products:
            print("商品データが見つかりません")
            return
        
        print(f"総商品数: {len(products)}件")
        
        # 共通コード分析
        common_codes = [p['common_code'] for p in products if p['common_code']]
        print(f"共通コード件数: {len(common_codes)}件")
        print(f"ユニーク件数: {len(set(common_codes))}件")
        
        if len(common_codes) != len(set(common_codes)):
            duplicates = [code for code, count in Counter(common_codes).items() if count > 1]
            print(f"重複する共通コード: {duplicates}")
        
        # プレフィックス分析
        prefixes = [code[:2] for code in common_codes if len(code) >= 2]
        prefix_counts = Counter(prefixes)
        print(f"\nプレフィックス分布:")
        for prefix, count in prefix_counts.most_common():
            percentage = count / len(common_codes) * 100
            print(f"  {prefix}: {count}件 ({percentage:.1f}%)")
        
        # 商品タイプ分析
        product_types = [p['product_type'] for p in products if p['product_type']]
        type_counts = Counter(product_types)
        print(f"\n商品タイプ分布:")
        for ptype, count in type_counts.most_common():
            print(f"  {ptype}: {count}件")
        
        # プラットフォーム別登録状況
        analyze_platform_data(products)
        
        # データ品質チェック
        check_data_quality(products)
        
    except Exception as e:
        print(f"エラー: {str(e)}")

def analyze_platform_data(products):
    """プラットフォーム別データ分析"""
    print(f"\n=== プラットフォーム別登録状況 ===")
    
    platform_fields = {
        'rakuten_sku': '楽天',
        'colorme_id': 'カラーミー',
        'smaregi_id': 'スマレジ',
        'yahoo_id': 'Yahoo',
        'amazon_asin': 'Amazon',
        'mercari_id': 'メルカリ'
    }
    
    total = len(products)
    
    for field, name in platform_fields.items():
        count = sum(1 for p in products if p.get(field) and str(p[field]).strip())
        percentage = count / total * 100
        print(f"{name}: {count}/{total} ({percentage:.1f}%)")

def check_data_quality(products):
    """データ品質チェック"""
    print(f"\n=== データ品質チェック ===")
    
    issues = []
    
    # 必須フィールドチェック
    required_fields = ['common_code', 'product_name']
    for field in required_fields:
        empty_count = sum(1 for p in products if not p.get(field) or not str(p[field]).strip())
        if empty_count > 0:
            issues.append(f"{field}が空: {empty_count}件")
    
    # 商品名重複チェック
    product_names = [p['product_name'] for p in products if p.get('product_name')]
    name_counts = Counter(product_names)
    duplicate_names = [name for name, count in name_counts.items() if count > 1]
    if duplicate_names:
        issues.append(f"重複商品名: {len(duplicate_names)}件")
        print(f"重複商品名例: {duplicate_names[:3]}")
    
    # JANコード重複チェック
    jan_codes = [p['jan_code'] for p in products if p.get('jan_code') and str(p['jan_code']).strip()]
    if jan_codes:
        jan_counts = Counter(jan_codes)
        duplicate_jans = [jan for jan, count in jan_counts.items() if count > 1]
        if duplicate_jans:
            issues.append(f"重複JANコード: {len(duplicate_jans)}件")
    
    if issues:
        print("発見された問題:")
        for issue in issues:
            print(f"  NG {issue}")
    else:
        print("OK 主要な品質問題は発見されませんでした")

def analyze_choice_codes():
    """選択肢コード分析"""
    print(f"\n=== 選択肢コード分析 ===")
    
    try:
        result = supabase.table('choice_code_mapping').select('*').execute()
        choice_codes = result.data
        
        if not choice_codes:
            print("選択肢コードデータが見つかりません")
            return
        
        print(f"選択肢コード総数: {len(choice_codes)}件")
        
        # 共通コードごとの選択肢数
        code_groups = defaultdict(list)
        for choice in choice_codes:
            if choice.get('common_code'):
                code_groups[choice['common_code']].append(choice['choice_code'])
        
        choice_counts = [len(choices) for choices in code_groups.values()]
        print(f"対応する共通コード数: {len(code_groups)}件")
        print(f"平均選択肢数: {sum(choice_counts) / len(choice_counts):.1f}個")
        print(f"最大選択肢数: {max(choice_counts)}個")
        
        # 選択肢が多い商品
        many_choices = [(code, len(choices)) for code, choices in code_groups.items() if len(choices) > 5]
        if many_choices:
            print(f"選択肢が多い商品（5個以上）:")
            for code, count in sorted(many_choices, key=lambda x: x[1], reverse=True)[:5]:
                print(f"  {code}: {count}個")
        
    except Exception as e:
        print(f"選択肢コード分析エラー: {str(e)}")

def analyze_package_components():
    """まとめ商品内訳分析"""
    print(f"\n=== まとめ商品内訳分析 ===")
    
    try:
        result = supabase.table('package_components').select('*').execute()
        components = result.data
        
        if not components:
            print("まとめ商品データが見つかりません")
            return
        
        print(f"まとめ商品内訳総数: {len(components)}件")
        
        # まとめ商品ごとの構成品数
        package_groups = defaultdict(list)
        for comp in components:
            if comp.get('package_code'):
                package_groups[comp['package_code']].append(comp['component_code'])
        
        component_counts = [len(comps) for comps in package_groups.values()]
        print(f"ユニークまとめ商品数: {len(package_groups)}件")
        print(f"平均構成品数: {sum(component_counts) / len(component_counts):.1f}個")
        print(f"最大構成品数: {max(component_counts)}個")
        
        # 構成品が多いまとめ商品
        many_components = [(code, len(comps)) for code, comps in package_groups.items() if len(comps) > 3]
        if many_components:
            print(f"構成品が多いまとめ商品（3個以上）:")
            for code, count in sorted(many_components, key=lambda x: x[1], reverse=True)[:5]:
                print(f"  {code}: {count}個")
        
    except Exception as e:
        print(f"まとめ商品分析エラー: {str(e)}")

def analyze_inventory():
    """在庫データ分析"""
    print(f"\n=== 在庫データ分析 ===")
    
    try:
        result = supabase.table('inventory').select('*').execute()
        inventory = result.data
        
        if not inventory:
            print("在庫データが見つかりません")
            return
        
        print(f"在庫レコード総数: {len(inventory)}件")
        
        # プラットフォーム別在庫数
        platform_result = supabase.table('platform').select('*').execute()
        platforms = {p['id']: p['name'] for p in platform_result.data}
        
        platform_counts = Counter(inv['platform_id'] for inv in inventory if inv.get('platform_id'))
        print(f"プラットフォーム別在庫登録数:")
        for platform_id, count in platform_counts.most_common():
            platform_name = platforms.get(platform_id, f"ID:{platform_id}")
            print(f"  {platform_name}: {count}件")
        
        # 在庫状況
        stock_levels = [inv['current_stock'] for inv in inventory if inv.get('current_stock') is not None]
        if stock_levels:
            print(f"\n在庫状況:")
            print(f"  総在庫数: {sum(stock_levels)}個")
            print(f"  平均在庫: {sum(stock_levels) / len(stock_levels):.1f}個")
            print(f"  在庫0の商品: {sum(1 for stock in stock_levels if stock <= 0)}件")
            print(f"  在庫5以下の商品: {sum(1 for stock in stock_levels if stock <= 5)}件")
        
    except Exception as e:
        print(f"在庫分析エラー: {str(e)}")

def recommend_optimizations():
    """最適化提案"""
    print(f"\n=== データベース最適化提案 ===")
    
    recommendations = [
        "1. 共通コードに一意制約とフォーマット制約を追加",
        "2. 商品タイプをENUM型に変更して値を制限",
        "3. プラットフォーム固有IDの重複チェック機能を追加",
        "4. 在庫データに共通コード外部キーを追加",
        "5. 商品マスター変更履歴テーブルを追加",
        "6. 定期的なデータ整合性チェック機能を実装"
    ]
    
    for i, rec in enumerate(recommendations, 1):
        print(f"  {i}. {rec}")

if __name__ == "__main__":
    print("データベース内容分析開始...\n")
    
    analyze_product_master()
    analyze_choice_codes()
    analyze_package_components()
    analyze_inventory()
    recommend_optimizations()
    
    print("\n分析完了！")