#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
不足している楽天SKUレコードを作成
制約削除後に実行
"""

import os
from supabase import create_client
from datetime import datetime, timezone

# 環境変数を設定
os.environ['SUPABASE_URL'] = 'https://equrcpeifogdrxoldkpe.supabase.co'
os.environ['SUPABASE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ'

SUPABASE_URL = "https://equrcpeifogdrxoldkpe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ"

def create_missing_sku_records():
    """不足している楽天SKUレコードを作成"""
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    print("=== 不足楽天SKUレコード作成 ===")
    
    # 同じ商品の楽天SKUリスト（すべてPC001にマッピング）
    missing_skus = [
        {'rakuten_sku': '1837', 'common_code': 'PC001'},
        {'rakuten_sku': '1852', 'common_code': 'PC001'},
        {'rakuten_sku': '1825', 'common_code': 'PC001'},
        {'rakuten_sku': '1851', 'common_code': 'PC001'}
    ]
    
    created_count = 0
    
    for sku_data in missing_skus:
        try:
            # 既存チェック
            existing = supabase.table('product_master').select('id').eq('rakuten_sku', sku_data['rakuten_sku']).execute()
            
            if existing.data:
                print(f"  既存: 楽天SKU {sku_data['rakuten_sku']} - 更新します")
                # 更新
                result = supabase.table('product_master').update({
                    'common_code': sku_data['common_code']
                }).eq('rakuten_sku', sku_data['rakuten_sku']).execute()
                
                if result.data:
                    print(f"    更新成功: {sku_data['rakuten_sku']} → {sku_data['common_code']}")
                    created_count += 1
            else:
                print(f"  新規作成: 楽天SKU {sku_data['rakuten_sku']}")
                # 新規作成
                result = supabase.table('product_master').insert({
                    'rakuten_sku': sku_data['rakuten_sku'],
                    'common_code': sku_data['common_code'],
                    'created_at': datetime.now(timezone.utc).isoformat(),
                    'updated_at': datetime.now(timezone.utc).isoformat(),
                    'product_name': f'楽天商品 {sku_data["rakuten_sku"]}',
                    'is_active': True
                }).execute()
                
                if result.data:
                    print(f"    作成成功: {sku_data['rakuten_sku']} → {sku_data['common_code']}")
                    created_count += 1
                else:
                    print(f"    作成失敗: {sku_data['rakuten_sku']}")
                    
        except Exception as e:
            print(f"  エラー: 楽天SKU {sku_data['rakuten_sku']} - {str(e)}")
    
    print(f"\n=== 完了 ===")
    print(f"処理成功: {created_count}件")
    
    # 結果確認
    print(f"\n=== 確認 ===")
    for sku_data in missing_skus:
        result = supabase.table('product_master').select('rakuten_sku, common_code').eq('rakuten_sku', sku_data['rakuten_sku']).execute()
        if result.data:
            item = result.data[0]
            print(f"  楽天SKU {item['rakuten_sku']}: → {item['common_code']}")
        else:
            print(f"  楽天SKU {sku_data['rakuten_sku']}: 未登録")

if __name__ == "__main__":
    create_missing_sku_records()