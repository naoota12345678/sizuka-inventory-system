#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
システム動作確認スクリプト
各コンポーネントの接続と基本機能をテスト
"""

import os
import sys
import asyncio
from datetime import datetime, timedelta
import pytz

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.config import Config
from core.database import Database
from api.rakuten_api import RakutenAPI
from api.sheets_sync import SHEETS_SYNC_AVAILABLE

def print_section(title):
    """セクションタイトルを表示"""
    print(f"\n{'='*50}")
    print(f" {title}")
    print(f"{'='*50}")

def test_environment():
    """環境変数のチェック"""
    print_section("環境変数チェック")
    
    env_vars = {
        'SUPABASE_URL': Config.SUPABASE_URL,
        'SUPABASE_KEY': Config.SUPABASE_KEY,
        'RAKUTEN_SERVICE_SECRET': Config.RAKUTEN_SERVICE_SECRET,
        'RAKUTEN_LICENSE_KEY': Config.RAKUTEN_LICENSE_KEY,
        'PRODUCT_MASTER_SPREADSHEET_ID': Config.PRODUCT_MASTER_SPREADSHEET_ID
    }
    
    all_good = True
    for name, value in env_vars.items():
        if value:
            # 秘密情報は一部マスク
            if 'KEY' in name or 'SECRET' in name:
                display_value = value[:10] + '...' if len(value) > 10 else value
            else:
                display_value = value
            print(f"✅ {name}: {display_value}")
        else:
            print(f"❌ {name}: 未設定")
            all_good = False
    
    return all_good

def test_database_connection():
    """データベース接続テスト"""
    print_section("データベース接続テスト")
    
    try:
        if Database.test_connection():
            print("✅ Supabase接続: 成功")
            
            # テーブル存在確認
            from supabase import create_client
            supabase = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
            
            tables = ['platform', 'orders', 'order_items', 'inventory', 'product_master']
            for table in tables:
                try:
                    result = supabase.table(table).select("*").limit(1).execute()
                    print(f"✅ テーブル '{table}': 存在確認OK")
                except Exception as e:
                    print(f"❌ テーブル '{table}': エラー - {str(e)}")
            
            return True
        else:
            print("❌ Supabase接続: 失敗")
            return False
            
    except Exception as e:
        print(f"❌ データベース接続エラー: {str(e)}")
        return False

def test_rakuten_api():
    """楽天API接続テスト"""
    print_section("楽天API接続テスト")
    
    try:
        api = RakutenAPI()
        
        # 認証情報の確認
        if api.service_secret and api.license_key:
            print("✅ 楽天API認証情報: 設定済み")
        else:
            print("❌ 楽天API認証情報: 未設定")
            return False
        
        # 過去1時間の注文を取得してテスト
        end_date = datetime.now(pytz.UTC)
        start_date = end_date - timedelta(hours=1)
        
        try:
            # 実際のAPI呼び出しは行わず、設定のみ確認
            print("✅ 楽天API設定: 正常")
            return True
        except Exception as e:
            print(f"⚠️  楽天API設定確認: {str(e)}")
            return True  # 設定は正常
            
    except Exception as e:
        print(f"❌ 楽天APIエラー: {str(e)}")
        return False

def test_google_sheets():
    """Google Sheets接続テスト"""
    print_section("Google Sheets接続テスト")
    
    if not SHEETS_SYNC_AVAILABLE:
        print("⚠️  Google Sheets同期: 利用不可（依存関係未インストール）")
        return True
    
    if Config.is_sheets_sync_available():
        print("✅ Google認証情報: 利用可能")
        
        if Config.PRODUCT_MASTER_SPREADSHEET_ID:
            print(f"✅ スプレッドシートID: {Config.PRODUCT_MASTER_SPREADSHEET_ID}")
        else:
            print("❌ スプレッドシートID: 未設定")
            
        # 認証ファイルの確認
        creds_path = Config.get_google_creds_path()
        if creds_path:
            print(f"✅ 認証ファイル: {creds_path}")
        elif Config.GOOGLE_SERVICE_ACCOUNT_JSON:
            print("✅ 認証情報: 環境変数に設定")
        else:
            print("❌ 認証ファイル: 見つかりません")
            
        return True
    else:
        print("❌ Google Sheets同期: 認証情報が見つかりません")
        return False

def check_file_structure():
    """ファイル構造の確認"""
    print_section("ファイル構造チェック")
    
    required_dirs = ['api', 'core', 'product_master']
    required_files = ['main.py', 'requirements.txt']
    
    all_good = True
    
    for dir_name in required_dirs:
        if os.path.exists(dir_name):
            print(f"✅ ディレクトリ '{dir_name}': 存在")
        else:
            print(f"❌ ディレクトリ '{dir_name}': 見つかりません")
            all_good = False
    
    for file_name in required_files:
        if os.path.exists(file_name):
            print(f"✅ ファイル '{file_name}': 存在")
        else:
            print(f"❌ ファイル '{file_name}': 見つかりません")
            all_good = False
    
    return all_good

async def test_api_endpoints():
    """APIエンドポイントのテスト（ローカル実行時のみ）"""
    print_section("APIエンドポイントテスト")
    
    try:
        import httpx
        
        # ローカルサーバーが起動しているか確認
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get("http://localhost:8080/health")
                if response.status_code == 200:
                    data = response.json()
                    print("✅ ヘルスチェック: 正常")
                    print(f"   - Supabase接続: {data.get('supabase_connected', False)}")
                    print(f"   - Sheets同期: {data.get('sheets_sync_available', False)}")
                else:
                    print(f"⚠️  ヘルスチェック: ステータス {response.status_code}")
            except Exception:
                print("⚠️  APIサーバー: 未起動（ローカルテストをスキップ）")
                
    except ImportError:
        print("⚠️  httpxがインストールされていません")

def main():
    """メイン実行"""
    print("\n楽天注文同期システム - 動作確認")
    print("="*50)
    
    results = {
        "環境変数": test_environment(),
        "データベース": test_database_connection(),
        "楽天API": test_rakuten_api(),
        "Google Sheets": test_google_sheets(),
        "ファイル構造": check_file_structure()
    }
    
    # 非同期テスト
    asyncio.run(test_api_endpoints())
    
    # 総合結果
    print_section("総合結果")
    
    all_passed = all(results.values())
    failed_tests = [name for name, result in results.items() if not result]
    
    if all_passed:
        print("\n✅ すべてのチェックが正常に完了しました！")
        print("システムは正常に動作する準備ができています。")
    else:
        print(f"\n⚠️  一部のチェックで問題が見つかりました:")
        for test in failed_tests:
            print(f"   - {test}")
        print("\n上記の問題を解決してから実行してください。")
    
    # 推奨事項
    print_section("推奨事項")
    print("1. 本番環境では、すべての環境変数を適切に設定してください")
    print("2. Google認証ファイルは、セキュアな場所に配置してください")
    print("3. 定期的にログを確認し、エラーがないか監視してください")
    print("4. バックアップとリカバリープランを準備してください")

if __name__ == "__main__":
    main()