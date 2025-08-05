#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基本売上集計と選択肢分析のロジック比較デバッグ
"""

from supabase import create_client
import re

SUPABASE_URL = "https://equrcpeifogdrxoldkpe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ"

def debug_mapping_difference():
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    print("=== 基本売上集計 vs 選択肢分析の違いを特定 ===\n")
    
    # 同じ期間、同じデータで比較
    start_date = '2025-08-01'
    end_date = '2025-08-04'
    
    # 同じクエリでデータ取得
    query = supabase.table('order_items').select('*, orders!inner(created_at)').gte('orders.created_at', start_date).lte('orders.created_at', end_date)
    response = query.execute()
    items = response.data if response.data else []
    
    print(f"対象データ: {len(items)}件")
    
    # サンプルデータ分析（最初の10件）
    print("\n=== サンプルデータ分析（最初の10件）===")
    
    basic_mapped = 0
    choice_mapped = 0
    debug_items = []
    
    for i, item in enumerate(items[:10]):
        choice_code = item.get('choice_code', '')
        quantity = item.get('quantity', 0)
        price = item.get('price', 0)
        
        print(f"\n【アイテム {i+1}】")
        print(f"  choice_code: '{choice_code}'")
        print(f"  quantity: {quantity}, price: {price}")
        
        if choice_code:
            extracted_codes = re.findall(r'R\d{2,}', choice_code)
            print(f"  抽出されたRコード: {extracted_codes}")
            
            # 基本売上集計のロジック（common_codeが必要）
            basic_success = False
            for code in extracted_codes:
                try:
                    mapping_response = supabase.table("choice_code_mapping").select("common_code, product_name").contains("choice_info", {"choice_code": code}).execute()
                    
                    if mapping_response.data:
                        common_code = mapping_response.data[0].get('common_code')
                        product_name = mapping_response.data[0].get('product_name', '')
                        
                        print(f"    {code} → common_code: '{common_code}', product_name: '{product_name}'")
                        
                        # ここが重要：common_codeがある場合のみカウント
                        if common_code:
                            basic_success = True
                            print(f"    基本売上集計: ✅ カウント")
                        else:
                            print(f"    基本売上集計: ❌ common_codeがNone")
                    else:
                        print(f"    {code} → マッピングなし")
                        
                except Exception as e:
                    print(f"    {code} → エラー: {e}")
            
            # 選択肢分析のロジック（common_codeがなくてもカウント）
            choice_success = len(extracted_codes) > 0
            
            print(f"  基本売上集計結果: {'✅' if basic_success else '❌'}")
            print(f"  選択肢分析結果: {'✅' if choice_success else '❌'}")
            
            if basic_success:
                basic_mapped += 1
            if choice_success:
                choice_mapped += 1
                
            debug_items.append({
                'choice_code': choice_code,
                'extracted_codes': extracted_codes,
                'basic_success': basic_success,
                'choice_success': choice_success
            })
    
    print(f"\n=== サンプル結果 ===")
    print(f"基本売上集計成功: {basic_mapped}/10 = {basic_mapped/10*100:.1f}%")
    print(f"選択肢分析成功: {choice_mapped}/10 = {choice_mapped/10*100:.1f}%")
    
    # 問題の特定
    print(f"\n=== 問題分析 ===")
    
    # choice_code_mappingテーブルのcommon_code状況確認
    print("choice_code_mappingテーブルのcommon_code状況:")
    mapping_check = supabase.table("choice_code_mapping").select("choice_info, common_code, product_name").limit(10).execute()
    
    none_count = 0
    valid_count = 0
    
    if mapping_check.data:
        for mapping in mapping_check.data:
            common_code = mapping.get('common_code')
            choice_info = mapping.get('choice_info', {})
            choice_code = choice_info.get('choice_code', 'unknown') if isinstance(choice_info, dict) else 'unknown'
            
            if common_code:
                valid_count += 1
                print(f"  ✅ {choice_code} → {common_code}")
            else:
                none_count += 1
                print(f"  ❌ {choice_code} → common_code is None")
    
    print(f"\nchoice_code_mappingテーブル分析:")
    print(f"  有効なcommon_code: {valid_count}件")
    print(f"  None/空のcommon_code: {none_count}件")
    
    if none_count > valid_count:
        print(f"\n🚨 問題発見: choice_code_mappingテーブルの多くのレコードでcommon_codeがNoneまたは空です")
        print(f"   → これが基本売上集計の成功率が低い原因です")
        print(f"   → 選択肢分析はcommon_codeに依存しないため100%成功しています")
    else:
        print(f"\n❓ choice_code_mappingテーブルは正常に見えます。他の原因を調査中...")

if __name__ == "__main__":
    debug_mapping_difference()