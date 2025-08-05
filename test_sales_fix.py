#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修正後の売上集計テスト
"""

from supabase import create_client

url = 'https://equrcpeifogdrxoldkpe.supabase.co'
key = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ'
supabase = create_client(url, key)

print('=== 修正後の売上集計テスト（2025年7月） ===\n')

# order_itemsから直接2025年7月31日以降のデータを集計（実際のデータ期間に合わせる）
query = supabase.table('order_items').select('*, orders!inner(created_at)').gte('orders.created_at', '2025-07-31')

response = query.execute()
items = response.data if response.data else []

print(f'2025年7月の注文商品数: {len(items)}件\n')

# 商品別集計
product_sales = {}
total_sales = 0

for item in items:
    product_code = item.get('product_code', 'unknown')
    quantity = item.get('quantity', 0)
    price = item.get('price', 0)
    sales_amount = price * quantity
    total_sales += sales_amount
    
    if product_code not in product_sales:
        # product_masterからマッピング情報を取得
        if product_code != 'unknown':
            master_response = supabase.table('product_master').select('common_code, product_name').eq('rakuten_sku', product_code).limit(1).execute()
            if master_response.data:
                common_code = master_response.data[0].get('common_code', f'UNMAPPED_{product_code}')
                mapped_name = master_response.data[0].get('product_name', item.get('product_name', '不明'))
            else:
                common_code = f'UNMAPPED_{product_code}'
                mapped_name = item.get('product_name', '不明')
        else:
            common_code = 'UNKNOWN'
            mapped_name = item.get('product_name', '不明')
        
        product_sales[product_code] = {
            'product_code': product_code,
            'common_code': common_code,
            'product_name': mapped_name,
            'quantity': 0,
            'total_amount': 0
        }
    
    product_sales[product_code]['quantity'] += quantity
    product_sales[product_code]['total_amount'] += sales_amount

print(f'7月の売上合計: {total_sales:,.0f}円\n')

# 上位5商品を表示
sorted_products = sorted(product_sales.values(), key=lambda x: x['total_amount'], reverse=True)[:5]

print('商品別売上TOP5（修正後）:')
for i, product in enumerate(sorted_products, 1):
    print(f'{i}. 【{product["common_code"]}】{product["product_name"]}')
    print(f'   売上: {product["total_amount"]:,.0f}円, 数量: {product["quantity"]}個')
    print()

print('\n=== マッピング成功商品の例 ===')
mapped_products = [p for p in product_sales.values() if not p['common_code'].startswith('UNMAPPED_')]
print(f'マッピング成功商品数: {len(mapped_products)}件')

if mapped_products:
    print('成功例:')
    for product in mapped_products[:3]:
        print(f'  {product["product_code"]} → {product["common_code"]} ({product["product_name"]})')