#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Google認証情報をSecret Managerに設定し、Cloud Runサービスを更新
"""

import json
import subprocess
import sys

def main():
    print("🔧 Google Sheets認証設定を開始します...")
    
    # 1. google-credentials.jsonを読み込む
    try:
        with open('google-credentials.json', 'r') as f:
            creds = json.load(f)
        print("✅ 認証ファイルを読み込みました")
    except Exception as e:
        print(f"❌ 認証ファイルの読み込みエラー: {e}")
        return 1
    
    # 2. JSON文字列に変換（改行をエスケープ）
    creds_json = json.dumps(creds, separators=(',', ':'))
    
    # 3. Secret Managerに保存
    print("📝 Secret Managerに認証情報を保存中...")
    try:
        # 既存のシークレットを削除（存在する場合）
        subprocess.run(['gcloud', 'secrets', 'delete', 'GOOGLE_SERVICE_ACCOUNT_JSON', '--quiet'], 
                      capture_output=True)
    except:
        pass
    
    # 新しいシークレットを作成
    result = subprocess.run(
        ['gcloud', 'secrets', 'create', 'GOOGLE_SERVICE_ACCOUNT_JSON', '--data-file=-'],
        input=creds_json.encode(),
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"❌ Secret作成エラー: {result.stderr}")
        return 1
    
    print("✅ Secretを作成しました")
    
    # 4. Cloud Runサービスを更新
    print("🚀 Cloud Runサービスを更新中...")
    result = subprocess.run([
        'gcloud', 'run', 'services', 'update', 'rakuten-order-sync',
        '--region=asia-northeast1',
        '--set-secrets=GOOGLE_SERVICE_ACCOUNT_JSON=GOOGLE_SERVICE_ACCOUNT_JSON:latest'
    ], capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"❌ サービス更新エラー: {result.stderr}")
        return 1
    
    print("✅ Cloud Runサービスを更新しました")
    
    # 5. 再デプロイの案内
    print("\n" + "="*50)
    print("✨ 設定が完了しました！")
    print("次のコマンドでサービスを再デプロイしてください：")
    print("gcloud builds submit --config=cloudbuild.yaml")
    print("="*50)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())