#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
CM091の商品名を正確に修正
"""

from supabase import create_client
from datetime import datetime, timezone

SUPABASE_URL = 'https://equrcpeifogdrxoldkpe.supabase.co'
SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ'

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def fix_cm091_product_name():
    print('=' * 60)
    print('CM091商品名を正確に修正')
    print('=' * 60)
    
    # CM091の現在の商品名確認
    print('\nCM091の現在の状況確認...')
    current = supabase.table('inventory').select('*').eq('common_code', 'CM091').execute()
    if current.data:
        current_data = current.data[0]
        print(f'現在: {current_data.get("product_name")} - 在庫: {current_data.get("current_stock")}個')
        
        # 正確な商品名に修正
        correct_name = 'ちび袋 ひとくちサーモン 10g'
        
        update_result = supabase.table('inventory').update({
            'product_name': correct_name,
            'last_updated': datetime.now(timezone.utc).isoformat()
        }).eq('common_code', 'CM091').execute()
        
        if update_result.data:
            print(f'[完了] CM091の商品名を「{correct_name}」に修正しました')
        else:
            print('[エラー] 商品名の更新に失敗しました')
    
    # 関連するマッピングテーブルも更新
    print('\nマッピングテーブルの商品名も確認・更新...')
    
    # product_masterでCM091の商品名更新
    pm_cm091 = supabase.table('product_master').select('*').eq('common_code', 'CM091').execute()
    if pm_cm091.data:
        for item in pm_cm091.data:
            supabase.table('product_master').update({
                'product_name': 'ちび袋 ひとくちサーモン 10g'
            }).eq('id', item['id']).execute()
        print(f'[完了] product_masterの商品名を更新しました ({len(pm_cm091.data)}件)')
    
    # choice_code_mappingでCM091の商品名更新
    ccm_cm091 = supabase.table('choice_code_mapping').select('*').eq('common_code', 'CM091').execute()
    if ccm_cm091.data:
        for item in ccm_cm091.data:
            supabase.table('choice_code_mapping').update({
                'product_name': 'ちび袋 ひとくちサーモン 10g'
            }).eq('id', item['id']).execute()
        print(f'[完了] choice_code_mappingの商品名を更新しました ({len(ccm_cm091.data)}件)')
    
    # 最終確認
    print('\n=== 修正後の確認 ===')
    final = supabase.table('inventory').select('*').eq('common_code', 'CM091').execute()
    if final.data:
        item = final.data[0]
        print(f'CM091: {item.get("product_name")} - 在庫: {item.get("current_stock")}個')
        print('\n他のちび袋商品との区別が明確になりました')
    
    print('\n商品名修正が完了しました')

if __name__ == "__main__":
    fix_cm091_product_name()