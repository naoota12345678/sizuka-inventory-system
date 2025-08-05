#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
在庫管理98% vs 売上API42%の差の原因調査
"""

from supabase import create_client
import re

SUPABASE_URL = "https://equrcpeifogdrxoldkpe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ"

def investigate_mapping_gap():
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    print("=== 在庫管理98% vs 売上API42%の原因調査 ===\n")
    
    # 1. choice_code_mappingテーブルの全容確認
    print("【1】choice_code_mappingテーブルの状況")
    print("-" * 50)
    
    mapping_query = supabase.table("choice_code_mapping").select("*").execute()
    mapping_data = mapping_query.data if mapping_query.data else []
    
    print(f"choice_code_mappingテーブル総件数: {len(mapping_data)}件")
    
    # common_codeの有無確認
    valid_mappings = 0
    invalid_mappings = 0
    
    print("\n登録済みマッピング（最初の10件）:")
    for i, mapping in enumerate(mapping_data[:10]):
        choice_info = mapping.get('choice_info', {})
        common_code = mapping.get('common_code')
        
        if isinstance(choice_info, dict):
            choice_code = choice_info.get('choice_code', 'unknown')
        else:
            choice_code = 'unknown'
        
        if common_code:
            valid_mappings += 1
            print(f"  OK: {choice_code} → {common_code}")
        else:
            invalid_mappings += 1
            print(f"  NG: {choice_code} → common_code is None")
    
    print(f"\n有効マッピング: {valid_mappings}件")
    print(f"無効マッピング: {invalid_mappings}件")
    
    # 2. 実際の売上データのRコード分析
    print(f"\n【2】売上データのRコード分析")
    print("-" * 50)
    
    # choice_code付きの売上データ取得
    sales_query = supabase.table('order_items').select('choice_code').not_.is_('choice_code', 'null').neq('choice_code', '').limit(100).execute()
    sales_data = sales_query.data if sales_query.data else []
    
    print(f"choice_code付き売上データサンプル: {len(sales_data)}件")
    
    # Rコード抽出と頻度分析
    r_code_frequency = {}
    
    for item in sales_data:
        choice_code = item.get('choice_code', '')
        extracted_codes = re.findall(r'R\d{2,}', choice_code)
        
        for code in extracted_codes:
            r_code_frequency[code] = r_code_frequency.get(code, 0) + 1
    
    # 頻度順でソート
    sorted_r_codes = sorted(r_code_frequency.items(), key=lambda x: x[1], reverse=True)
    
    print(f"\n売上データ内のRコード頻度TOP10:")
    mapped_count = 0
    unmapped_count = 0
    
    for i, (r_code, frequency) in enumerate(sorted_r_codes[:10], 1):
        # choice_code_mappingで確認
        mapping_check = supabase.table("choice_code_mapping").select("common_code").contains("choice_info", {"choice_code": r_code}).execute()
        
        if mapping_check.data and mapping_check.data[0].get('common_code'):
            status = "✅ 登録済み"
            mapped_count += 1
        else:
            status = "❌ 未登録"
            unmapped_count += 1
        
        print(f"  {i:2d}. {r_code}: {frequency}回 - {status}")
    
    print(f"\nTOP10のうち登録済み: {mapped_count}/10")
    print(f"TOP10のうち未登録: {unmapped_count}/10")
    
    # 3. 在庫管理との比較
    print(f"\n【3】在庫管理システムとの比較")
    print("-" * 50)
    
    print("在庫管理が98%成功する理由の仮説:")
    print("1. 在庫管理は異なるマッピングテーブルを使用している")
    print("2. 在庫管理は異なるデータセットを使用している") 
    print("3. 在庫管理のRコード抽出ロジックが異なる")
    print("4. choice_code_mappingに必要なデータが不足している")
    
    # 4. 結論と推奨アクション
    print(f"\n【4】結論と推奨アクション")
    print("-" * 50)
    
    if unmapped_count > mapped_count:
        print("❌ 問題: 人気のRコードが多数未登録")
        print("   → choice_code_mappingテーブルにデータ追加が必要")
        print("   → 在庫管理で使用しているマッピングデータを確認・移行する")
    elif valid_mappings < 50:
        print("❌ 問題: choice_code_mappingテーブルのデータ不足")
        print("   → 147件の在庫管理マッピングをchoice_code_mappingに移行する")
    else:
        print("❓ 別の原因: マッピングデータは十分だが他に問題がある")
        print("   → 在庫管理システムのロジックを詳細調査する")

if __name__ == "__main__":
    investigate_mapping_gap()