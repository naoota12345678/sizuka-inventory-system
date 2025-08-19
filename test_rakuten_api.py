#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
楽天API接続テスト用スクリプト
404エラーの原因を特定
"""

import os
import requests
from datetime import datetime, timedelta, timezone
import logging

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 環境変数
RAKUTEN_SERVICE_SECRET = os.getenv('RAKUTEN_SERVICE_SECRET', 'SP338531_d1NJjF2R5OwZpWH6')
RAKUTEN_LICENSE_KEY = os.getenv('RAKUTEN_LICENSE_KEY', 'SL338531_kUvqO4kIHaMbr9ik')

def test_rakuten_api_endpoints():
    """複数の楽天APIエンドポイントをテスト"""
    
    # テスト対象のエンドポイント
    endpoints = [
        'https://api.rms.rakuten.co.jp/es/1.0/order/ws',  # 現在使用中
        'https://api.rms.rakuten.co.jp/es/2.0/order/ws',  # v2.0の可能性
        'https://orderapi.rms.rakuten.co.jp/rms/mall/order/api/ws',  # SOAPエンドポイント
        'https://api.rakutenrmssdk.jp/es/1.0/order/ws',   # 新SDK
    ]
    
    # 期間設定
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=1)
    
    # リクエストXML
    request_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
    <SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/" xmlns:ns1="http://orderapi.rms.rakuten.co.jp/rms/mall/order/api/ws">
        <SOAP-ENV:Body>
            <ns1:searchOrder>
                <arg0>
                    <requestId>1</requestId>
                    <authKey>
                        <serviceSecret>{RAKUTEN_SERVICE_SECRET}</serviceSecret>
                        <licenseKey>{RAKUTEN_LICENSE_KEY}</licenseKey>
                    </authKey>
                    <shopUrl></shopUrl>
                    <userName>sizuka</userName>
                    <dateType>1</dateType>
                    <startDate>{start_date.strftime('%Y%m%d')}</startDate>
                    <endDate>{end_date.strftime('%Y%m%d')}</endDate>
                </arg0>
            </ns1:searchOrder>
        </SOAP-ENV:Body>
    </SOAP-ENV:Envelope>"""
    
    headers = {
        'Content-Type': 'text/xml; charset=utf-8',
        'SOAPAction': ''
    }
    
    for endpoint in endpoints:
        logger.info(f"テスト中: {endpoint}")
        
        try:
            response = requests.post(
                endpoint,
                data=request_xml.encode('utf-8'),
                headers=headers,
                timeout=30
            )
            
            logger.info(f"  ステータス: {response.status_code}")
            logger.info(f"  レスポンス: {response.text[:200]}...")
            
            if response.status_code == 200:
                logger.info(f"✅ 成功: {endpoint}")
                return endpoint
            elif response.status_code == 404:
                logger.warning(f"❌ 404エラー: {endpoint}")
            else:
                logger.warning(f"⚠️  その他エラー ({response.status_code}): {endpoint}")
                
        except Exception as e:
            logger.error(f"❌ 接続エラー: {endpoint} - {str(e)}")
    
    return None

def test_auth_format():
    """認証形式のテスト"""
    
    # 複数の認証形式をテスト
    auth_formats = [
        # 現在の形式
        f"""
        <authKey>
            <serviceSecret>{RAKUTEN_SERVICE_SECRET}</serviceSecret>
            <licenseKey>{RAKUTEN_LICENSE_KEY}</licenseKey>
        </authKey>
        """,
        
        # 新形式の可能性
        f"""
        <authKey>
            <clientId>{RAKUTEN_LICENSE_KEY}</clientId>
            <clientSecret>{RAKUTEN_SERVICE_SECRET}</clientSecret>
        </authKey>
        """,
        
        # ヘッダー認証の可能性
        ""
    ]
    
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=1)
    
    for i, auth_block in enumerate(auth_formats):
        logger.info(f"認証形式 {i+1} をテスト中...")
        
        if i == 2:  # ヘッダー認証の場合
            headers = {
                'Content-Type': 'text/xml; charset=utf-8',
                'Authorization': f'Bearer {RAKUTEN_SERVICE_SECRET}',
                'X-License-Key': RAKUTEN_LICENSE_KEY,
                'SOAPAction': ''
            }
            auth_xml = ""
        else:
            headers = {
                'Content-Type': 'text/xml; charset=utf-8',
                'SOAPAction': ''
            }
            auth_xml = auth_block
        
        request_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
        <SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/" xmlns:ns1="http://orderapi.rms.rakuten.co.jp/rms/mall/order/api/ws">
            <SOAP-ENV:Body>
                <ns1:searchOrder>
                    <arg0>
                        <requestId>1</requestId>
                        {auth_xml}
                        <shopUrl></shopUrl>
                        <userName>sizuka</userName>
                        <dateType>1</dateType>
                        <startDate>{start_date.strftime('%Y%m%d')}</startDate>
                        <endDate>{end_date.strftime('%Y%m%d')}</endDate>
                    </arg0>
                </ns1:searchOrder>
            </SOAP-ENV:Body>
        </SOAP-ENV:Envelope>"""
        
        try:
            response = requests.post(
                'https://api.rms.rakuten.co.jp/es/1.0/order/ws',
                data=request_xml.encode('utf-8'),
                headers=headers,
                timeout=30
            )
            
            logger.info(f"  認証形式 {i+1}: ステータス {response.status_code}")
            logger.info(f"  レスポンス: {response.text[:200]}...")
            
            if response.status_code == 200:
                logger.info(f"✅ 認証成功: 形式 {i+1}")
                return i+1
                
        except Exception as e:
            logger.error(f"❌ 認証テストエラー {i+1}: {str(e)}")
    
    return None

def main():
    """メインテスト実行"""
    logger.info("楽天API接続テスト開始")
    logger.info(f"SERVICE_SECRET: {RAKUTEN_SERVICE_SECRET[:10]}...")
    logger.info(f"LICENSE_KEY: {RAKUTEN_LICENSE_KEY[:10]}...")
    
    # エンドポイントテスト
    logger.info("\n=== エンドポイントテスト ===")
    working_endpoint = test_rakuten_api_endpoints()
    
    # 認証形式テスト
    logger.info("\n=== 認証形式テスト ===")
    working_auth = test_auth_format()
    
    # 結果サマリー
    logger.info("\n=== テスト結果 ===")
    if working_endpoint:
        logger.info(f"動作するエンドポイント: {working_endpoint}")
    else:
        logger.error("動作するエンドポイントが見つかりません")
        
    if working_auth:
        logger.info(f"動作する認証形式: {working_auth}")
    else:
        logger.error("動作する認証形式が見つかりません")

if __name__ == "__main__":
    main()