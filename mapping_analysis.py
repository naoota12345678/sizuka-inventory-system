#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
マッピング状況の詳細分析
"""

from supabase import create_client

url = 'https://equrcpeifogdrxoldkpe.supabase.co'
key = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ'
supabase = create_client(url, key)

print('=== マッピング状況の詳細確認 ===\n')

# product_masterに実際に登録されている楽天SKU
pm_skus = supabase.table('product_master').select('rakuten_sku').not_.is_('rakuten_sku', 'null').execute()
registered_skus = set(item['rakuten_sku'] for item in pm_skus.data if item.get('rakuten_sku'))

print(f'product_masterに登録されている楽天SKU数: {len(registered_skus)}')

# 実際の注文で使われている商品コード（上位20）
items = supabase.table('order_items').select('product_code').gte('created_at', '2025-02-10').execute()
used_codes = {}
for item in items.data:
    code = item.get('product_code', 'unknown')
    if code != 'unknown':
        used_codes[code] = used_codes.get(code, 0) + 1

# 使用頻度順でソート
sorted_codes = sorted(used_codes.items(), key=lambda x: x[1], reverse=True)[:20]

print('\n注文で使用されている商品コードTOP20:')
for code, count in sorted_codes:
    is_mapped = code in registered_skus
    status = 'マッピング済み' if is_mapped else '未マッピング'
    print(f'  {code}: {count}回使用 → {status}')

print(f'\n=== マッピングの問題分析 ===')
mapped_in_orders = sum(1 for code, _ in sorted_codes if code in registered_skus)
print(f'TOP20中のマッピング済み: {mapped_in_orders}/20')

# 楽天SKUのパターン確認
print('\nproduct_masterのSKUパターンサンプル:')
for sku in list(registered_skus)[:10]:
    print(f'  {sku}')

print('\n実際の注文のコードパターンサンプル:')
for code, _ in sorted_codes[:10]:
    print(f'  {code}')

print('\n=== マッピング成功例と失敗例 ===')
success_examples = []
failure_examples = []

for code, count in sorted_codes[:10]:
    if code in registered_skus:
        # マッピング情報取得
        mapping = supabase.table('product_master').select('common_code, product_name').eq('rakuten_sku', code).execute()
        if mapping.data:
            success_examples.append({
                'code': code,
                'common_code': mapping.data[0].get('common_code'),
                'product_name': mapping.data[0].get('product_name', '')[:50] + '...',
                'count': count
            })
    else:
        failure_examples.append({'code': code, 'count': count})

print('マッピング成功例:')
for example in success_examples[:5]:
    print(f'  {example["code"]} → {example["common_code"]} ({example["product_name"]}) [{example["count"]}回使用]')

print('\nマッピング失敗例（未登録商品）:')
for example in failure_examples[:5]:
    print(f'  {example["code"]} → 未登録 [{example["count"]}回使用]')

# 統計サマリー
total_orders = sum(count for _, count in sorted_codes)
mapped_orders = sum(count for code, count in sorted_codes if code in registered_skus)
print(f'\n=== 統計サマリー ===')
print(f'総注文回数（TOP20）: {total_orders}回')
print(f'マッピング済み注文: {mapped_orders}回')
print(f'実質マッピング率: {(mapped_orders / total_orders * 100):.1f}%')