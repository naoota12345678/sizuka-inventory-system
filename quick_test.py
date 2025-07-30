import requests
import json

# テスト対象のURL
base_url = "https://rakuten-order-sync-338531499605.asia-northeast1.run.app"

print("🧪 デプロイされたAPIのテストを開始します...")
print(f"URL: {base_url}")
print("-" * 50)

# 1. ルートエンドポイント
print("\n1. ルートエンドポイント (/)")
try:
    response = requests.get(f"{base_url}/", timeout=10)
    print(f"   ステータスコード: {response.status_code}")
    if response.status_code == 200:
        print(f"   レスポンス: {response.json()}")
    else:
        print(f"   エラー: {response.text}")
except Exception as e:
    print(f"   エラー: {str(e)}")

# 2. ヘルスチェック
print("\n2. ヘルスチェック (/health)")
try:
    response = requests.get(f"{base_url}/health", timeout=10)
    print(f"   ステータスコード: {response.status_code}")
    if response.status_code == 200:
        print(f"   レスポンス: {response.json()}")
    else:
        print(f"   エラー: {response.text}")
except Exception as e:
    print(f"   エラー: {str(e)}")

# 3. docs確認
print("\n3. APIドキュメント (/docs)")
try:
    response = requests.get(f"{base_url}/docs", timeout=10)
    print(f"   ステータスコード: {response.status_code}")
    if response.status_code == 200:
        print("   ✅ APIドキュメントが利用可能")
    else:
        print(f"   エラー: {response.text[:100]}")
except Exception as e:
    print(f"   エラー: {str(e)}")

print("\n" + "-" * 50)
print("テスト完了")