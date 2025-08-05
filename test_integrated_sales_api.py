#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
統合された売上APIのテスト
"""

from dual_sales_api import get_basic_sales_summary, get_choice_detail_analysis
from datetime import datetime, timedelta

def test_integrated_apis():
    """統合されたAPIをテスト"""
    print("=== 統合売上API テスト ===\n")
    
    # テスト期間設定（最近7日間）
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    
    print(f"テスト期間: {start_date} ~ {end_date}\n")
    
    # A) 基本売上集計テスト
    print("1. 基本売上集計テスト（choice_code → common_code）")
    print("-" * 50)
    
    try:
        basic_result = get_basic_sales_summary(start_date, end_date)
        
        if basic_result['status'] == 'success':
            summary = basic_result['summary']
            print(f"✓ 基本売上API成功")
            print(f"  総売上: {summary['total_sales']:,.0f}円")
            print(f"  総数量: {summary['total_quantity']:,}個")
            print(f"  商品種類: {summary['unique_products']}種類")
            print(f"  マッピング成功率: {summary['mapping_success_rate']:.1f}%")
            
            # TOP3商品表示
            print(f"\n  売上TOP3:")
            for i, product in enumerate(basic_result['products'][:3], 1):
                print(f"    {i}. {product['common_code']} - {product['product_name'][:30]}")
                print(f"       {product['total_amount']:,.0f}円 ({product['quantity']}個)")
        else:
            print(f"✗ 基本売上API失敗: {basic_result.get('message', 'Unknown error')}")
            
    except Exception as e:
        print(f"✗ 基本売上API例外: {str(e)}")
    
    print("\n" + "=" * 60 + "\n")
    
    # B) 選択肢詳細分析テスト
    print("2. 選択肢詳細分析テスト（R05, R13等の人気分析）")
    print("-" * 50)
    
    try:
        choice_result = get_choice_detail_analysis(start_date, end_date)
        
        if choice_result['status'] == 'success':
            summary = choice_result['summary']
            print(f"✓ 選択肢分析API成功")
            print(f"  選択肢売上: {summary['total_sales']:,.0f}円")
            print(f"  選択肢数量: {summary['total_quantity']:,}個")
            print(f"  選択肢種類: {summary['unique_choices']}種類")
            
            # TOP3選択肢表示
            print(f"\n  人気選択肢TOP3:")
            for i, choice in enumerate(choice_result['choices'][:3], 1):
                print(f"    {i}. {choice['choice_code']} ({choice['common_code']}) - {choice['product_name'][:30]}")
                print(f"       {choice['total_amount']:,.0f}円 ({choice['quantity']}個)")
        else:
            print(f"✗ 選択肢分析API失敗: {choice_result.get('message', 'Unknown error')}")
            
    except Exception as e:
        print(f"✗ 選択肢分析API例外: {str(e)}")
    
    print("\n" + "=" * 60 + "\n")
    
    # 統計比較
    try:
        if 'basic_result' in locals() and 'choice_result' in locals():
            if basic_result['status'] == 'success' and choice_result['status'] == 'success':
                basic_sales = basic_result['summary']['total_sales']
                choice_sales = choice_result['summary']['total_sales']
                
                print("3. 統計比較")
                print("-" * 30)
                print(f"基本売上集計: {basic_sales:,.0f}円")
                print(f"選択肢分析売上: {choice_sales:,.0f}円")
                
                if choice_sales > 0:
                    ratio = basic_sales / choice_sales * 100
                    print(f"基本/選択肢比率: {ratio:.1f}%")
                    
                    if ratio < 50:
                        print("→ 基本売上が低い: choice_codeのcommon_codeマッピングが不足している可能性")
                    elif ratio > 150:
                        print("→ 基本売上が高い: 選択肢以外のデータも含まれている")
                    else:
                        print("→ 適切な範囲: 両方のアプローチが正常に動作")
                
    except Exception as e:
        print(f"統計比較でエラー: {str(e)}")
    
    print("\n=== テスト完了 ===")

if __name__ == "__main__":
    test_integrated_apis()