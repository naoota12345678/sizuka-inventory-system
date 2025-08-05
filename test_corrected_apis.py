#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修正後のAPIテスト - 在庫管理と同じ98%成功率の検証
"""

from supabase import create_client
from datetime import datetime, timedelta
import re
from collections import defaultdict

SUPABASE_URL = "https://equrcpeifogdrxoldkpe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ"

def test_corrected_basic_sales_api():
    """修正版基本売上集計APIのテスト（main_cloudrun.pyの修正を反映）"""
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    start_date = '2025-08-01'
    end_date = '2025-08-04'
    
    print("=== 修正後基本売上集計APIテスト ===")
    print(f"期間: {start_date} ~ {end_date}")
    
    # 修正されたクエリ（choice_codeがあるデータのみ）
    query = supabase.table('order_items').select('*, orders!inner(created_at)').gte('orders.created_at', start_date).lte('orders.created_at', end_date).not_.is_('choice_code', 'null').neq('choice_code', '')
    response = query.execute()
    items = response.data if response.data else []
    
    print(f"choice_code付き注文数: {len(items)}件")
    
    # 共通コード別売上集計
    common_code_sales = defaultdict(lambda: {
        'common_code': '',
        'product_name': '',
        'quantity': 0,
        'total_amount': 0,
        'orders_count': 0
    })
    
    mapped_items = 0
    unmapped_items = 0
    
    for item in items:
        choice_code = item.get('choice_code', '')
        quantity = item.get('quantity', 0)
        price = item.get('price', 0)
        sales_amount = price * quantity
        
        mapped_any = False
        
        if choice_code:
            extracted_codes = re.findall(r'R\d{2,}', choice_code)
            
            for code in extracted_codes:
                try:
                    mapping_response = supabase.table("choice_code_mapping").select("common_code, product_name").contains("choice_info", {"choice_code": code}).execute()
                    
                    if mapping_response.data:
                        common_code = mapping_response.data[0].get('common_code')
                        product_name = mapping_response.data[0].get('product_name', '')
                        
                        if common_code:
                            common_code_sales[common_code]['common_code'] = common_code
                            common_code_sales[common_code]['product_name'] = product_name
                            common_code_sales[common_code]['quantity'] += quantity
                            common_code_sales[common_code]['total_amount'] += sales_amount
                            common_code_sales[common_code]['orders_count'] += 1
                            mapped_any = True
                except Exception as e:
                    continue
        
        if mapped_any:
            mapped_items += 1
        else:
            unmapped_items += 1
    
    # 統計計算
    success_rate = (mapped_items / (mapped_items + unmapped_items) * 100) if (mapped_items + unmapped_items) > 0 else 0
    total_sales = sum(item['total_amount'] for item in common_code_sales.values())
    total_quantity = sum(item['quantity'] for item in common_code_sales.values())
    
    print(f"\n=== 修正後基本売上集計結果 ===")
    print(f"マッピング成功: {mapped_items}件")
    print(f"マッピング失敗: {unmapped_items}件")
    print(f"成功率: {success_rate:.1f}%")
    print(f"総売上: {total_sales:,.0f}円")
    print(f"商品種類: {len(common_code_sales)}種類")
    
    return success_rate, total_sales, len(common_code_sales)

def test_choice_analysis_comparison():
    """選択肢詳細分析との比較"""
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    start_date = '2025-08-01'
    end_date = '2025-08-04'
    
    print(f"\n=== 選択肢詳細分析（比較用） ===")
    
    # choice_codeがある注文のみ取得
    query = supabase.table('order_items').select('*, orders!inner(created_at)').gte('orders.created_at', start_date).lte('orders.created_at', end_date).not_.is_('choice_code', 'null').neq('choice_code', '')
    response = query.execute()
    items = response.data if response.data else []
    
    choice_sales = defaultdict(lambda: {
        'choice_code': '',
        'quantity': 0,
        'total_amount': 0
    })
    
    total_choice_items = len(items)
    mapped_choice_items = 0
    
    for item in items:
        choice_code = item.get('choice_code', '')
        quantity = item.get('quantity', 0)
        price = item.get('price', 0)
        
        if choice_code:
            extracted_codes = re.findall(r'R\d{2,}', choice_code)
            if extracted_codes:
                mapped_choice_items += 1
                
                for code in extracted_codes:
                    choice_sales[code]['choice_code'] = code
                    choice_sales[code]['quantity'] += quantity
                    choice_sales[code]['total_amount'] += price * quantity
    
    choice_success_rate = (mapped_choice_items / total_choice_items * 100) if total_choice_items > 0 else 0
    choice_total_sales = sum(item['total_amount'] for item in choice_sales.values())
    
    print(f"選択肢分析成功率: {choice_success_rate:.1f}%")
    print(f"選択肢総売上: {choice_total_sales:,.0f}円")
    print(f"選択肢種類: {len(choice_sales)}種類")
    
    return choice_success_rate, choice_total_sales

def main():
    print("=" * 80)
    print("修正後売上API検証テスト")
    print("=" * 80)
    
    # 基本売上集計テスト
    basic_rate, basic_sales, basic_products = test_corrected_basic_sales_api()
    
    # 選択肢分析テスト
    choice_rate, choice_sales = test_choice_analysis_comparison()
    
    print(f"\n" + "=" * 80)
    print("最終結果比較")
    print("=" * 80)
    
    print(f"基本売上集計成功率: {basic_rate:.1f}%")
    print(f"選択肢分析成功率: {choice_rate:.1f}%")
    print(f"成功率差分: {abs(basic_rate - choice_rate):.1f}ポイント")
    
    print(f"\n基本売上集計売上: {basic_sales:,.0f}円")
    print(f"選択肢分析売上: {choice_sales:,.0f}円")
    
    # 評価
    print(f"\n=== 評価 ===")
    if basic_rate >= 95:
        print("✅ 優秀: 在庫管理と同レベル（98%）の成功率を達成！")
    elif basic_rate >= 80:
        print("⚠️  良好: 高い成功率だが、さらなる改善余地あり")
    elif basic_rate >= 50:
        print("❌ 不十分: choice_code_mappingの登録データ不足")
    else:
        print("❌❌ 重大問題: システムに根本的な問題あり")
    
    if abs(basic_rate - choice_rate) <= 5:
        print("✅ 一貫性: 基本売上集計と選択肢分析の成功率が一致")
    else:
        print("❌ 不一致: まだロジックに問題がある可能性")
    
    return basic_rate >= 95 and abs(basic_rate - choice_rate) <= 5

if __name__ == "__main__":
    success = main()
    print(f"\n{'='*80}")
    if success:
        print("🎉 修正成功: 売上APIが在庫管理レベルで正常動作しています")
    else:
        print("🔧 追加修正が必要です")
    print(f"{'='*80}")