"""
Google Sheets同期のテスト
"""

import requests
import json

API_URL = "https://rakuten-order-sync-7alvdxgvsa-an.a.run.app"

def test_sheets_sync():
    print("=== Google Sheets同期テスト ===\n")
    
    # 1. 環境情報の確認
    print("1. 環境情報の確認...")
    response = requests.get(f"{API_URL}/debug-env")
    if response.status_code == 200:
        data = response.json()
        print(f"   環境設定:")
        print(f"   - Google認証ファイル: {'✓ 設定済み' if data.get('creds_file_found') else '✗ 未設定'}")
        print(f"   - Spreadsheet ID: {'✓ 設定済み' if data.get('spreadsheet_id_set') else '✗ 未設定'}")
        print(f"   - Sheets Sync利用可能: {'✓ Yes' if data.get('sheets_sync_available') else '✗ No'}")
    print()
    
    # 2. POSTリクエストでSheets同期を実行
    print("2. Sheets同期の実行...")
    try:
        response = requests.post(
            f"{API_URL}/sync-sheets",
            headers={
                "Content-Type": "application/json",
                "Content-Length": "0"
            }
        )
        
        print(f"   ステータスコード: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   結果: {json.dumps(data, indent=4, ensure_ascii=False)}")
            
            if data.get('status') == 'success' and data.get('results'):
                results = data['results']
                print("\n   詳細結果:")
                for key, value in results.items():
                    print(f"   - {key}: 成功 {value.get('success', 0)}件, エラー {value.get('error', 0)}件")
        else:
            print(f"   エラー: {response.text}")
            
    except Exception as e:
        print(f"   エラー: {str(e)}")

if __name__ == "__main__":
    test_sheets_sync()
