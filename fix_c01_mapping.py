#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
C01（タイオセット）のマッピング追加
唯一のマッピング失敗商品を解決
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

def fix_c01_mapping():
    """
    C01（タイオセット）のマッピングを追加
    """
    print("=" * 60)
    print("C01（タイオセット）マッピング修正")
    print("=" * 60)
    
    try:
        # 新しい共通コードを決定
        new_common_code = "CM301"  # 新しい共通コード
        product_name = "タイオセット"
        
        print(f"追加するマッピング:")
        print(f"  choice_code: C01")
        print(f"  rakuten_sku: 1834") 
        print(f"  common_code: {new_common_code}")
        print(f"  product_name: {product_name}")
        
        # 1. choice_code_mappingにC01を追加
        print(f"\nStep 1: choice_code_mappingにC01を追加...")
        
        choice_record = {
            'choice_info': {
                'choice_code': 'C01',
                'choice_name': 'C01 Choice',
                'choice_value': product_name,
                'category': 'manual_addition_c01'
            },
            'common_code': new_common_code,
            'product_name': product_name,
            'rakuten_sku': 'CHOICE_C01'  # NOT NULL制約対応
        }
        
        choice_result = supabase.table('choice_code_mapping').insert(choice_record).execute()
        
        if choice_result.data:
            print(f"  ✅ choice_code_mapping追加成功: C01 → {new_common_code}")
        else:
            print(f"  ❌ choice_code_mapping追加失敗")
            return False
        
        # 2. product_masterにSKU 1834を追加
        print(f"\nStep 2: product_masterにSKU 1834を追加...")
        
        product_record = {
            'rakuten_sku': '1834',
            'common_code': new_common_code,
            'product_name': product_name
        }
        
        product_result = supabase.table('product_master').insert(product_record).execute()
        
        if product_result.data:
            print(f"  ✅ product_master追加成功: 1834 → {new_common_code}")
        else:
            print(f"  ❌ product_master追加失敗")
            return False
        
        # 3. 在庫レコード作成
        print(f"\nStep 3: 在庫レコード作成...")
        
        inventory_record = {
            'common_code': new_common_code,
            'product_name': product_name,
            'current_stock': 0,  # 初期在庫0
            'minimum_stock': 0,
            'last_updated': datetime.now(timezone.utc).isoformat()
        }
        
        inventory_result = supabase.table('inventory').insert(inventory_record).execute()
        
        if inventory_result.data:
            print(f"  ✅ inventory追加成功: {new_common_code}")
        else:
            print(f"  ❌ inventory追加失敗")
            return False
        
        # 4. マッピング確認
        print(f"\nStep 4: マッピング確認...")
        
        # C01確認
        c01_check = supabase.table('choice_code_mapping').select('*').contains('choice_info', {'choice_code': 'C01'}).execute()
        print(f"  C01マッピング: {len(c01_check.data)}件")
        
        # SKU 1834確認
        sku_check = supabase.table('product_master').select('*').eq('rakuten_sku', '1834').execute()
        print(f"  SKU 1834マッピング: {len(sku_check.data)}件")
        
        print(f"\n" + "=" * 60)
        print("C01（タイオセット）マッピング修正完了")
        print("=" * 60)
        print(f"追加された共通コード: {new_common_code}")
        print(f"商品名: {product_name}")
        print(f"これでマッピング成功率が100%になります！")
        
        return True
        
    except Exception as e:
        print(f"エラー: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    try:
        print("唯一のマッピング失敗商品 C01（タイオセット）を修正します。")
        
        response = input("\n処理を実行しますか？ (y/n): ")
        if response.lower() != 'y':
            print("処理をキャンセルしました。")
            exit(0)
        
        success = fix_c01_mapping()
        
        if success:
            print(f"\n🎉 C01マッピング修正が完了しました！")
            print(f"これで楽天データのマッピング成功率が100%になります。")
        else:
            print(f"\n❌ 処理でエラーが発生しました")
        
    except KeyboardInterrupt:
        print("\n処理が中断されました")