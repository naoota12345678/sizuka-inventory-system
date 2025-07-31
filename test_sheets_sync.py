#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Google Sheets同期テストスクリプト
"""

from api.sheets_sync import sync_product_master, SHEETS_SYNC_AVAILABLE
import json

def test_sheets_sync():
    print("=== Google Sheets同期テスト ===")
    
    if not SHEETS_SYNC_AVAILABLE:
        print("❌ Google Sheets同期が利用できません")
        return False
    
    try:
        print("Google Sheetsから名寄せデータを同期中...")
        result = sync_product_master()
        
        print()
        print("同期結果:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
        if result.get('status') == 'success':
            print()
            print("✅ 同期成功！")
            
            # 同期されたデータを確認
            from core.database import supabase
            
            print()
            print("=== 同期されたデータの確認 ===")
            
            # product_masterの確認
            try:
                products = supabase.table('product_master').select('common_code, product_name, rakuten_sku').limit(5).execute()
                if products.data:
                    print("商品マスター（サンプル）:")
                    for product in products.data:
                        print(f"  {product.get('common_code')}: {product.get('product_name')}")
                        print(f"    楽天SKU: {product.get('rakuten_sku')}")
                else:
                    print("商品マスターにデータがありません")
            except Exception as e:
                print(f"商品マスター確認エラー: {str(e)}")
            
            return True
        else:
            print("❌ 同期に失敗しました")
            return False
            
    except Exception as e:
        print(f"❌ 同期エラー: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_sheets_sync()
    
    if success:
        print()
        print("🎉 次のステップ:")
        print("1. 楽天注文商品と名寄せデータの連携テスト")
        print("2. 在庫連動システムの実装")
    else:
        print()
        print("⚠️ まずSupabaseでテーブルを作成してください")