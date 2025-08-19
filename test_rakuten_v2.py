#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
楽天API v2.0 詳細テスト
"""

import os
import requests
import base64
import json
from datetime import datetime, timedelta

# 認証情報
RAKUTEN_SERVICE_SECRET = os.getenv('RAKUTEN_SERVICE_SECRET', 'SP338531_d1NJjF2R5OwZpWH6')
RAKUTEN_LICENSE_KEY = os.getenv('RAKUTEN_LICENSE_KEY', 'SL338531_kUvqO4kIHaMbr9ik')

def test_v2_api():
    """v2.0 APIテスト"""
    
    # 認証文字列作成
    auth_string = f"{RAKUTEN_SERVICE_SECRET}:{RAKUTEN_LICENSE_KEY}"
    auth_b64 = base64.b64encode(auth_string.encode('utf-8')).decode('utf-8')
    
    print(f"Service Secret: {RAKUTEN_SERVICE_SECRET[:10]}...")
    print(f"License Key: {RAKUTEN_LICENSE_KEY[:10]}...")
    print(f"Auth String: {auth_string[:20]}...")
    print(f"Base64: {auth_b64[:30]}...")
    
    # ヘッダー
    headers = {
        'Authorization': f'ESA {auth_b64}',
        'Content-Type': 'application/json; charset=utf-8'
    }
    
    print(f"\nHeaders: {headers}")
    
    # 期間設定
    end_date = datetime.now()
    start_date = end_date - timedelta(days=1)
    
    # リクエストボディ
    request_body = {
        "orderSearchModel": {
            "dateType": 1,
            "startDate": start_date.strftime('%Y-%m-%d'),
            "endDate": end_date.strftime('%Y-%m-%d')
        }
    }
    
    print(f"\nRequest Body: {json.dumps(request_body, indent=2)}")
    
    # APIリクエスト
    url = 'https://api.rms.rakuten.co.jp/es/2.0/purchaseItem/getOrderItem/'
    print(f"\nURL: {url}")
    
    try:
        response = requests.post(
            url,
            json=request_body,
            headers=headers,
            timeout=30
        )
        
        print(f"\nStatus Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print(f"Response Body: {response.text[:1000]}")
        
        if response.status_code == 404:
            print("\n❌ 404エラー: エンドポイントが見つかりません")
            print("URLまたはパスが間違っている可能性があります")
        elif response.status_code == 401:
            print("\n❌ 401エラー: 認証失敗")
            print("認証情報を確認してください")
        elif response.status_code == 400:
            print("\n⚠️ 400エラー: リクエスト形式エラー")
            try:
                error_detail = response.json()
                print(f"エラー詳細: {json.dumps(error_detail, indent=2)}")
            except:
                pass
        elif response.status_code == 200:
            print("\n✅ 成功!")
            
    except Exception as e:
        print(f"\n❌ エラー: {str(e)}")

if __name__ == "__main__":
    test_v2_api()