#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
システム動作確認（簡易版）
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.config import Config
from core.database import Database

print("\n=== 楽天注文同期システム 動作確認 ===\n")

# 1. 環境変数チェック
print("[環境変数]")
env_check = {
    'SUPABASE_URL': bool(Config.SUPABASE_URL),
    'SUPABASE_KEY': bool(Config.SUPABASE_KEY),
    'RAKUTEN_SERVICE_SECRET': bool(Config.RAKUTEN_SERVICE_SECRET),
    'RAKUTEN_LICENSE_KEY': bool(Config.RAKUTEN_LICENSE_KEY),
    'SPREADSHEET_ID': bool(Config.PRODUCT_MASTER_SPREADSHEET_ID)
}

for name, exists in env_check.items():
    status = "OK" if exists else "NG"
    print(f"  {status} {name}")

# 2. データベース接続
print("\n[データベース接続]")
try:
    if Database.test_connection():
        print("  OK Supabase接続")
    else:
        print("  NG Supabase接続")
except Exception as e:
    print(f"  NG エラー: {str(e)}")

# 3. Google Sheets設定
print("\n[Google Sheets設定]")
if Config.is_sheets_sync_available():
    print("  OK 認証情報あり")
else:
    print("  NG 認証情報なし")

# 4. 総合判定
print("\n[判定結果]")
all_ok = all(env_check.values()) and Database.test_connection()
if all_ok:
    print("  システムは正常に動作可能です")
else:
    print("  設定に問題があります。環境変数を確認してください")

print("\n" + "="*40)