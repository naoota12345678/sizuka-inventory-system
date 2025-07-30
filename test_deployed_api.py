#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
デプロイ後のAPIテストスクリプト
"""

import requests
import json
import sys
from datetime import datetime, timedelta

def test_api(base_url):
    """APIの各エンドポイントをテスト"""
    
    print(f"🧪 APIテストを開始します: {base_url}")
    print("-" * 50)
    
    # 1. ヘルスチェック
    print("\n1. ヘルスチェック (/health)")
    try:
        response = requests.get(f"{base_url}/health")
        print(f"   ステータス: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   レスポンス: {json.dumps(data, indent=2, ensure_ascii=False)}")
            print("   ✅ ヘルスチェック成功")
        else:
            print(f"   ❌ エラー: {response.text}")
    except Exception as e:
        print(f"   ❌ エラー: {str(e)}")
    
    # 2. ルートエンドポイント
    print("\n2. ルートエンドポイント (/)")
    try:
        response = requests.get(f"{base_url}/")
        print(f"   ステータス: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   アプリ名: {data.get('message')}")
            print(f"   バージョン: {data.get('version')}")
            print("   ✅ ルートエンドポイント成功")
        else:
            print(f"   ❌ エラー: {response.text}")
    except Exception as e:
        print(f"   ❌ エラー: {str(e)}")
    
    # 3. データベース接続確認
    print("\n3. データベース接続確認 (/check-connection)")
    try:
        response = requests.get(f"{base_url}/check-connection")
        print(f"   ステータス: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   接続状態: {data.get('status')}")
            print(f"   注文数: {data.get('orders_count', 0)}")
            print(f"   商品数: {data.get('items_count', 0)}")
            print("   ✅ データベース接続成功")
        else:
            print(f"   ❌ エラー: {response.text}")
    except Exception as e:
        print(f"   ❌ エラー: {str(e)}")
    
    # 4. 環境変数デバッグ（開発用）
    print("\n4. 環境変数デバッグ (/debug-env)")
    try:
        response = requests.get(f"{base_url}/debug-env")
        print(f"   ステータス: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Google Sheets同期: {'利用可能' if data.get('sheets_sync_available') else '利用不可'}")
            print(f"   スプレッドシートID設定: {'あり' if data.get('spreadsheet_id_set') else 'なし'}")
            print("   ✅ 環境変数確認成功")
        else:
            print(f"   ❌ エラー: {response.text}")
    except Exception as e:
        print(f"   ❌ エラー: {str(e)}")
    
    # 5. 注文同期テスト（過去1日）
    print("\n5. 注文同期テスト (/sync-orders?days=1)")
    try:
        response = requests.get(f"{base_url}/sync-orders?days=1")
        print(f"   ステータス: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   同期状態: {data.get('status')}")
            print(f"   注文数: {data.get('order_count', 0)}")
            if data.get('sync_result'):
                result = data['sync_result']
                print(f"   成功: {result.get('success_count', 0)}件")
                print(f"   エラー: {result.get('error_count', 0)}件")
            print("   ✅ 注文同期成功")
        else:
            print(f"   ❌ エラー: {response.text}")
    except Exception as e:
        print(f"   ❌ エラー: {str(e)}")
    
    # 6. Google Sheets同期テスト
    print("\n6. Google Sheets同期テスト (/sync-sheets)")
    try:
        response = requests.post(f"{base_url}/sync-sheets")
        print(f"   ステータス: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            status = data.get('status')
            if status == 'unavailable':
                print("   ⚠️ Google Sheets同期は利用できません")
                print(f"   詳細: {data.get('details')}")
            elif status == 'success':
                print("   ✅ Google Sheets同期成功")
                if data.get('results'):
                    print(f"   結果: {json.dumps(data['results'], indent=2, ensure_ascii=False)}")
            else:
                print(f"   ❌ エラー: {data.get('message')}")
        else:
            print(f"   ❌ エラー: {response.text}")
    except Exception as e:
        print(f"   ❌ エラー: {str(e)}")
    
    print("\n" + "-" * 50)
    print("🏁 APIテスト完了")

def main():
    """メイン処理"""
    if len(sys.argv) > 1:
        # URLが引数で指定された場合
        base_url = sys.argv[1].rstrip('/')
    else:
        # デフォルトはローカルホスト
        base_url = "http://localhost:8000"
    
    test_api(base_url)

if __name__ == "__main__":
    main()