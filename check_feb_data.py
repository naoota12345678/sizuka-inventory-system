#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
2025年2月10日以降のデータ処理状況確認
"""

from supabase import create_client

url = 'https://equrcpeifogdrxoldkpe.supabase.co'
key = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ'
supabase = create_client(url, key)

print('=== 2025年2月10日以降のデータ処理状況 ===\n')

# 1. 注文データの状況
orders = supabase.table('orders').select('count', count='exact').gte('created_at', '2025-02-10').execute()
items = supabase.table('order_items').select('count', count='exact').gte('created_at', '2025-02-10').execute()

print(f'2/10以降の注文数: {orders.count}件')
print(f'2/10以降の商品数: {items.count}件\n')

# 2. 売上集計テスト（修正後のロジック）
query = supabase.table('order_items').select('*, orders!inner(created_at)').gte('orders.created_at', '2025-02-10')
response = query.execute()
items_data = response.data if response.data else []

total_sales = 0
mapped_count = 0
unmapped_count = 0
product_codes = set()

for item in items_data:
    quantity = item.get('quantity', 0) 
    price = item.get('price', 0)
    total_sales += price * quantity
    
    product_code = item.get('product_code', 'unknown')
    product_codes.add(product_code)
    
    if product_code != 'unknown':
        # マッピング確認
        master_response = supabase.table('product_master').select('common_code').eq('rakuten_sku', product_code).limit(1).execute()
        if master_response.data:
            mapped_count += 1
        else:
            unmapped_count += 1

print(f'2/10以降の売上合計: {total_sales:,.0f}円')
print(f'マッピング成功: {mapped_count}件')
print(f'マッピング失敗: {unmapped_count}件')
mapping_rate = (mapped_count / (mapped_count + unmapped_count) * 100) if (mapped_count + unmapped_count) > 0 else 0
print(f'マッピング率: {mapping_rate:.1f}%')
print(f'ユニーク商品コード数: {len(product_codes)}種類\n')

# 3. 月別売上推移
monthly_sales = {}
for item in items_data:
    order_data = item.get('orders', {})
    created_at = order_data.get('created_at', '')
    if created_at:
        month = created_at[:7]  # YYYY-MM
        quantity = item.get('quantity', 0)
        price = item.get('price', 0)
        
        if month not in monthly_sales:
            monthly_sales[month] = 0
        monthly_sales[month] += price * quantity

print('月別売上推移:')
for month in sorted(monthly_sales.keys()):
    print(f'  {month}: {monthly_sales[month]:,.0f}円')

# 4. 商品コードサンプル確認
print(f'\n商品コードサンプル（最初の10個）:')
sample_codes = list(product_codes)[:10]
for code in sample_codes:
    if code != 'unknown':
        # マッピング状況確認
        master_response = supabase.table('product_master').select('common_code, product_name').eq('rakuten_sku', code).limit(1).execute()
        if master_response.data:
            common_code = master_response.data[0].get('common_code', 'N/A')
            product_name = master_response.data[0].get('product_name', 'N/A')
            print(f'  {code} → {common_code} ({product_name[:30]}...)')
        else:
            print(f'  {code} → 未マッピング')
    else:
        print(f'  {code} → 商品コード不明')

print('\n=== データ処理問題の確認 ===')

# 5. 最近の注文データサンプル
recent_items = supabase.table('order_items').select('*').order('created_at', desc=True).limit(5).execute()
print(f'最新の注文商品5件:')
for i, item in enumerate(recent_items.data, 1):
    print(f'  {i}. 商品コード: {item.get("product_code", "N/A")}')
    print(f'     商品名: {item.get("product_name", "N/A")}')
    print(f'     価格: {item.get("price", 0)}円')
    print(f'     数量: {item.get("quantity", 0)}個')
    print(f'     作成日: {item.get("created_at", "N/A")}')
    print()