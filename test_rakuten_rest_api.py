#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
楽天REST API接続テスト
SOAP APIの代わりにREST APIを試す
"""

import os
import requests
from datetime import datetime, timedelta
import logging
import base64
import hashlib
import time

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 環境変数
RAKUTEN_SERVICE_SECRET = os.getenv('RAKUTEN_SERVICE_SECRET', 'SP338531_d1NJjF2R5OwZpWH6')
RAKUTEN_LICENSE_KEY = os.getenv('RAKUTEN_LICENSE_KEY', 'SL338531_kUvqO4kIHaMbr9ik')

def test_rest_api():
    """楽天REST API形式をテスト"""
    
    # テスト対象のエンドポイント
    endpoints = [
        # REST API エンドポイント候補
        'https://api.rms.rakuten.co.jp/es/2.0/order/searchOrder/',
        'https://api.rms.rakuten.co.jp/es/1.0/order/searchOrder/',
        'https://api.rms.rakuten.co.jp/rms/order/searchOrder',
        
        # 異なるベースURL
        'https://api.rms.rakuten.ne.jp/es/1.0/order/ws',
        'https://api.rms.rakuten.jp/es/1.0/order/ws',
    ]
    
    # 期間設定
    end_date = datetime.now()
    start_date = end_date - timedelta(days=1)
    
    for endpoint in endpoints:
        logger.info(f"テスト中: {endpoint}")
        
        # 認証ヘッダーパターン1: Basic認証
        auth_string = f"{RAKUTEN_LICENSE_KEY}:{RAKUTEN_SERVICE_SECRET}"
        auth_bytes = auth_string.encode('utf-8')
        auth_b64 = base64.b64encode(auth_bytes).decode('utf-8')
        
        headers1 = {
            'Authorization': f'Basic {auth_b64}',
            'Content-Type': 'application/json'
        }
        
        # 認証ヘッダーパターン2: ESA形式
        headers2 = {
            'Authorization': f'ESA {RAKUTEN_SERVICE_SECRET}:{RAKUTEN_LICENSE_KEY}',
            'Content-Type': 'application/json'
        }
        
        # 認証ヘッダーパターン3: 個別ヘッダー
        headers3 = {
            'X-RMS-Service-Secret': RAKUTEN_SERVICE_SECRET,
            'X-RMS-License-Key': RAKUTEN_LICENSE_KEY,
            'Content-Type': 'application/json'
        }
        
        # リクエストボディ（JSON形式）
        request_body = {
            'dateType': 1,
            'startDate': start_date.strftime('%Y%m%d'),
            'endDate': end_date.strftime('%Y%m%d')
        }
        
        for i, headers in enumerate([headers1, headers2, headers3], 1):
            try:
                response = requests.post(
                    endpoint,
                    json=request_body,
                    headers=headers,
                    timeout=30
                )
                
                logger.info(f"  認証パターン{i}: ステータス {response.status_code}")
                
                if response.status_code == 200:
                    logger.info(f"✅ 成功: {endpoint} with 認証パターン{i}")
                    logger.info(f"レスポンス: {response.text[:200]}...")
                    return endpoint, i
                elif response.status_code == 401:
                    logger.warning(f"❌ 認証エラー: {endpoint} with 認証パターン{i}")
                elif response.status_code == 404:
                    logger.warning(f"❌ 404エラー: {endpoint} with 認証パターン{i}")
                    break  # このエンドポイントは存在しない
                else:
                    logger.warning(f"⚠️ その他エラー ({response.status_code}): {response.text[:100]}")
                    
            except Exception as e:
                logger.error(f"❌ 接続エラー: {endpoint} - {str(e)}")
                break
                
        time.sleep(1)  # レート制限対策
    
    return None, None

def test_api_info():
    """APIのステータス情報を取得"""
    
    # API情報エンドポイント
    info_endpoints = [
        'https://api.rms.rakuten.co.jp/es/1.0/system/status',
        'https://api.rms.rakuten.co.jp/status',
        'https://webservice.rakuten.co.jp/api/status',
    ]
    
    for endpoint in info_endpoints:
        logger.info(f"APIステータス確認: {endpoint}")
        
        try:
            response = requests.get(endpoint, timeout=10)
            logger.info(f"  ステータス: {response.status_code}")
            
            if response.status_code < 500:
                logger.info(f"  レスポンス: {response.text[:200]}...")
                
        except Exception as e:
            logger.error(f"  エラー: {str(e)}")

def main():
    """メインテスト実行"""
    logger.info("楽天REST API接続テスト開始")
    logger.info(f"SERVICE_SECRET: {RAKUTEN_SERVICE_SECRET[:10]}...")
    logger.info(f"LICENSE_KEY: {RAKUTEN_LICENSE_KEY[:10]}...")
    
    # APIステータス確認
    logger.info("\n=== APIステータス確認 ===")
    test_api_info()
    
    # REST APIテスト
    logger.info("\n=== REST APIテスト ===")
    working_endpoint, working_auth = test_rest_api()
    
    # 結果サマリー
    logger.info("\n=== テスト結果 ===")
    if working_endpoint:
        logger.info(f"✅ 動作するエンドポイント: {working_endpoint}")
        logger.info(f"✅ 動作する認証パターン: {working_auth}")
    else:
        logger.error("❌ 動作するエンドポイントが見つかりません")
        logger.info("\n楽天APIのエンドポイントが変更された可能性があります。")
        logger.info("楽天RMS管理画面で最新のAPI仕様書を確認してください。")

if __name__ == "__main__":
    main()