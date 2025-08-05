#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
シンプル売上集計API - 商品別売上（選択肢詳細は別途分析）
"""

from supabase import create_client
from datetime import datetime, timedelta
import re

SUPABASE_URL = "https://equrcpeifogdrxoldkpe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ"


def get_sales_summary(start_date: str = None, end_date: str = None):
    """
    基本売上集計 - 商品別
    """
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # デフォルト期間設定
    if not end_date:
        end_date = datetime.now().strftime('%Y-%m-%d')
    if not start_date:
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    
    print(f"=== 売上集計 ({start_date} ~ {end_date}) ===")
    
    # order_itemsから商品データを取得
    query = supabase.table('order_items').select('*, orders!inner(created_at)').gte('orders.created_at', start_date).lte('orders.created_at', end_date)
    response = query.execute()
    items = response.data if response.data else []
    
    print(f"対象注文商品数: {len(items)}件")
    
    # 商品別集計（product_codeベース）
    product_sales = {}
    mapped_count = 0
    unmapped_count = 0
    
    for item in items:
        product_code = item.get('product_code', 'unknown')
        quantity = item.get('quantity', 0)
        price = item.get('price', 0)
        sales_amount = price * quantity
        
        # product_masterでマッピング確認
        common_code = None
        mapped_name = item.get('product_name', '不明')
        
        if product_code != 'unknown':
            # 8桁コード → 4桁変換を試行
            if product_code.startswith('10000') and len(product_code) == 8:
                # 10000059 → 59 のような変換
                suffix = product_code[5:]  # 末尾3桁
                predicted_4digit = str(int(suffix))  # ゼロ埋めを除去
                
                # 4桁でproduct_masterを検索
                master_response = supabase.table("product_master").select("common_code, product_name").eq("rakuten_sku", predicted_4digit).execute()
                if master_response.data:
                    common_code = master_response.data[0].get('common_code')
                    mapped_name = master_response.data[0].get('product_name', mapped_name)
                    mapped_count += 1
                else:
                    # 元の8桁でも試行
                    master_response = supabase.table("product_master").select("common_code, product_name").eq("rakuten_sku", product_code).execute()
                    if master_response.data:
                        common_code = master_response.data[0].get('common_code')
                        mapped_name = master_response.data[0].get('product_name', mapped_name) 
                        mapped_count += 1
            else:
                # 4桁などの短いコード
                master_response = supabase.table("product_master").select("common_code, product_name").eq("rakuten_sku", product_code).execute()
                if master_response.data:
                    common_code = master_response.data[0].get('common_code')
                    mapped_name = master_response.data[0].get('product_name', mapped_name)
                    mapped_count += 1
        
        if not common_code:
            common_code = f'UNMAPPED_{product_code}'
            unmapped_count += 1
        
        # 集計
        if common_code not in product_sales:
            product_sales[common_code] = {
                'common_code': common_code,
                'product_code': product_code,
                'product_name': mapped_name,
                'quantity': 0,
                'total_amount': 0,
                'orders_count': 0
            }
        
        product_sales[common_code]['quantity'] += quantity
        product_sales[common_code]['total_amount'] += sales_amount
        product_sales[common_code]['orders_count'] += 1
    
    # 結果表示
    success_rate = (mapped_count / (mapped_count + unmapped_count) * 100) if (mapped_count + unmapped_count) > 0 else 0
    print(f"マッピング成功: {mapped_count}件")
    print(f"マッピング失敗: {unmapped_count}件") 
    print(f"成功率: {success_rate:.1f}%")
    
    # 売上順でソート
    sorted_products = sorted(product_sales.values(), key=lambda x: x['total_amount'], reverse=True)
    
    print("\\n=== 商品別売上TOP10 ===")
    for i, product in enumerate(sorted_products[:10], 1):
        is_mapped = not product['common_code'].startswith('UNMAPPED_')
        status = 'OK' if is_mapped else 'NG'
        print(f"{i:2d}. [{status}] {product['common_code']} - {product['product_name'][:30]}...")
        print(f"     売上: {product['total_amount']:,.0f}円, 数量: {product['quantity']}個")
    
    # 総計
    total_sales = sum(p['total_amount'] for p in product_sales.values())
    total_quantity = sum(p['quantity'] for p in product_sales.values())
    
    print(f"\\n=== 総計 ===")
    print(f"総売上: {total_sales:,.0f}円")
    print(f"総数量: {total_quantity:,}個")
    print(f"商品種類: {len(product_sales)}種類")
    
    return {
        'status': 'success',
        'period': {'start_date': start_date, 'end_date': end_date},
        'summary': {
            'total_sales': total_sales,
            'total_quantity': total_quantity,
            'unique_products': len(product_sales),
            'mapping_success_rate': success_rate
        },
        'products': sorted_products[:20]  # TOP20を返却
    }


def get_choice_analysis(start_date: str = None, end_date: str = None):
    """
    選択肢分析 - どの選択肢が人気か
    """
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # デフォルト期間設定
    if not end_date:
        end_date = datetime.now().strftime('%Y-%m-%d')
    if not start_date:
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    
    print(f"\\n=== 選択肢分析 ({start_date} ~ {end_date}) ===")
    
    # choice_codeがある注文のみ取得
    query = supabase.table('order_items').select('*, orders!inner(created_at)').gte('orders.created_at', start_date).lte('orders.created_at', end_date).not_.is_('choice_code', 'null').neq('choice_code', '')
    response = query.execute()
    items = response.data if response.data else []
    
    print(f"選択肢付き注文: {len(items)}件")
    
    # 選択肢別集計
    choice_sales = {}
    
    for item in items:
        choice_code = item.get('choice_code', '')
        quantity = item.get('quantity', 0)
        price = item.get('price', 0)
        
        if choice_code:
            # R05, R13等を抽出
            extracted_codes = re.findall(r'R\\d{2,}', choice_code)
            
            for code in extracted_codes:
                if code not in choice_sales:
                    # product_masterから商品名取得
                    master_response = supabase.table("product_master").select("common_code, product_name").eq("rakuten_sku", code).execute()
                    if master_response.data:
                        product_name = master_response.data[0].get('product_name', code)
                        common_code = master_response.data[0].get('common_code', code)
                    else:
                        product_name = code
                        common_code = code
                    
                    choice_sales[code] = {
                        'choice_code': code,
                        'common_code': common_code,
                        'product_name': product_name,
                        'quantity': 0,
                        'total_amount': 0
                    }
                
                choice_sales[code]['quantity'] += quantity
                choice_sales[code]['total_amount'] += price * quantity
    
    # 人気順でソート
    sorted_choices = sorted(choice_sales.values(), key=lambda x: x['quantity'], reverse=True)
    
    print("\\n=== 人気選択肢TOP10 ===")
    for i, choice in enumerate(sorted_choices[:10], 1):
        print(f"{i:2d}. {choice['choice_code']} ({choice['common_code']}) - {choice['product_name'][:30]}...")
        print(f"     数量: {choice['quantity']}個, 売上: {choice['total_amount']:,.0f}円")
    
    return sorted_choices


if __name__ == "__main__":
    # 基本売上集計
    result = get_sales_summary('2025-07-31', '2025-08-04')
    
    # 選択肢分析
    choice_result = get_choice_analysis('2025-07-31', '2025-08-04')