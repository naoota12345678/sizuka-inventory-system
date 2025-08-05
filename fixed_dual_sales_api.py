#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修正版売上分析API - choice_code_mappingテーブルを正しく使用
"""

from supabase import create_client
from datetime import datetime, timedelta
import re
from collections import defaultdict

SUPABASE_URL = "https://equrcpeifogdrxoldkpe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ"

def get_fixed_basic_sales_summary(start_date: str = None, end_date: str = None):
    """
    修正版: choice_code_mappingテーブルを使った基本売上集計
    """
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # デフォルト期間設定
    if not end_date:
        end_date = datetime.now().strftime('%Y-%m-%d')
    if not start_date:
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    
    print(f"=== 修正版基本売上集計 ({start_date} ~ {end_date}) ===")
    
    # order_itemsから商品データを取得
    query = supabase.table('order_items').select('*, orders!inner(created_at)').gte('orders.created_at', start_date).lte('orders.created_at', end_date)
    response = query.execute()
    items = response.data if response.data else []
    
    print(f"対象注文商品数: {len(items)}件")
    
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
                # choice_code_mappingテーブルで共通コード取得
                mapping_response = supabase.table("choice_code_mapping").select("common_code, product_name").eq("choice_code", code).execute()
                
                if mapping_response.data:
                    common_code = mapping_response.data[0].get('common_code')
                    product_name = mapping_response.data[0].get('product_name', '')
                    
                    # 共通コード単位で集計
                    if common_code:
                        common_code_sales[common_code]['common_code'] = common_code
                        common_code_sales[common_code]['product_name'] = product_name
                        common_code_sales[common_code]['quantity'] += quantity
                        common_code_sales[common_code]['total_amount'] += sales_amount
                        common_code_sales[common_code]['orders_count'] += 1
                        common_code_sales[common_code]['choice_codes'].add(code)
                        mapped_any = True
        
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
    
    print("\n商品別売上TOP5:")
    for i, product in enumerate(sales_list[:5], 1):
        choice_str = ', '.join(product['choice_codes'][:3])
        print(f"{i}. {product['common_code']} - {product['product_name']}")
        print(f"   売上: {product['total_amount']:,.0f}円, 数量: {product['quantity']}個")
        print(f"   含まれる選択肢: {choice_str}")
    
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

def get_fixed_choice_detail_analysis(start_date: str = None, end_date: str = None):
    """
    修正版: choice_code_mappingテーブルを使った選択肢詳細分析
    """
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # デフォルト期間設定
    if not end_date:
        end_date = datetime.now().strftime('%Y-%m-%d')
    if not start_date:
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    
    print(f"\n=== 修正版選択肢詳細分析 ({start_date} ~ {end_date}) ===")
    
    # choice_codeがある注文のみ取得
    query = supabase.table('order_items').select('*, orders!inner(created_at)').gte('orders.created_at', start_date).lte('orders.created_at', end_date).not_.is_('choice_code', 'null').neq('choice_code', '')
    response = query.execute()
    items = response.data if response.data else []
    
    print(f"選択肢付き注文: {len(items)}件")
    
    # choice_code別集計
    choice_sales = defaultdict(lambda: {
        'choice_code': '',
        'common_code': '',
        'product_name': '',
        'quantity': 0,
        'total_amount': 0,
        'orders_count': 0
    })
    
    for item in items:
        choice_code = item.get('choice_code', '')
        quantity = item.get('quantity', 0)
        price = item.get('price', 0)
        
        # choice_codeから商品コード（R05, R13等）を抽出
        extracted_codes = re.findall(r'R\d{2,}', choice_code)
        
        for code in extracted_codes:
            # choice_code_mappingテーブルから商品情報取得
            mapping_response = supabase.table("choice_code_mapping").select("common_code, product_name").eq("choice_code", code).execute()
            
            if mapping_response.data:
                common_code = mapping_response.data[0].get('common_code', code)
                product_name = mapping_response.data[0].get('product_name', code)
            else:
                common_code = code
                product_name = f'未登録商品 ({code})'
            
            # choice_code別に集計
            choice_sales[code]['choice_code'] = code
            choice_sales[code]['common_code'] = common_code
            choice_sales[code]['product_name'] = product_name
            choice_sales[code]['quantity'] += quantity
            choice_sales[code]['total_amount'] += price * quantity
            choice_sales[code]['orders_count'] += 1
    
    # 人気順でソート
    choice_list = list(choice_sales.values())
    choice_list.sort(key=lambda x: x['quantity'], reverse=True)
    
    total_choice_sales = sum(item['total_amount'] for item in choice_list)
    total_choice_quantity = sum(item['quantity'] for item in choice_list)
    
    print(f"選択肢別売上: {total_choice_sales:,.0f}円")
    print(f"選択肢別数量: {total_choice_quantity:,}個")
    print(f"選択肢種類: {len(choice_list)}種類")
    
    print("\n人気選択肢TOP10:")
    for i, choice in enumerate(choice_list[:10], 1):
        print(f"{i:2d}. {choice['choice_code']} ({choice['common_code']}) - {choice['product_name']}")
        print(f"     数量: {choice['quantity']}個, 売上: {choice['total_amount']:,.0f}円")
    
    return {
        'status': 'success',
        'type': 'choice_detail_analysis',
        'period': {'start_date': start_date, 'end_date': end_date},
        'summary': {
            'total_sales': total_choice_sales,
            'total_quantity': total_choice_quantity,
            'unique_choices': len(choice_list)
        },
        'choices': choice_list
    }

if __name__ == "__main__":
    # テスト実行
    print("=== 修正版売上API テスト ===")
    
    # 基本売上集計
    basic_result = get_fixed_basic_sales_summary('2025-08-01', '2025-08-04')
    
    # 選択肢詳細分析
    choice_result = get_fixed_choice_detail_analysis('2025-08-01', '2025-08-04')
    
    print(f"\n=== 結果比較 ===")
    print(f"基本売上: {basic_result['summary']['total_sales']:,.0f}円 (成功率: {basic_result['summary']['mapping_success_rate']:.1f}%)")
    print(f"選択肢売上: {choice_result['summary']['total_sales']:,.0f}円")