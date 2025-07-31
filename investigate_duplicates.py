#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
重複データの詳細調査
JANコード重複の原因を特定し、名寄せデータの整合性を確認
"""

import os
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.database import supabase

def investigate_jan_duplicates():
    """JANコード重複の詳細調査"""
    print("=== JANコード重複調査 ===\n")
    
    try:
        # 全商品データ取得
        result = supabase.table('product_master').select('*').execute()
        products = result.data
        
        if not products:
            print("商品データが見つかりません")
            return
        
        # JANコードが設定されている商品のみ抽出
        jan_products = []
        for p in products:
            jan = p.get('jan_code')
            if jan and str(jan).strip():
                jan_products.append({
                    'common_code': p['common_code'],
                    'product_name': p['product_name'],
                    'jan_code': str(jan).strip(),
                    'product_type': p.get('product_type', ''),
                    'rakuten_sku': p.get('rakuten_sku', ''),
                    'colorme_id': p.get('colorme_id', ''),
                    'smaregi_id': p.get('smaregi_id', '')
                })
        
        print(f"JANコードが設定されている商品: {len(jan_products)}件")
        
        # JANコード別にグループ化
        jan_groups = defaultdict(list)
        for product in jan_products:
            jan_groups[product['jan_code']].append(product)
        
        # 重複しているJANコードを特定
        duplicate_jans = {jan: products for jan, products in jan_groups.items() if len(products) > 1}
        
        print(f"重複しているJANコード: {len(duplicate_jans)}件\n")
        
        if duplicate_jans:
            print("=== 重複JANコードの詳細 ===")
            for jan, products in duplicate_jans.items():
                print(f"\nJANコード: {jan} ({len(products)}件の重複)")
                for i, product in enumerate(products, 1):
                    print(f"  {i}. 共通コード: {product['common_code']}")
                    print(f"     商品名: {product['product_name']}")
                    print(f"     商品タイプ: {product['product_type']}")
                    print(f"     楽天SKU: {product['rakuten_sku']}")
                    print(f"     カラーミーID: {product['colorme_id']}")
                    print(f"     スマレジID: {product['smaregi_id']}")
                
                # 重複の原因を推定
                analyze_duplicate_cause(products)
                print("-" * 50)
        
        return duplicate_jans
        
    except Exception as e:
        print(f"エラー: {str(e)}")
        return {}

def analyze_duplicate_cause(products):
    """重複の原因を分析"""
    print("     【重複の原因分析】")
    
    # 商品名が同じか確認
    product_names = [p['product_name'] for p in products]
    if len(set(product_names)) == 1:
        print("     → 同一商品の可能性（商品名が同一）")
    else:
        print("     → 異なる商品の可能性（商品名が異なる）")
        for name in set(product_names):
            print(f"       - {name}")
    
    # 商品タイプが同じか確認
    product_types = [p['product_type'] for p in products]
    if len(set(product_types)) == 1:
        print(f"     → 商品タイプは統一（{product_types[0]}）")
    else:
        print("     → 商品タイプが混在")
        for ptype in set(product_types):
            print(f"       - {ptype}")
    
    # プラットフォーム別ID確認
    platforms = ['rakuten_sku', 'colorme_id', 'smaregi_id']
    for platform in platforms:
        platform_ids = [p[platform] for p in products if p[platform]]
        if len(platform_ids) > 1 and len(set(platform_ids)) > 1:
            print(f"     → {platform}が異なる: {set(platform_ids)}")

def investigate_common_code_duplicates():
    """共通コード重複の調査"""
    print("\n=== 共通コード重複調査 ===\n")
    
    try:
        result = supabase.table('product_master').select('common_code', 'product_name').execute()
        products = result.data
        
        common_codes = [p['common_code'] for p in products if p['common_code']]
        code_counts = Counter(common_codes)
        
        duplicates = [code for code, count in code_counts.items() if count > 1]
        
        if duplicates:
            print(f"重複している共通コード: {len(duplicates)}件")
            for code in duplicates:
                matching_products = [p for p in products if p['common_code'] == code]
                print(f"\n共通コード: {code} ({len(matching_products)}件)")
                for product in matching_products:
                    print(f"  - {product['product_name']}")
        else:
            print("✅ 共通コードに重複はありません")
        
    except Exception as e:
        print(f"エラー: {str(e)}")

def investigate_product_name_duplicates():
    """商品名重複の調査"""
    print("\n=== 商品名重複調査 ===\n")
    
    try:
        result = supabase.table('product_master').select('common_code', 'product_name', 'product_type').execute()
        products = result.data
        
        # 商品名でグループ化（空白や大文字小文字を正規化）
        name_groups = defaultdict(list)
        for product in products:
            name = product.get('product_name', '').strip()
            if name:
                normalized_name = name.lower().replace(' ', '').replace('　', '')
                name_groups[normalized_name].append(product)
        
        # 重複している商品名
        duplicate_names = {name: products for name, products in name_groups.items() if len(products) > 1}
        
        if duplicate_names:
            print(f"重複している商品名: {len(duplicate_names)}件")
            for name, products in list(duplicate_names.items())[:5]:  # 最初の5件のみ表示
                print(f"\n正規化後商品名: {name} ({len(products)}件)")
                for product in products:
                    print(f"  共通コード: {product['common_code']}")
                    print(f"  元の商品名: {product['product_name']}")
                    print(f"  商品タイプ: {product['product_type']}")
                    print()
        else:
            print("✅ 商品名に重複はありません")
        
    except Exception as e:
        print(f"エラー: {str(e)}")

def check_nameよせ_integrity():
    """名寄せデータの整合性チェック"""
    print("\n=== 名寄せデータ整合性チェック ===\n")
    
    try:
        # 商品マスター
        products_result = supabase.table('product_master').select('common_code', 'product_name').execute()
        products = {p['common_code']: p['product_name'] for p in products_result.data}
        
        # 選択肢コード対応表
        choice_result = supabase.table('choice_code_mapping').select('choice_code', 'common_code').execute()
        choice_mappings = choice_result.data
        
        # まとめ商品内訳
        package_result = supabase.table('package_components').select('package_code', 'component_code').execute()
        package_components = package_result.data
        
        issues = []
        
        # 選択肢コードの整合性チェック
        print("選択肢コード整合性:")
        orphan_choices = 0
        for choice in choice_mappings:
            common_code = choice.get('common_code')
            if common_code and common_code not in products:
                orphan_choices += 1
        
        if orphan_choices > 0:
            issues.append(f"商品マスターに存在しない共通コードを参照する選択肢コード: {orphan_choices}件")
        else:
            print("✅ 選択肢コードの整合性OK")
        
        # まとめ商品内訳の整合性チェック
        print("\nまとめ商品内訳整合性:")
        orphan_packages = 0
        orphan_components = 0
        
        for component in package_components:
            package_code = component.get('package_code')
            component_code = component.get('component_code')
            
            if package_code and package_code not in products:
                orphan_packages += 1
            if component_code and component_code not in products:
                orphan_components += 1
        
        if orphan_packages > 0:
            issues.append(f"存在しないまとめ商品コード: {orphan_packages}件")
        if orphan_components > 0:
            issues.append(f"存在しない構成品コード: {orphan_components}件")
        
        if orphan_packages == 0 and orphan_components == 0:
            print("✅ まとめ商品内訳の整合性OK")
        
        # サマリー
        if issues:
            print(f"\n発見された整合性の問題:")
            for issue in issues:
                print(f"  ❌ {issue}")
        else:
            print(f"\n✅ 名寄せデータの整合性に問題はありません")
        
    except Exception as e:
        print(f"エラー: {str(e)}")

def suggest_cleanup_actions(duplicate_jans):
    """クリーンアップのアクション提案"""
    print("\n=== データクリーンアップ提案 ===\n")
    
    if duplicate_jans:
        print("JANコード重複の解決方法:")
        print("1. 同一商品の場合:")
        print("   → より詳細な共通コードに統合")
        print("   → 古いレコードを削除")
        print("2. 異なる商品の場合:")
        print("   → JANコードを修正")
        print("   → 商品名を明確化")
        
        print("\n自動修正可能な項目:")
        auto_fixable = []
        manual_required = []
        
        for jan, products in duplicate_jans.items():
            product_names = [p['product_name'] for p in products]
            if len(set(product_names)) == 1:
                auto_fixable.append(jan)
            else:
                manual_required.append(jan)
        
        print(f"  自動修正可能: {len(auto_fixable)}件（同一商品名）")
        print(f"  手動確認必要: {len(manual_required)}件（商品名が異なる）")
        
        if auto_fixable:
            print(f"\n自動修正候補のJANコード: {auto_fixable[:3]}...")
    
    print("\n推奨クリーンアップ手順:")
    print("1. Google SheetsとDBの同期を実行")
    print("2. 重複JANコードを手動で確認・修正")
    print("3. 整合性チェックを再実行")
    print("4. 在庫データに共通コード参照を追加")

if __name__ == "__main__":
    print("名寄せデータ重複調査開始...\n")
    
    duplicate_jans = investigate_jan_duplicates()
    investigate_common_code_duplicates()
    investigate_product_name_duplicates()
    check_nameよせ_integrity()
    suggest_cleanup_actions(duplicate_jans)
    
    print("\n調査完了！")