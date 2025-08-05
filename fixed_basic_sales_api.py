#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修正版基本売上集計API - choice_codeフィルタリングを追加
"""

from supabase import create_client
from datetime import datetime, timedelta
import re
from collections import defaultdict

SUPABASE_URL = "https://equrcpeifogdrxoldkpe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ"

def get_corrected_basic_sales_summary(start_date: str = None, end_date: str = None):
    """
    修正版: choice_codeがあるデータのみを対象とした基本売上集計
    """
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # デフォルト期間設定
    if not end_date:
        end_date = datetime.now().strftime('%Y-%m-%d')
    if not start_date:
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    
    print(f"=== 修正版基本売上集計 ({start_date} ~ {end_date}) ===")
    
    # choice_codeがある注文のみ取得（選択肢分析と同じ条件）
    query = supabase.table('order_items').select('*, orders!inner(created_at)').gte('orders.created_at', start_date).lte('orders.created_at', end_date).not_.is_('choice_code', 'null').neq('choice_code', '')
    response = query.execute()
    items = response.data if response.data else []
    
    print(f"choice_code付き注文商品数: {len(items)}件")
    
    # 共通コード別売上集計
    common_code_sales = defaultdict(lambda: {
        'common_code': '',
        'product_name': '',
        'quantity': 0,
        'total_amount': 0,
        'orders_count': 0,
        'choice_codes': set()
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
            # choice_codeから商品コード（R05, R13等）を抽出
            extracted_codes = re.findall(r'R\d{2,}', choice_code)
            
            for code in extracted_codes:
                # choice_code_mappingテーブルでJSONB検索
                try:
                    mapping_response = supabase.table("choice_code_mapping").select("common_code, product_name").contains("choice_info", {"choice_code": code}).execute()
                    
                    if mapping_response.data:
                        common_code = mapping_response.data[0].get('common_code')
                        product_name = mapping_response.data[0].get('product_name', '')
                        
                        # 共通コード単位で集計（common_codeがなくてもマッピング成功とみなす）
                        if common_code:
                            common_code_sales[common_code]['common_code'] = common_code
                            common_code_sales[common_code]['product_name'] = product_name
                            common_code_sales[common_code]['quantity'] += quantity
                            common_code_sales[common_code]['total_amount'] += sales_amount
                            common_code_sales[common_code]['orders_count'] += 1
                            common_code_sales[common_code]['choice_codes'].add(code)
                            mapped_any = True
                        else:
                            # common_codeがなくてもcodeで集計
                            common_code_sales[code]['common_code'] = code
                            common_code_sales[code]['product_name'] = product_name or f'商品 ({code})'
                            common_code_sales[code]['quantity'] += quantity
                            common_code_sales[code]['total_amount'] += sales_amount
                            common_code_sales[code]['orders_count'] += 1
                            common_code_sales[code]['choice_codes'].add(code)
                            mapped_any = True
                except Exception as e:
                    print(f"Error mapping {code}: {e}")
                    continue
        
        if mapped_any:
            mapped_items += 1
        else:
            unmapped_items += 1
    
    # 結果をリスト化（売上順）
    sales_list = []
    for data in common_code_sales.values():
        # choice_codesをリストに変換
        data['choice_codes'] = list(data['choice_codes'])
        sales_list.append(data)
    
    sales_list.sort(key=lambda x: x['total_amount'], reverse=True)
    
    # 統計表示
    success_rate = (mapped_items / (mapped_items + unmapped_items) * 100) if (mapped_items + unmapped_items) > 0 else 0
    total_sales = sum(item['total_amount'] for item in sales_list)
    total_quantity = sum(item['quantity'] for item in sales_list)
    
    print(f"マッピング成功: {mapped_items}件")
    print(f"マッピング失敗: {unmapped_items}件")
    print(f"成功率: {success_rate:.1f}%")
    print(f"総売上: {total_sales:,.0f}円")
    print(f"総数量: {total_quantity:,}個")
    print(f"商品種類: {len(sales_list)}種類")
    
    return {
        'status': 'success',
        'type': 'basic_sales_summary',
        'period': {'start_date': start_date, 'end_date': end_date},
        'summary': {
            'total_sales': total_sales,
            'total_quantity': total_quantity,
            'unique_products': len(sales_list),
            'mapping_success_rate': success_rate
        },
        'products': sales_list
    }

if __name__ == "__main__":
    # 修正版テスト
    result = get_corrected_basic_sales_summary('2025-08-01', '2025-08-04')
    
    print(f"\n=== 修正結果 ===")
    print(f"成功率: {result['summary']['mapping_success_rate']:.1f}%")
    print(f"総売上: {result['summary']['total_sales']:,.0f}円")
    
    if result['summary']['mapping_success_rate'] >= 95:
        print("✅ 成功: 在庫管理レベルの成功率を達成しました！")
    else:
        print("❌ まだ問題があります")