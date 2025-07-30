"""
Google Sheets連携の確認スクリプト
"""

import requests
import json

API_URL = "https://rakuten-order-sync-7alvdxgvsa-an.a.run.app"

def check_sheets_integration():
    print("=== Google Sheets連携チェック ===\n")
    
    # 1. 環境情報の確認
    print("1. 環境情報の確認...")
    response = requests.get(f"{API_URL}/debug-env")
    if response.status_code == 200:
        data = response.json()
        print(f"   - Google認証ファイル: {'✓ 設定済み' if data.get('creds_file_found') else '✗ 未設定'}")
        print(f"   - Spreadsheet ID: {'✓ 設定済み' if data.get('spreadsheet_id_set') else '✗ 未設定'}")
        print(f"   - Sheets Sync利用可能: {'✓ Yes' if data.get('sheets_sync_available') else '✗ No'}")
        print(f"   - Google Auth: {'✓ インポート済み' if data['debug_info']['google_auth_imported'] else '✗ 未インポート'}")
        print(f"   - Google API Client: {'✓ インポート済み' if data['debug_info']['googleapiclient_imported'] else '✗ 未インポート'}")
        print(f"   - Pandas: {'✓ インポート済み' if data['debug_info']['pandas_imported'] else '✗ 未インポート'}")
    print()
    
    # 2. ヘルスチェック
    print("2. ヘルスチェック...")
    response = requests.get(f"{API_URL}/health")
    if response.status_code == 200:
        data = response.json()
        print(f"   - Sheets Sync Available: {data.get('sheets_sync_available')}")
        print(f"   - Config: {json.dumps(data.get('config', {}), indent=6)}")
    print()
    
    # 3. Sheets同期の実行
    print("3. Sheets同期テスト...")
    response = requests.post(f"{API_URL}/sync-sheets")
    if response.status_code == 200:
        data = response.json()
        print(f"   - ステータス: {data.get('status')}")
        print(f"   - メッセージ: {data.get('message')}")
        if data.get('results'):
            print(f"   - 結果: {json.dumps(data.get('results'), indent=6, ensure_ascii=False)}")
    else:
        print(f"   - エラー: {response.status_code}")
        print(f"   - 詳細: {response.text}")
    print()
    
    # 4. 推奨事項
    print("=== 診断結果 ===")
    response = requests.get(f"{API_URL}/debug-env")
    data = response.json()
    
    if not data.get('sheets_sync_available'):
        print("❌ Google Sheets同期が利用できません")
        print("\n原因:")
        if not data['debug_info']['pandas_imported']:
            print("   - pandasがインポートされていません")
            print("   → Cloud Runのコンテナ内でpandasが正しくインストールされていない可能性があります")
        print("\n解決方法:")
        print("   1. Dockerfileでpandasのインストールを確認")
        print("   2. requirements.txtにpandas==2.0.3が含まれていることを確認")
        print("   3. 再度ビルド・デプロイを実行")
    else:
        print("✅ Google Sheets同期は正常に動作しています")

if __name__ == "__main__":
    check_sheets_integration()
