#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
売上システムと在庫システムのマッピング成功率比較テスト
"""

from final_fixed_sales_api import get_final_basic_sales_summary, get_final_choice_detail_analysis
import sys
sys.stdout.reconfigure(encoding='utf-8')

def test_sales_vs_inventory():
    print("=== 売上システム vs 在庫システム マッピング成功率比較 ===\n")
    
    # テスト期間設定（最近1週間）
    start_date = '2025-07-28'
    end_date = '2025-08-04'
    
    print(f"テスト期間: {start_date} ~ {end_date}\n")
    
    # 1. 基本売上集計テスト
    print("【1】基本売上集計（choice_code → common_code マッピング）")
    print("-" * 60)
    
    basic_result = get_final_basic_sales_summary(start_date, end_date)
    
    if basic_result['status'] == 'success':
        summary = basic_result['summary']
        success_rate = summary['mapping_success_rate']
        
        print(f"\n【結果】")
        print(f"  マッピング成功率: {success_rate:.1f}%")
        print(f"  総売上: {summary['total_sales']:,.0f}円")
        print(f"  商品種類: {summary['unique_products']}種類")
        
        # 成功率評価
        if success_rate >= 95:
            print(f"  評価: ✅ 優秀 (在庫管理レベル)")
        elif success_rate >= 80:
            print(f"  評価: ⚠️  改善余地あり")
        else:
            print(f"  評価: ❌ 要修正")
            
    else:
        print(f"❌ APIエラー: {basic_result.get('message')}")
    
    print("\n" + "=" * 80 + "\n")
    
    # 2. 選択肢詳細分析テスト
    print("【2】選択肢詳細分析（個別Rコードの人気分析）")
    print("-" * 60)
    
    choice_result = get_final_choice_detail_analysis(start_date, end_date)
    
    if choice_result['status'] == 'success':
        summary = choice_result['summary']
        total_choices = summary['unique_choices']
        mapped_choices = sum(1 for choice in choice_result['choices'] if not choice['product_name'].startswith('未登録商品'))
        choice_success_rate = (mapped_choices / total_choices * 100) if total_choices > 0 else 0
        
        print(f"\n【結果】")
        print(f"  選択肢マッピング成功率: {choice_success_rate:.1f}%")
        print(f"  選択肢総売上: {summary['total_sales']:,.0f}円")
        print(f"  選択肢種類: {total_choices}種類")
        print(f"  マッピング済み選択肢: {mapped_choices}種類")
        print(f"  未登録選択肢: {total_choices - mapped_choices}種類")
        
        # 人気TOP5の登録状況
        print(f"\n  人気選択肢TOP5の登録状況:")
        for i, choice in enumerate(choice_result['choices'][:5], 1):
            status = "✅" if not choice['product_name'].startswith('未登録商品') else "❌"
            print(f"    {i}. {status} {choice['choice_code']}: {choice['product_name'][:30]}")
            print(f"       売上: {choice['total_amount']:,.0f}円 ({choice['quantity']}個)")
            
    else:
        print(f"❌ APIエラー: {choice_result.get('message')}")
    
    print("\n" + "=" * 80 + "\n")
    
    # 3. 在庫管理との比較評価
    print("【3】在庫管理システムとの比較評価")
    print("-" * 60)
    
    if 'basic_result' in locals() and basic_result['status'] == 'success':
        sales_success_rate = basic_result['summary']['mapping_success_rate']
        expected_rate = 98.0  # 在庫管理の成功率
        
        print(f"在庫管理成功率: {expected_rate:.1f}%")
        print(f"売上集計成功率: {sales_success_rate:.1f}%")
        print(f"差分: {abs(expected_rate - sales_success_rate):.1f}ポイント")
        
        if sales_success_rate >= 95:
            print(f"\n✅ 結論: 売上システムは在庫管理と同レベルで正常動作しています")
        elif sales_success_rate >= 50:
            print(f"\n⚠️  結論: choice_code_mappingテーブルのデータ不足が原因です")
            print(f"   → 在庫管理で使用されている147件のマッピングが売上側で不足している可能性")
        else:
            print(f"\n❌ 結論: システムに問題があります。追加調査が必要です")
    
    print("\n" + "=" * 80)
    print("テスト完了")

if __name__ == "__main__":
    test_sales_vs_inventory()