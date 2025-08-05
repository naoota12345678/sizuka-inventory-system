#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
シンプルな売上APIテスト
"""
import sys
import os
sys.stdout.reconfigure(encoding='utf-8')

from dual_sales_api import get_basic_sales_summary, get_choice_detail_analysis

def test_apis():
    print("=== 売上API テスト ===")
    
    # 最近3日間のデータでテスト
    start_date = '2025-08-01'
    end_date = '2025-08-04' 
    
    print(f"期間: {start_date} ~ {end_date}")
    
    # 基本売上集計テスト
    print("\n1. 基本売上集計テスト")
    basic_result = get_basic_sales_summary(start_date, end_date)
    
    if basic_result['status'] == 'success':
        summary = basic_result['summary']
        print(f"基本売上: {summary['total_sales']:,.0f}円")
        print(f"商品種類: {summary['unique_products']}種類")  
        print(f"成功率: {summary['mapping_success_rate']:.1f}%")
    else:
        print(f"エラー: {basic_result.get('message', '不明')}")
    
    # 選択肢分析テスト
    print("\n2. 選択肢分析テスト")  
    choice_result = get_choice_detail_analysis(start_date, end_date)
    
    if choice_result['status'] == 'success':
        summary = choice_result['summary']
        print(f"選択肢売上: {summary['total_sales']:,.0f}円")
        print(f"選択肢種類: {summary['unique_choices']}種類")
    else:
        print(f"エラー: {choice_result.get('message', '不明')}")

if __name__ == "__main__":
    test_apis()