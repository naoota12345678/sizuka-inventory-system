#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
楽天APIから最新データを取得してSKU構造を確認
"""

import os
import json
from datetime import datetime, timedelta

# 環境変数を設定
os.environ['SUPABASE_URL'] = 'https://equrcpeifogdrxoldkpe.supabase.co'
os.environ['SUPABASE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ'
os.environ['RAKUTEN_SERVICE_SECRET'] = 'SP338531_d1NJjF2R5OwZpWH6'
os.environ['RAKUTEN_LICENSE_KEY'] = 'SL338531_kUvqO4kIHaMbr9ik'

from api.rakuten_api import RakutenAPI

def test_rakuten_api_sku():
    """楽天APIからデータを取得してSKU構造を確認"""
    
    try:
        # 楽天APIクライアントを初期化
        api = RakutenAPI()
        
        # 今日から3日前までのデータを取得
        end_date = datetime.now()
        start_date = end_date - timedelta(days=3)
        
        print(f"楽天API注文データ取得: {start_date.strftime('%Y-%m-%d')} ～ {end_date.strftime('%Y-%m-%d')}")
        
        # 注文データを取得
        orders = api.get_orders(start_date, end_date)
        
        print(f"取得した注文数: {len(orders)}")
        
        if orders:
            # 最初の注文の詳細を確認
            first_order = orders[0]
            print(f"\n=== 注文サンプル ===")
            print(f"Order Number: {first_order.get('orderNumber')}")
            
            # パッケージリストを確認
            packages = first_order.get('PackageModelList', [])
            if packages:
                first_package = packages[0]
                print(f"\nPackage情報:")
                print(f"  Keys: {list(first_package.keys())}")
                
                # アイテムリストを確認
                items = first_package.get('ItemModelList', [])
                if items:
                    first_item = items[0]
                    print(f"\n=== アイテム詳細 ===")
                    print(f"Item keys: {list(first_item.keys())}")
                    
                    # SKU関連フィールドを確認
                    sku_fields = ['itemNumber', 'variantId', 'skuId', 'SkuModelList']
                    print(f"\nSKU関連フィールド:")
                    for field in sku_fields:
                        value = first_item.get(field)
                        print(f"  {field}: {value}")
                    
                    # SkuModelListの詳細
                    sku_models = first_item.get('SkuModelList', [])
                    if sku_models:
                        print(f"\nSkuModelList[0]:")
                        for key, value in sku_models[0].items():
                            print(f"  {key}: {value}")
                    
                    # selectedChoiceの確認
                    selected_choice = first_item.get('selectedChoice')
                    print(f"\nselectedChoice: {selected_choice}")
                    
                    # 全アイテム情報をJSONで出力（一部）
                    print(f"\n=== 完全なアイテム構造（最初の1件） ===")
                    print(json.dumps(first_item, indent=2, ensure_ascii=False)[:1000] + "...")
                    
    except Exception as e:
        print(f"エラー: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_rakuten_api_sku()