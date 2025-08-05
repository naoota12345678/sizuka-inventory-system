#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
楽天SKUコード（4桁）とproduct_code（8桁）の関係確認
"""

from supabase import create_client

url = 'https://equrcpeifogdrxoldkpe.supabase.co'
key = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ'
supabase = create_client(url, key)

print('=== 楽天SKUコード（4桁）とproduct_code（8桁）の関係確認 ===\n')

# 1. product_masterの楽天SKU（4桁）を確認
print('1. product_masterの楽天SKU（4桁）:')
pm_4digit = supabase.table('product_master').select('rakuten_sku, common_code, product_name').not_.is_('rakuten_sku', 'null').execute()

# 4桁のSKUをフィルタ
four_digit_skus = []
for item in pm_4digit.data:
    sku = str(item.get('rakuten_sku', ''))
    if len(sku) <= 5 and sku.isdigit():  # 4桁または5桁の数字
        four_digit_skus.append(item)

print(f'   4-5桁の楽天SKU数: {len(four_digit_skus)}')
print('   サンプル:')
for item in four_digit_skus[:5]:
    print(f'     {item["rakuten_sku"]} → {item["common_code"]} ({item["product_name"][:30]}...)')

# 2. order_itemsの8桁product_code
print('\n2. order_itemsの8桁product_code:')
items_8digit = supabase.table('order_items').select('product_code').like('product_code', '10000%').execute()

eight_digit_codes = set()
for item in items_8digit.data:
    code = item.get('product_code', '')
    if code.startswith('10000') and len(code) == 8:
        eight_digit_codes.add(code)

print(f'   8桁（10000XXX）の商品コード数: {len(eight_digit_codes)}')
print('   サンプル:')
for code in list(eight_digit_codes)[:5]:
    print(f'     {code}')

# 3. 4桁と8桁の変換規則を推定
print('\n3. 4桁→8桁の変換規則推定:')
print('   例: 楽天SKU「59」→ product_code「10000059」?')

# 実際にテスト
test_mappings = []
matches_found = 0

for item in four_digit_skus[:10]:
    sku_4digit = str(item['rakuten_sku'])
    # 8桁に変換（10000 + 0埋め3桁）
    predicted_8digit = f'10000{sku_4digit.zfill(3)}'
    
    # 実際の注文データにあるかチェック
    exists = predicted_8digit in eight_digit_codes
    if exists:
        matches_found += 1
    
    test_mappings.append({
        '4digit': sku_4digit,
        '8digit_predicted': predicted_8digit,
        'exists_in_orders': exists,
        'common_code': item['common_code']
    })

print('   変換テスト結果:')
for mapping in test_mappings:
    status = 'OK' if mapping['exists_in_orders'] else 'NG'
    print(f'     {mapping["4digit"]} → {mapping["8digit_predicted"]} ({mapping["common_code"]}) [{status}]')

print(f'\n   マッチ率: {matches_found}/10 = {matches_found/10*100:.1f}%')

# 4. 逆パターンも確認（8桁→4桁）
print('\n4. 8桁→4桁の逆変換確認:')
reverse_matches = 0
sku_4digit_set = set(str(item['rakuten_sku']) for item in four_digit_skus)

for code_8digit in list(eight_digit_codes)[:10]:
    # 10000XXXから末尾3桁を取得してint変換
    if code_8digit.startswith('10000'):
        suffix = code_8digit[5:]  # 末尾3桁
        predicted_4digit = str(int(suffix))  # ゼロ埋めを除去
        
        # product_masterに存在するかチェック
        exists = predicted_4digit in sku_4digit_set
        if exists:
            reverse_matches += 1
        
        status = 'OK' if exists else 'NG'
        print(f'     {code_8digit} → 楽天SKU「{predicted_4digit}」予測 [{status}]')

print(f'\n   逆変換マッチ率: {reverse_matches}/10 = {reverse_matches/10*100:.1f}%')

# 5. 実際にマッピングが成功している例を探す
print('\n5. 実際のマッピング成功例:')
success_examples = []

for code_8digit in list(eight_digit_codes):
    if code_8digit.startswith('10000'):
        suffix = code_8digit[5:]
        predicted_4digit = str(int(suffix))
        
        # product_masterで確認
        for item in four_digit_skus:
            if str(item['rakuten_sku']) == predicted_4digit:
                success_examples.append({
                    '8digit': code_8digit,
                    '4digit': predicted_4digit,
                    'common_code': item['common_code'],
                    'product_name': item['product_name']
                })
                break

print(f'   成功例数: {len(success_examples)}')
for example in success_examples[:5]:
    print(f'     {example["8digit"]} ↔ {example["4digit"]} → {example["common_code"]} ({example["product_name"][:30]}...)')

# 6. 問題のまとめ
print('\n=== 問題のまとめ ===')
print(f'1. product_masterの楽天SKU: {len(four_digit_skus)}種類（4-5桁）')
print(f'2. 実際の注文商品コード: {len(eight_digit_codes)}種類（8桁）')
print(f'3. 変換可能な商品: {len(success_examples)}種類')
print(f'4. 変換率: {len(success_examples)/len(eight_digit_codes)*100:.1f}%')

if len(success_examples) < len(eight_digit_codes) * 0.5:
    print('\n⚠️  警告: 変換率が低いため、売上集計でマッピングが失敗している')
    print('   対策: 8桁商品コードでもproduct_masterを検索できるようにする')