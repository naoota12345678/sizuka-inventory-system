#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
CM018/CM091の在庫商品名修正
"""

from supabase import create_client
from datetime import datetime, timezone

SUPABASE_URL = 'https://equrcpeifogdrxoldkpe.supabase.co'
SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ'

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def fix_inventory_names():
    print('=' * 60)
    print('CM018/CM091 在庫商品名修正')
    print('=' * 60)
    
    # CM091の商品名を修正
    print('\nCM091の商品名を「ちび袋」関連に修正...')
    
    # 現在のCM091データ確認
    current = supabase.table('inventory').select('*').eq('common_code', 'CM091').execute()
    if current.data:
        current_data = current.data[0]
        print(f'現在: {current_data.get("product_name")} - 在庫: {current_data.get("current_stock")}個')
        
        # 商品名を修正
        update_result = supabase.table('inventory').update({
            'product_name': 'ちび袋（10g詰め合わせ）',
            'last_updated': datetime.now(timezone.utc).isoformat()
        }).eq('common_code', 'CM091').execute()
        
        if update_result.data:
            print('[完了] CM091の商品名を「ちび袋（10g詰め合わせ）」に修正しました')
    
    # CM018の商品名も確認・修正
    print('\nCM018の商品名確認...')
    cm018 = supabase.table('inventory').select('*').eq('common_code', 'CM018').execute()
    if cm018.data:
        current_name = cm018.data[0].get('product_name')
        print(f'現在: {current_name}')
        
        # スマレジID_10017は正しくない可能性があるので修正
        if 'スマレジ' in str(current_name) or '10017' in str(current_name):
            correct_name = 'ひとくちサーモン 30g'
            
            update_result = supabase.table('inventory').update({
                'product_name': correct_name,
                'last_updated': datetime.now(timezone.utc).isoformat()
            }).eq('common_code', 'CM018').execute()
            
            if update_result.data:
                print(f'[完了] CM018の商品名を「{correct_name}」に修正しました')
    
    # 最終確認
    print('\n=== 修正後の在庫状況 ===')
    final_cm018 = supabase.table('inventory').select('*').eq('common_code', 'CM018').execute()
    final_cm091 = supabase.table('inventory').select('*').eq('common_code', 'CM091').execute()
    
    if final_cm018.data:
        item = final_cm018.data[0]
        print(f'CM018: {item.get("product_name")} - 在庫: {item.get("current_stock")}個')
    
    if final_cm091.data:
        item = final_cm091.data[0]
        print(f'CM091: {item.get("product_name")} - 在庫: {item.get("current_stock")}個')
    
    print('\n商品名の修正が完了しました')

if __name__ == "__main__":
    fix_inventory_names()