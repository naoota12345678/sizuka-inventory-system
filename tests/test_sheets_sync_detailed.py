"""
Google Sheets同期の詳細テスト
エラーの原因を特定するためのテストスクリプト
"""

import requests
import json
from datetime import datetime

API_URL = "https://rakuten-order-sync-7alvdxgvsa-an.a.run.app"

def test_sheets_sync_detailed():
    print("=== Google Sheets同期 詳細テスト ===")
    print(f"実行時刻: {datetime.now()}\n")
    
    # 1. 同期前の状態確認
    print("1. 同期前のデータ確認...")
    
    # 商品マスターの件数を確認
    response = requests.get(f"{API_URL}/check-connection")
    if response.status_code == 200:
        data = response.json()
        print(f"   現在のデータ件数:")
        print(f"   - 注文数: {data.get('orders_count', 0)}")
        print(f"   - 注文アイテム数: {data.get('items_count', 0)}")
    print()
    
    # 2. 同期の実行
    print("2. Google Sheets同期を実行...")
    response = requests.post(
        f"{API_URL}/sync-sheets",
        headers={
            "Content-Type": "application/json",
            "Content-Length": "0"
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"   ステータス: {data.get('status')}")
        print("\n   === 同期結果の詳細 ===")
        
        results = data.get('results', {})
        total_success = 0
        total_error = 0
        
        for sheet_name, result in results.items():
            success = result.get('success', 0)
            error = result.get('error', 0)
            total_success += success
            total_error += error
            
            print(f"\n   {sheet_name}:")
            print(f"   - 成功: {success}件")
            print(f"   - エラー: {error}件")
            
            if error > 0:
                print(f"   ⚠️ エラーが発生しています")
                if 'error_message' in result:
                    print(f"   エラーメッセージ: {result['error_message']}")
        
        print(f"\n   === 合計 ===")
        print(f"   - 総成功数: {total_success}件")
        print(f"   - 総エラー数: {total_error}件")
        print(f"   - 成功率: {(total_success / (total_success + total_error) * 100):.1f}%")
        
        # エラーがある場合の推測
        if total_error > 0:
            print("\n   === エラーの可能性 ===")
            print("   1. スプレッドシートに空の行がある")
            print("   2. 数値フィールドに文字列が入っている")
            print("   3. 必須フィールドが空になっている")
            print("   4. データ形式が不正（日付、数値など）")
            
    else:
        print(f"   エラー: {response.status_code}")
        print(f"   詳細: {response.text}")
    
    print("\n=== テスト完了 ===")

if __name__ == "__main__":
    test_sheets_sync_detailed()
