#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修正版売上集計API - 在庫管理と同じ仕組み（choice_code → common_code）を使用
"""

from supabase import create_client
from datetime import datetime, timedelta
import re

SUPABASE_URL = "https://equrcpeifogdrxoldkpe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ"


def get_sales_by_choice_code(start_date: str = None, end_date: str = None):
    """
    choice_codeを使った売上集計（在庫管理と同じ仕組み）
    """
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # デフォルト期間設定
    if not end_date:
        end_date = datetime.now().strftime('%Y-%m-%d')
    if not start_date:
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    
    print(f"=== 修正版売上集計 ({start_date} ~ {end_date}) ===\n")
    
    # order_itemsから商品データを取得
    query = supabase.table('order_items').select('*, orders!inner(created_at)').gte('orders.created_at', start_date).lte('orders.created_at', end_date)
    response = query.execute()
    items = response.data if response.data else []
    
    print(f"対象注文商品数: {len(items)}件\n")
    
    # 商品別集計（在庫管理と同じ方式）
    product_sales = {}
    choice_code_success = 0
    product_code_success = 0
    mapping_failures = 0
    
    for item in items:
        product_code = item.get('product_code', 'unknown')
        choice_code = item.get('choice_code', '')
        quantity = item.get('quantity', 0)
        price = item.get('price', 0)
        sales_amount = price * quantity
        
        common_code = None
        mapped_name = item.get('product_name', '不明')
        mapping_method = 'none'
        
        # 方法1: choice_codeを使用（在庫管理と同じ）
        if choice_code:
            extracted_codes = re.findall(r'R\d{2,}', choice_code)
            
            if extracted_codes:
                first_code = extracted_codes[0]
                master_response = supabase.table("product_master").select("common_code, product_name").eq("rakuten_sku", first_code).execute()
                
                if master_response.data:
                    common_code = master_response.data[0].get('common_code')
                    mapped_name = master_response.data[0].get('product_name', mapped_name)
                    mapping_method = 'choice_code'
                    choice_code_success += 1
        
        # 方法2: product_codeを使用（従来の方法）
        if not common_code and product_code != 'unknown':
            master_response = supabase.table("product_master").select("common_code, product_name").eq("rakuten_sku", product_code).execute()
            if master_response.data:
                common_code = master_response.data[0].get('common_code')
                mapped_name = master_response.data[0].get('product_name', mapped_name)
                mapping_method = 'product_code'
                product_code_success += 1
        
        # 方法3: マッピング失敗
        if not common_code:
            common_code = f'UNMAPPED_{product_code}'
            mapping_method = 'failed'
            mapping_failures += 1
        
        # 集計
        if common_code not in product_sales:
            product_sales[common_code] = {
                'common_code': common_code,
                'product_name': mapped_name,
                'quantity': 0,
                'total_amount': 0,
                'orders_count': 0,
                'mapping_method': mapping_method
            }
        
        product_sales[common_code]['quantity'] += quantity
        product_sales[common_code]['total_amount'] += sales_amount
        product_sales[common_code]['orders_count'] += 1
    
    # 結果表示
    print("=== マッピング結果 ===")
    print(f"choice_code成功: {choice_code_success}件")
    print(f"product_code成功: {product_code_success}件") 
    print(f"マッピング失敗: {mapping_failures}件")
    total_items = choice_code_success + product_code_success + mapping_failures
    success_rate = (choice_code_success + product_code_success) / total_items * 100 if total_items > 0 else 0
    print(f"総合成功率: {success_rate:.1f}%\n")
    
    # 売上順でソート
    sorted_products = sorted(product_sales.values(), key=lambda x: x['total_amount'], reverse=True)
    
    print("=== 商品別売上TOP10 ===")
    for i, product in enumerate(sorted_products[:10], 1):
        method_icon = "✓" if product['mapping_method'] != 'failed' else "✗"
        print(f"{i:2d}. {method_icon} 【{product['common_code']}】{product['product_name'][:30]}...")
        print(f"     売上: {product['total_amount']:,.0f}円, 数量: {product['quantity']}個, 方法: {product['mapping_method']}")
    
    # 総計
    total_sales = sum(p['total_amount'] for p in product_sales.values())
    total_quantity = sum(p['quantity'] for p in product_sales.values())
    
    print(f"\n=== 総計 ===")
    print(f"総売上: {total_sales:,.0f}円")
    print(f"総数量: {total_quantity:,}個")
    print(f"商品種類: {len(product_sales)}種類")
    
    return {
        'status': 'success',
        'period': {'start_date': start_date, 'end_date': end_date},
        'summary': {
            'total_sales': total_sales,
            'total_quantity': total_quantity,
            'total_orders': len(items),
            'unique_products': len(product_sales),
            'mapping_stats': {
                'choice_code_success': choice_code_success,
                'product_code_success': product_code_success,
                'mapping_failures': mapping_failures,
                'success_rate': success_rate
            }
        },
        'products': sorted_products
    }


if __name__ == "__main__":
    # テスト実行
    result = get_sales_by_choice_code('2025-07-31', '2025-08-04')
    print(f"\n=== APIレスポンス例 ===")
    print(f"ステータス: {result['status']}")
    print(f"期間: {result['period']['start_date']} ~ {result['period']['end_date']}")
    print(f"総売上: {result['summary']['total_sales']:,.0f}円")
    print(f"成功率: {result['summary']['mapping_stats']['success_rate']:.1f}%")