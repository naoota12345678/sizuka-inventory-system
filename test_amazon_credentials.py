#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Amazon認証情報テストスクリプト
GitHub Actionsで設定されたSecretsが正しく動作するかテスト
"""

import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_amazon_credentials():
    """Amazon認証情報のテスト"""
    
    print("=== Amazon認証情報テスト ===")
    
    # 必要な環境変数の確認
    required_vars = [
        'AMAZON_CLIENT_ID',
        'AMAZON_CLIENT_SECRET', 
        'AMAZON_REFRESH_TOKEN'
    ]
    
    optional_vars = [
        'AMAZON_MARKETPLACE_ID',
        'AMAZON_REGION'
    ]
    
    all_present = True
    
    print("必須認証情報:")
    for var in required_vars:
        value = os.getenv(var)
        if value:
            print(f"  ✅ {var}: {'*' * min(len(value), 20)} (長さ: {len(value)})")
        else:
            print(f"  ❌ {var}: 未設定")
            all_present = False
    
    print("\nオプション設定:")
    for var in optional_vars:
        value = os.getenv(var)
        if value:
            print(f"  ✅ {var}: {value}")
        else:
            print(f"  ⚠️  {var}: デフォルト値使用")
    
    # Supabase認証情報も確認
    print("\nSupabase認証情報:")
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_KEY')
    
    if supabase_url:
        print(f"  ✅ SUPABASE_URL: {supabase_url}")
    else:
        print("  ❌ SUPABASE_URL: 未設定")
        all_present = False
        
    if supabase_key:
        print(f"  ✅ SUPABASE_KEY: {'*' * 20}... (長さ: {len(supabase_key)})")
    else:
        print("  ❌ SUPABASE_KEY: 未設定") 
        all_present = False
    
    print("\n=== 結果 ===")
    if all_present:
        print("✅ すべての必須認証情報が設定されています")
        print("Amazon SP-API同期の準備が完了しています")
        return True
    else:
        print("❌ 一部の認証情報が不足しています")
        print("GitHub Secretsの設定を確認してください")
        return False

def test_amazon_sp_api_connection():
    """Amazon SP-API接続テスト（簡易版）"""
    
    print("\n=== Amazon SP-API接続テスト ===")
    
    try:
        import requests
        
        client_id = os.getenv('AMAZON_CLIENT_ID')
        client_secret = os.getenv('AMAZON_CLIENT_SECRET')
        refresh_token = os.getenv('AMAZON_REFRESH_TOKEN')
        
        if not all([client_id, client_secret, refresh_token]):
            print("❌ 認証情報不足のため接続テストをスキップ")
            return False
        
        # LWAトークン取得テスト
        token_url = "https://api.amazon.com/auth/o2/token"
        token_data = {
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token,
            'client_id': client_id,
            'client_secret': client_secret
        }
        
        print("アクセストークン取得テスト中...")
        response = requests.post(token_url, data=token_data, timeout=10)
        
        if response.status_code == 200:
            token_info = response.json()
            print("✅ アクセストークン取得成功")
            print(f"  トークンタイプ: {token_info.get('token_type', 'N/A')}")
            print(f"  有効期限: {token_info.get('expires_in', 'N/A')}秒")
            return True
        else:
            print(f"❌ アクセストークン取得失敗: {response.status_code}")
            print(f"  レスポンス: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 接続テストエラー: {str(e)}")
        return False

if __name__ == "__main__":
    credentials_ok = test_amazon_credentials()
    
    if credentials_ok:
        connection_ok = test_amazon_sp_api_connection()
        
        if connection_ok:
            print("\n🎉 Amazon統合テスト完全成功!")
            print("Amazon注文同期が動作可能です")
        else:
            print("\n⚠️  認証情報は設定済みですが、API接続に問題があります")
            print("Amazon Developer Consoleで設定を確認してください")
    else:
        print("\n❌ 認証情報の設定が必要です")