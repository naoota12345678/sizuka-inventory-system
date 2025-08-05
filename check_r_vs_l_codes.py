#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RコードとLコードの違いを調査
"""

from supabase import create_client
import re

SUPABASE_URL = "https://equrcpeifogdrxoldkpe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ"

def check_code_types():
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    print("=== RコードとLコードの違い調査 ===\n")
    
    # 1. choice_code_mappingに登録されているコードタイプ
    print("【1】choice_code_mappingに登録されているコードタイプ")
    print("-" * 60)
    
    mapping_query = supabase.table("choice_code_mapping").select("choice_info").execute()
    mapping_data = mapping_query.data if mapping_query.data else []
    
    code_types = {'R': 0, 'L': 0, 'M': 0, 'その他': 0}
    all_mapped_codes = []
    
    for mapping in mapping_data:
        choice_info = mapping.get('choice_info', {})
        if isinstance(choice_info, dict):
            choice_code = choice_info.get('choice_code', '')
            all_mapped_codes.append(choice_code)
            
            if choice_code.startswith('R'):
                code_types['R'] += 1
            elif choice_code.startswith('L'):
                code_types['L'] += 1
            elif choice_code.startswith('M'):
                code_types['M'] += 1
            else:
                code_types['その他'] += 1
    
    print("choice_code_mappingに登録されているコードタイプ:")
    for code_type, count in code_types.items():
        print(f"  {code_type}コード: {count}件")
    
    # Rコードのリスト
    r_codes_in_mapping = [code for code in all_mapped_codes if code.startswith('R')]
    print(f"\n登録済みRコード（最初の10件）:")
    for code in r_codes_in_mapping[:10]:
        print(f"  {code}")
    
    # 2. 売上データで使用されているコードタイプ
    print(f"\n【2】売上データで使用されているコードタイプ")
    print("-" * 60)
    
    sales_query = supabase.table('order_items').select('choice_code').not_.is_('choice_code', 'null').neq('choice_code', '').limit(200).execute()
    sales_data = sales_query.data if sales_query.data else []
    
    sales_code_frequency = {}
    
    for item in sales_data:
        choice_code = item.get('choice_code', '')
        # R, L, Mコードを抽出
        all_codes = re.findall(r'[RLM]\d{2,}', choice_code)
        
        for code in all_codes:
            sales_code_frequency[code] = sales_code_frequency.get(code, 0) + 1
    
    # 売上データのコードタイプ分析
    sales_code_types = {'R': 0, 'L': 0, 'M': 0, 'その他': 0}
    
    for code in sales_code_frequency.keys():
        if code.startswith('R'):
            sales_code_types['R'] += 1
        elif code.startswith('L'):
            sales_code_types['L'] += 1
        elif code.startswith('M'):
            sales_code_types['M'] += 1
        else:
            sales_code_types['その他'] += 1
    
    print("売上データで使用されているコードタイプ:")
    for code_type, count in sales_code_types.items():
        print(f"  {code_type}コード: {count}種類")
    
    # 3. 人気コードの登録状況確認
    print(f"\n【3】人気コードの登録状況")
    print("-" * 60)
    
    sorted_sales_codes = sorted(sales_code_frequency.items(), key=lambda x: x[1], reverse=True)
    
    print("売上データ人気コードTOP15の登録状況:")
    registered_count = 0
    unregistered_count = 0
    
    for i, (code, frequency) in enumerate(sorted_sales_codes[:15], 1):
        if code in all_mapped_codes:
            status = "OK"
            registered_count += 1
        else:
            status = "NG"
            unregistered_count += 1
        
        print(f"  {i:2d}. [{status}] {code}: {frequency}回")
    
    print(f"\nTOP15のうち:")
    print(f"  登録済み: {registered_count}件")
    print(f"  未登録: {unregistered_count}件")
    print(f"  登録率: {registered_count/15*100:.1f}%")
    
    # 4. 結論
    print(f"\n【4】問題の特定")
    print("-" * 60)
    
    if unregistered_count > registered_count:
        print("❌ 問題発見: 人気のあるコードが多数未登録")
        print("   → 売上データで使用される頻度の高いコードがchoice_code_mappingに不足")
        print("   → これが42%成功率の原因です")
    else:
        print("✅ 登録状況は良好")
        print("   → 別の原因を調査する必要があります")
    
    # 5. 修正提案
    print(f"\n【5】修正提案")
    print("-" * 60)
    print("未登録の人気コードをchoice_code_mappingに追加することで")
    print("成功率を42% → 90%以上に改善できる可能性があります")

if __name__ == "__main__":
    check_code_types()