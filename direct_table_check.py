# -*- coding: utf-8 -*-
"""
既存のCloud RunからSupabaseに直接アクセスしてテーブル構造を確認
"""
import requests
import json

def check_via_existing_api():
    """既存のAPIエンドポイントを使ってテーブル情報を取得"""
    base_url = "https://sizuka-inventory-system-p2wv4efvja-an.a.run.app"
    
    print("=== 既存APIを使用したテーブル構造確認 ===\n")
    
    # 1. システム状況確認
    try:
        response = requests.get(f"{base_url}/api/system_status", timeout=30)
        if response.status_code == 200:
            data = response.json()
            print("1. システム状況:")
            print(f"   - データベース接続: OK")
            
            # テーブル存在確認
            for table_name, info in data.get("table_status", {}).items():
                exists = info.get("exists", False)
                has_data = info.get("has_data", False)
                print(f"   - {table_name}: {'存在' if exists else '不存在'}, データ: {'あり' if has_data else 'なし'}")
        else:
            print(f"システム状況API エラー: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"システム状況API 接続エラー: {str(e)}")
        return False
    
    # 2. 楽天選択肢コード抽出デモ（実際のorder_itemsテーブル構造がわかる）
    try:
        response = requests.get(f"{base_url}/api/demo_choice_extraction", timeout=30)
        if response.status_code == 200:
            data = response.json()
            print(f"\n2. 楽天選択肢コード抽出デモ:")
            print(f"   - ステータス: {data.get('status', 'unknown')}")
            
            # 実際のorder_itemsデータ構造を確認
            if "order_items_sample" in data:
                sample = data["order_items_sample"]
                if sample:
                    print(f"   - order_itemsサンプル取得: 成功")
                    columns = list(sample[0].keys()) if sample else []
                    print(f"   - カラム数: {len(columns)}")
                    
                    # 楽天関連カラムの確認
                    rakuten_cols = ['choice_code', 'rakuten_sku', 'rakuten_item_number', 'extended_rakuten_data']
                    existing = [col for col in rakuten_cols if col in columns]
                    missing = [col for col in rakuten_cols if col not in columns]
                    
                    print(f"   - 楽天カラム存在: {existing}")
                    print(f"   - 楽天カラム欠落: {missing}")
                    
                    if len(missing) == 0:
                        print("   ✅ 02_rakuten_enhancement.sql は適用済み")
                    else:
                        print("   ❌ 02_rakuten_enhancement.sql は未適用")
            
        else:
            print(f"選択肢抽出デモAPI エラー: {response.status_code}")
            
    except Exception as e:
        print(f"選択肢抽出デモAPI 接続エラー: {str(e)}")
    
    # 3. 商品分析API（product_mapping_masterテーブルの確認）
    try:
        response = requests.get(f"{base_url}/api/analyze_sold_products", timeout=30)
        if response.status_code == 200:
            data = response.json()
            print(f"\n3. 商品分析API:")
            print(f"   - ステータス: {data.get('status', 'unknown')}")
            
            # product_mapping_masterの確認
            if "mapping_suggestions" in data:
                print("   ✅ product_mapping機能は動作中")
            elif "error" in data and "product_mapping_master" in str(data.get("error", "")):
                print("   ❌ product_mapping_master テーブルが存在しない")
            
        else:
            print(f"商品分析API エラー: {response.status_code}")
            
    except Exception as e:
        print(f"商品分析API 接続エラー: {str(e)}")
    
    print(f"\n=== 確認完了 ===")
    return True

if __name__ == "__main__":
    check_via_existing_api()