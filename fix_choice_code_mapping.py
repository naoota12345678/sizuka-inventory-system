#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
選択肢コードマッピング修正スクリプト
P01、S01を正しく共通コード（CM201、CM202）に変換

問題: 在庫テーブルに選択肢コード（P01、S01）が直接保存されている
解決: 在庫テーブルのP01→CM201、S01→CM202への変換
"""

import os
import logging
from datetime import datetime, timezone
from supabase import create_client

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 環境変数設定
os.environ['SUPABASE_URL'] = 'https://equrcpeifogdrxoldkpe.supabase.co'
os.environ['SUPABASE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ'

# Supabase接続
supabase = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_KEY'])

def fix_choice_code_mapping():
    """
    在庫テーブルの選択肢コードを正しい共通コードに変換
    """
    print("=" * 60)
    print("選択肢コードマッピング修正開始")
    print("=" * 60)
    
    try:
        # Step 1: 現在の状況確認
        print("Step 1: 現在の在庫状況確認...")
        
        # 在庫テーブルの選択肢コード確認
        choice_codes_result = supabase.table('inventory').select(
            'id, common_code, current_stock, product_name'
        ).in_('common_code', ['P01', 'S01', 'S02']).execute()
        
        print(f"  選択肢コードが直接保存されている在庫: {len(choice_codes_result.data)}件")
        for item in choice_codes_result.data:
            print(f"    - {item['common_code']}: {item['current_stock']}個 ({item.get('product_name', '')})")
        
        # マッピング先の確認
        mapped_codes_result = supabase.table('inventory').select(
            'id, common_code, current_stock, product_name'
        ).in_('common_code', ['CM201', 'CM202', 'CM203']).execute()
        
        print(f"  マッピング先共通コード: {len(mapped_codes_result.data)}件")
        for item in mapped_codes_result.data:
            print(f"    - {item['common_code']}: {item['current_stock']}個 ({item.get('product_name', '')})")
        
        # Step 2: マッピング情報取得
        print("\nStep 2: choice_code_mappingからマッピング情報取得...")
        
        # P01のマッピング
        p01_mapping = supabase.table('choice_code_mapping').select(
            'common_code, product_name'
        ).filter('choice_info->>choice_code', 'eq', 'P01').execute()
        
        # S01のマッピング
        s01_mapping = supabase.table('choice_code_mapping').select(
            'common_code, product_name'
        ).filter('choice_info->>choice_code', 'eq', 'S01').execute()
        
        # S02のマッピング
        s02_mapping = supabase.table('choice_code_mapping').select(
            'common_code, product_name'
        ).filter('choice_info->>choice_code', 'eq', 'S02').execute()
        
        mapping_rules = {}
        if p01_mapping.data:
            mapping_rules['P01'] = {
                'target_code': p01_mapping.data[0]['common_code'],
                'product_name': p01_mapping.data[0]['product_name']
            }
            print(f"    P01 → {p01_mapping.data[0]['common_code']} ({p01_mapping.data[0]['product_name']})")
        
        if s01_mapping.data:
            mapping_rules['S01'] = {
                'target_code': s01_mapping.data[0]['common_code'],
                'product_name': s01_mapping.data[0]['product_name']
            }
            print(f"    S01 → {s01_mapping.data[0]['common_code']} ({s01_mapping.data[0]['product_name']})")
        
        if s02_mapping.data:
            mapping_rules['S02'] = {
                'target_code': s02_mapping.data[0]['common_code'],
                'product_name': s02_mapping.data[0]['product_name']
            }
            print(f"    S02 → {s02_mapping.data[0]['common_code']} ({s02_mapping.data[0]['product_name']})")
        
        print(f"  マッピングルール: {len(mapping_rules)}件")
        
        # Step 3: マッピング適用
        print("\nStep 3: 在庫テーブルマッピング適用...")
        
        fixed_count = 0
        merged_count = 0
        created_count = 0
        
        for choice_item in choice_codes_result.data:
            choice_code = choice_item['common_code']
            choice_stock = choice_item['current_stock'] or 0
            choice_id = choice_item['id']
            
            if choice_code not in mapping_rules:
                print(f"    警告: {choice_code}のマッピングルールが見つかりません")
                continue
            
            target_code = mapping_rules[choice_code]['target_code']
            target_name = mapping_rules[choice_code]['product_name']
            
            print(f"    処理中: {choice_code} ({choice_stock}個) → {target_code}")
            
            # マッピング先の在庫レコードが既に存在するかチェック
            target_existing = supabase.table('inventory').select(
                'id, current_stock, product_name'
            ).eq('common_code', target_code).execute()
            
            if target_existing.data:
                # マッピング先が既に存在する場合: 在庫を統合
                target_item = target_existing.data[0]
                target_current_stock = target_item['current_stock'] or 0
                new_stock = target_current_stock + choice_stock
                
                # マッピング先在庫を更新
                supabase.table('inventory').update({
                    'current_stock': new_stock,
                    'last_updated': datetime.now(timezone.utc).isoformat()
                }).eq('id', target_item['id']).execute()
                
                # 選択肢コード在庫レコードを削除
                supabase.table('inventory').delete().eq('id', choice_id).execute()
                
                print(f"      統合: {target_code} {target_current_stock} + {choice_stock} = {new_stock}個")
                merged_count += 1
                
            else:
                # マッピング先が存在しない場合: common_codeを変更
                supabase.table('inventory').update({
                    'common_code': target_code,
                    'product_name': target_name,
                    'last_updated': datetime.now(timezone.utc).isoformat()
                }).eq('id', choice_id).execute()
                
                print(f"      変換: {choice_code} → {target_code} ({choice_stock}個)")
                created_count += 1
            
            fixed_count += 1
        
        # Step 4: 修正結果確認
        print("\nStep 4: 修正結果確認...")
        
        # 修正後の選択肢コード確認
        after_choice_codes = supabase.table('inventory').select(
            'common_code, current_stock'
        ).in_('common_code', ['P01', 'S01', 'S02']).execute()
        
        # 修正後のマッピング先確認
        after_mapped_codes = supabase.table('inventory').select(
            'common_code, current_stock, product_name'
        ).in_('common_code', ['CM201', 'CM202', 'CM203']).execute()
        
        print(f"  修正後の選択肢コード在庫: {len(after_choice_codes.data)}件")
        if after_choice_codes.data:
            for item in after_choice_codes.data:
                print(f"    - {item['common_code']}: {item['current_stock']}個")
        else:
            print("    ✅ 選択肢コードは全て正しく変換されました")
        
        print(f"  修正後のマッピング先在庫: {len(after_mapped_codes.data)}件")
        for item in after_mapped_codes.data:
            print(f"    - {item['common_code']}: {item['current_stock']}個 ({item.get('product_name', '')})")
        
        print(f"\n" + "=" * 60)
        print("選択肢コードマッピング修正完了")
        print("=" * 60)
        print(f"処理したアイテム数: {fixed_count}件")
        print(f"  - 統合したアイテム: {merged_count}件")
        print(f"  - 変換したアイテム: {created_count}件")
        
        if len(after_choice_codes.data) == 0:
            print("\n✅ 全ての選択肢コードが正しく共通コードに変換されました！")
            print("在庫減少システムがクリーンになりました。")
        else:
            print(f"\n⚠️ {len(after_choice_codes.data)}件の選択肢コードがまだ残っています。")
        
        return True, {
            'fixed_count': fixed_count,
            'merged_count': merged_count,
            'created_count': created_count,
            'remaining_choice_codes': len(after_choice_codes.data)
        }
        
    except Exception as e:
        print(f"エラー: {str(e)}")
        import traceback
        traceback.print_exc()
        return False, None

if __name__ == "__main__":
    try:
        print("選択肢コード（P01、S01）を正しい共通コード（CM201、CM202）に変換します。")
        print("この処理により、在庫減少システムがクリーンになります。")
        
        response = input("\n処理を実行しますか？ (y/n): ")
        if response.lower() != 'y':
            print("処理をキャンセルしました。")
            exit(0)
        
        success, results = fix_choice_code_mapping()
        
        if success:
            print(f"\n修正サマリー:")
            print(f"  - 処理アイテム数: {results['fixed_count']}件")
            print(f"  - 統合: {results['merged_count']}件")
            print(f"  - 変換: {results['created_count']}件")
            print(f"  - 残り選択肢コード: {results['remaining_choice_codes']}件")
            
            if results['remaining_choice_codes'] == 0:
                print("\n🎉 選択肢コードマッピング修正が完全に成功しました！")
                print("在庫減少システムはクリーンになりました。")
            else:
                print(f"\n⚠️ まだ{results['remaining_choice_codes']}件の選択肢コードが残っています。")
        else:
            print("\n処理でエラーが発生しました")
        
    except KeyboardInterrupt:
        print("\n処理が中断されました")