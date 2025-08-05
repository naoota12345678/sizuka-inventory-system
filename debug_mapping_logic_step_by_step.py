#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
マッピングロジックの詳細デバッグ
"""

from supabase import create_client
import re

SUPABASE_URL = "https://equrcpeifogdrxoldkpe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ"

def debug_step_by_step():
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    print("=== マッピングロジック詳細デバッグ ===\n")
    
    # 1個のデータで詳細にトレース
    sales_query = supabase.table('order_items').select('choice_code, quantity, price').not_.is_('choice_code', 'null').neq('choice_code', '').limit(5).execute()
    items = sales_query.data if sales_query.data else []
    
    print("=== 5件のサンプルデータで詳細トレース ===")
    
    success_count = 0
    total_count = 0
    
    for i, item in enumerate(items, 1):
        choice_code = item.get('choice_code', '')
        quantity = item.get('quantity', 0)
        price = item.get('price', 0)
        
        print(f"\n【サンプル {i}】")
        print(f"  choice_code: '{choice_code}'")
        print(f"  quantity: {quantity}, price: {price}")
        
        total_count += 1
        
        if choice_code:
            # Rコード抽出
            extracted_codes = re.findall(r'R\d{2,}', choice_code)
            print(f"  抽出されたRコード: {extracted_codes}")
            
            mapped_any = False
            
            for code in extracted_codes:
                print(f"    {code}のマッピングを確認中...")
                
                try:
                    # クエリの詳細確認
                    query_obj = supabase.table("choice_code_mapping").select("common_code, product_name, choice_info").contains("choice_info", {"choice_code": code})
                    print(f"    クエリ: choice_info contains {{'choice_code': '{code}'}}")
                    
                    mapping_response = query_obj.execute()
                    
                    if mapping_response.data:
                        result = mapping_response.data[0]
                        common_code = result.get('common_code')
                        product_name = result.get('product_name', '')
                        choice_info = result.get('choice_info', {})
                        
                        print(f"    ✅ マッピング発見:")
                        print(f"      common_code: '{common_code}'")
                        print(f"      product_name: '{product_name}'")
                        print(f"      choice_info: {choice_info}")
                        
                        # ここが重要: common_codeの条件チェック
                        if common_code:
                            print(f"    ✅ common_codeあり → カウント")
                            mapped_any = True
                        else:
                            print(f"    ❌ common_codeがNone → カウントしない")
                    else:
                        print(f"    ❌ マッピング見つからず")
                        
                except Exception as e:
                    print(f"    ❌ エラー: {e}")
            
            if mapped_any:
                print(f"  結果: ✅ SUCCESS")
                success_count += 1
            else:
                print(f"  結果: ❌ FAIL")
        else:
            print(f"  結果: ❌ choice_codeなし")
    
    print(f"\n=== サンプル結果 ===")
    print(f"成功: {success_count}/{total_count} = {success_count/total_count*100:.1f}%")
    
    # 2. 特定のRコード（R01）で詳細テスト
    print(f"\n=== R01の詳細マッピングテスト ===")
    
    test_code = "R01"
    print(f"テストコード: {test_code}")
    
    try:
        mapping_response = supabase.table("choice_code_mapping").select("*").contains("choice_info", {"choice_code": test_code}).execute()
        
        if mapping_response.data:
            result = mapping_response.data[0]
            print(f"マッピング結果: {result}")
            
            common_code = result.get('common_code')
            if common_code:
                print(f"✅ common_code: '{common_code}' → SUCCESS条件満たす")
            else:
                print(f"❌ common_code: None → SUCCESS条件満たさない")
        else:
            print(f"❌ R01のマッピングが見つからない")
            
    except Exception as e:
        print(f"❌ エラー: {e}")
    
    # 3. choice_code_mappingの全Rコードのcommon_code確認
    print(f"\n=== 全Rコードのcommon_code状況確認 ===")
    
    r_mapping_query = supabase.table("choice_code_mapping").select("choice_info, common_code").execute()
    all_mappings = r_mapping_query.data if r_mapping_query.data else []
    
    r_with_common_code = 0
    r_without_common_code = 0
    
    for mapping in all_mappings:
        choice_info = mapping.get('choice_info', {})
        common_code = mapping.get('common_code')
        
        if isinstance(choice_info, dict):
            choice_code = choice_info.get('choice_code', '')
            
            if choice_code.startswith('R'):
                if common_code:
                    r_with_common_code += 1
                else:
                    r_without_common_code += 1
                    print(f"❌ {choice_code}: common_codeがNone")
    
    print(f"Rコードのcommon_code状況:")
    print(f"  common_codeあり: {r_with_common_code}件")
    print(f"  common_codeなし: {r_without_common_code}件")
    print(f"  成功率理論値: {r_with_common_code/(r_with_common_code + r_without_common_code)*100:.1f}%")
    
    if r_without_common_code > 0:
        print(f"\n🚨 問題発見: {r_without_common_code}件のRコードでcommon_codeがNone")
        print(f"   → これが42%成功率の原因です")

if __name__ == "__main__":
    debug_step_by_step()