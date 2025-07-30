#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Google Sheets同期の問題を診断するスクリプト
"""

import os
import sys

print("=== Google Sheets同期診断 ===\n")

# 1. 環境変数の確認
print("1. 環境変数の確認:")
env_vars = {
    'GOOGLE_APPLICATION_CREDENTIALS': os.getenv('GOOGLE_APPLICATION_CREDENTIALS'),
    'GOOGLE_CREDENTIALS_FILE': os.getenv('GOOGLE_CREDENTIALS_FILE'),
    'PRODUCT_MASTER_SPREADSHEET_ID': os.getenv('PRODUCT_MASTER_SPREADSHEET_ID')
}

for key, value in env_vars.items():
    print(f"   {key}: {value if value else 'Not set'}")

# 2. 認証ファイルの確認
print("\n2. 認証ファイルの確認:")
cred_paths = [
    'google-credentials.json',
    '/app/credentials.json',
    env_vars.get('GOOGLE_APPLICATION_CREDENTIALS', ''),
    env_vars.get('GOOGLE_CREDENTIALS_FILE', '')
]

for path in cred_paths:
    if path and os.path.exists(path):
        print(f"   ✅ {path}: 存在します (サイズ: {os.path.getsize(path)} bytes)")
    elif path:
        print(f"   ❌ {path}: 存在しません")

# 3. 必要なパッケージの確認
print("\n3. 必要なパッケージの確認:")
packages = [
    'google.oauth2',
    'googleapiclient',
    'google.auth',
    'pandas',
    'supabase'
]

for package in packages:
    try:
        __import__(package)
        print(f"   ✅ {package}: インストール済み")
    except ImportError as e:
        print(f"   ❌ {package}: インストールされていません ({e})")

# 4. Google Sheets APIの初期化テスト
print("\n4. Google Sheets APIの初期化テスト:")
try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    
    # 認証ファイルを探す
    cred_file = None
    for path in ['google-credentials.json', '/app/credentials.json']:
        if os.path.exists(path):
            cred_file = path
            break
    
    if cred_file:
        print(f"   認証ファイル使用: {cred_file}")
        credentials = service_account.Credentials.from_service_account_file(
            cred_file,
            scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
        )
        service = build('sheets', 'v4', credentials=credentials)
        print("   ✅ Google Sheets API初期化成功")
        
        # スプレッドシートの存在確認
        spreadsheet_id = os.getenv('PRODUCT_MASTER_SPREADSHEET_ID')
        if spreadsheet_id:
            try:
                result = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
                print(f"   ✅ スプレッドシート確認成功: {result.get('properties', {}).get('title', 'Unknown')}")
            except Exception as e:
                print(f"   ❌ スプレッドシート確認失敗: {e}")
    else:
        print("   ❌ 認証ファイルが見つかりません")
        
except Exception as e:
    print(f"   ❌ 初期化失敗: {e}")

# 5. sheets_sync.pyの確認
print("\n5. sheets_sync.pyモジュールの確認:")
try:
    import product_master.sheets_sync
    print("   ✅ product_master.sheets_sync: インポート成功")
    
    # GoogleSheetsSyncクラスの確認
    if hasattr(product_master.sheets_sync, 'GoogleSheetsSync'):
        print("   ✅ GoogleSheetsSyncクラス: 存在します")
    else:
        print("   ❌ GoogleSheetsSyncクラス: 見つかりません")
        
except Exception as e:
    print(f"   ❌ product_master.sheets_sync: インポート失敗 ({e})")

print("\n診断完了")
