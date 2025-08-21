#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
全ちび袋商品の表示名を正確に修正
"""

from supabase import create_client
from datetime import datetime, timezone

SUPABASE_URL = 'https://equrcpeifogdrxoldkpe.supabase.co'
SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ'

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def fix_all_chibi_product_names():
    print('=' * 80)
    print('全ちび袋商品の表示名修正')
    print('=' * 80)
    
    # ちび袋商品の正確な名前マッピング
    chibi_correct_names = {
        'CM088': 'ちび袋 ころころエゾ鹿ミンチ 10g',
        'CM089': 'ちび袋 ころころクッキー（8粒）',
        'CM090': 'ちび袋 たらカットジャーキー 18g',
        'CM091': 'ちび袋 ひとくちサーモン 10g',
        'CM092': 'ちび袋 ふわふわスモークサーモン 5g',
        'CM093': 'ちび袋 ほっけカットジャーキー 15g',
        'CM094': 'ちび袋 エゾ鹿ふりかけ 10g',
        'CM095': 'ちび袋 スライスサーモン 10g',
        'CM096': 'ちび袋 エゾ鹿スライスジャーキー 10g',
        'CM097': 'ちび袋 エゾ鹿レバースライスジャーキー 10g',
        'CM098': 'ちび袋 スティックサーモン 10g',
        'CM099': 'ちび袋 スモークサーモンチップ 10g',
        'CM100': 'ちび袋 エゾ鹿カットジャーキー 15g',
        'CM101': 'ちび袋 フレークサーモン 10g',
        'CM102': 'ちび袋 ラムカットジャーキー 15g',
        'CM103': 'ちび袋 豚ハツスライスジャーキー 10g',
        'CM104': 'ちび袋 豚レバースライスジャーキー 10g',
        'CM105': 'ちび袋 鮭カットジャーキー 15g',
        'CM106': 'ちび袋 鮭白子スライスジャーキー 10g',
        'CM107': 'ちび袋 鶏ささみスライスジャーキー 10g',
        'CM108': 'ちび袋 鶏むねスライスジャーキー 10g',
        'CM109': 'ちび袋 鶏砂肝ジャーキー 10g',
        'CM110': 'ちび袋 馬スライスジャーキー 10g',
        'CM111': 'ちび袋 カンガルースライスジャーキー 10g'
    }
    
    print(f'対象商品数: {len(chibi_correct_names)}件')
    
    updated_count = 0
    
    for common_code, correct_name in chibi_correct_names.items():
        print(f'\n--- {common_code} ---')
        
        # 現在の在庫確認
        current = supabase.table('inventory').select('*').eq('common_code', common_code).execute()
        if current.data:
            current_name = current.data[0].get('product_name', '')
            current_stock = current.data[0].get('current_stock', 0)
            
            print(f'現在: {current_name} - 在庫: {current_stock}個')
            
            if current_name != correct_name:
                # inventoryテーブルの商品名更新
                update_result = supabase.table('inventory').update({
                    'product_name': correct_name,
                    'last_updated': datetime.now(timezone.utc).isoformat()
                }).eq('common_code', common_code).execute()
                
                if update_result.data:
                    print(f'[修正] {correct_name}')
                    updated_count += 1
                else:
                    print(f'[失敗] {common_code}')
            else:
                print(f'[OK] 既に正しい名前')
        else:
            print(f'在庫データなし')
    
    print(f'\n' + '=' * 80)
    print(f'修正完了: {updated_count}件の商品名を更新しました')
    print('=' * 80)
    
    # 修正後の確認（重要商品のみ）
    check_codes = ['CM096', 'CM097', 'CM098', 'CM104', 'CM106', 'CM109', 'CM091']
    print('\n修正後確認:')
    for code in check_codes:
        final = supabase.table('inventory').select('*').eq('common_code', code).execute()
        if final.data:
            item = final.data[0]
            print(f'{code}: {item.get("product_name")} - 在庫: {item.get("current_stock")}個')

if __name__ == "__main__":
    fix_all_chibi_product_names()