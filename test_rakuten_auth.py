#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
楽天API認証テスト
"""

import os
import base64
import httpx
import asyncio
from dotenv import load_dotenv

# 環境変数の読み込み
load_dotenv()

async def test_rakuten_auth():
    """楽天API認証のテスト"""
    
    service_secret = os.getenv('RAKUTEN_SERVICE_SECRET')
    license_key = os.getenv('RAKUTEN_LICENSE_KEY')
    
    print("=" * 60)
    print("楽天API認証テスト")
    print("=" * 60)
    
    # 環境変数の確認
    print(f"Service Secret: {service_secret[:10]}..." if service_secret else "Service Secret: 未設定")
    print(f"License Key: {license_key[:10]}..." if license_key else "License Key: 未設定")
    
    if not service_secret or not license_key:
        print("\n❌ エラー: 認証情報が設定されていません")
        return
    
    # 認証ヘッダーの生成
    auth_string = f"{service_secret}:{license_key}"
    encoded_auth = base64.b64encode(auth_string.encode('utf-8')).decode('utf-8')
    
    print(f"\n認証文字列（最初の20文字）: {encoded_auth[:20]}...")
    
    headers = {
        'Authorization': f'ESA {encoded_auth}',
        'Content-Type': 'application/json; charset=utf-8'
    }
    
    # テストリクエスト（本日の注文を検索）
    from datetime import datetime
    import pytz
    
    jst = pytz.timezone('Asia/Tokyo')
    today = datetime.now(jst)
    start_date = today.replace(hour=0, minute=0, second=0).strftime("%Y-%m-%dT%H:%M:%S+0900")
    end_date = today.replace(hour=23, minute=59, second=59).strftime("%Y-%m-%dT%H:%M:%S+0900")
    
    print(f"\n検索期間: {start_date} ~ {end_date}")
    url = 'https://api.rms.rakuten.co.jp/es/2.0/purchaseItem/searchOrderItem/'
    
    search_data = {
        "dateType": 1,
        "startDatetime": start_date,
        "endDatetime": end_date,
        "orderProgressList": [100],
        "PaginationRequestModel": {
            "requestRecordsAmount": 1,
            "requestPage": 1
        }
    }
    
    print("\nAPIリクエストを送信中...")
    print(f"URL: {url}")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers=headers,
                json=search_data,
                timeout=30.0
            )
            
            print(f"\nステータスコード: {response.status_code}")
            
            if response.status_code == 200:
                print("✅ 認証成功！")
                data = response.json()
                order_count = len(data.get('orderNumberList', []))
                print(f"本日の注文数: {order_count}件")
            else:
                print("❌ 認証失敗")
                print(f"レスポンス: {response.text}")
                
                if response.status_code == 401:
                    print("\n考えられる原因:")
                    print("1. Service SecretまたはLicense Keyが間違っている")
                    print("2. APIの利用権限がない")
                    print("3. 認証情報の有効期限が切れている")
                
    except Exception as e:
        print(f"\n❌ エラー発生: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_rakuten_auth())
