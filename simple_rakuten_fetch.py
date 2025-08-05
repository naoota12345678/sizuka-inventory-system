#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
シンプルな楽天API呼び出しテスト
認証情報を直接設定して動作確認
"""

import os
import base64
import httpx
import json
from datetime import datetime, timedelta
import pytz
from supabase import create_client

# 認証情報を直接設定
SERVICE_SECRET = "SP338531_d1NJjF2R5OwZpWH6"
LICENSE_KEY = "SL338531_kUvqO4kIHaMbr9ik"

SUPABASE_URL = "https://equrcpeifogdrxoldkpe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ"

def test_rakuten_api():
    """楽天API接続テスト"""
    
    print("=== 楽天API接続テスト ===")
    
    # 認証ヘッダーの生成
    auth_string = f"{SERVICE_SECRET}:{LICENSE_KEY}"
    encoded_auth = base64.b64encode(auth_string.encode('utf-8')).decode('utf-8')
    
    headers = {
        'Authorization': f'ESA {encoded_auth}',
        'Content-Type': 'application/json; charset=utf-8'
    }
    
    base_url = 'https://api.rms.rakuten.co.jp/es/2.0'
    jst = pytz.timezone('Asia/Tokyo')
    
    # テスト期間（過去30日）
    end_date = datetime.now(jst)
    start_date = end_date - timedelta(days=30)
    
    jst_st = start_date.strftime("%Y-%m-%dT%H:%M:%S+0900")
    jst_ed = end_date.strftime("%Y-%m-%dT%H:%M:%S+0900")
    
    print(f"検索期間: {jst_st} ～ {jst_ed}")
    
    # 注文検索API
    url = f'{base_url}/purchaseItem/searchOrderItem/'
    search_data = {
        "dateType": 1,
        "startDatetime": jst_st,
        "endDatetime": jst_ed,
        "orderProgressList": [100, 200, 300, 400, 500, 600, 700],
        "PaginationRequestModel": {
            "requestRecordsAmount": 100,
            "requestPage": 1
        }
    }
    
    try:
        with httpx.Client() as client:
            print("楽天APIに接続中...")
            response = client.post(
                url,
                headers=headers,
                json=search_data,
                timeout=30.0
            )
            
            print(f"レスポンスステータス: {response.status_code}")
            
            if response.status_code == 401:
                print("認証エラー: 認証情報を確認してください")
                return False
            
            response.raise_for_status()
            data = response.json()
            
            order_numbers = data.get('orderNumberList', [])
            print(f"取得した注文数: {len(order_numbers)}件")
            
            if order_numbers:
                print("サンプル注文番号:")
                for i, order_num in enumerate(order_numbers[:5]):
                    print(f"  {i+1}: {order_num}")
                
                # 詳細取得のテスト（最初の1件のみ）
                print("\n注文詳細を取得中...")
                detail_url = f'{base_url}/purchaseItem/getOrderItem/'
                detail_data = {'orderNumberList': [order_numbers[0]]}
                
                detail_response = client.post(
                    detail_url,
                    headers=headers,
                    json=detail_data,
                    timeout=30.0
                )
                
                if detail_response.status_code == 200:
                    detail_data = detail_response.json()
                    orders = detail_data.get('OrderModelList', [])
                    if orders:
                        order = orders[0]
                        print(f"注文番号: {order.get('orderNumber')}")
                        print(f"注文日: {order.get('orderDatetime')}")
                        print(f"合計金額: {order.get('totalPrice', 0):,}円")
                        print("楽天API接続成功！")
                        return True
            else:
                print("指定期間に注文データがありません")
                return True
                
    except Exception as e:
        print(f"APIエラー: {str(e)}")
        return False

def check_current_data():
    """現在のSupabaseデータを確認"""
    print("\n=== 現在のデータ状況 ===")
    
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # ordersテーブルの状況
    orders_resp = supabase.table('orders').select('order_date').execute()
    
    from collections import defaultdict
    monthly_counts = defaultdict(int)
    
    for order in orders_resp.data:
        month = order['order_date'][:7]
        monthly_counts[month] += 1
    
    print("現在のordersテーブル:")
    for month in sorted(monthly_counts.keys()):
        print(f"  {month}: {monthly_counts[month]}件")
    
    print(f"合計: {len(orders_resp.data)}件")
    
    # platform_daily_salesの状況
    sales_resp = supabase.table('platform_daily_sales').select('*').eq('platform', 'rakuten').execute()
    print(f"\nplatform_daily_sales: {len(sales_resp.data)}日分のデータ")

def main():
    print("楽天API動作確認")
    print("在庫管理システムで使用している認証情報でテストします\n")
    
    # 現在のデータ状況確認
    check_current_data()
    
    # API接続テスト
    if test_rakuten_api():
        print("\n楽天APIは正常に動作しています")
        print("過去1年分のデータ取得を実行できます")
    else:
        print("\n楽天API接続に問題があります")

if __name__ == "__main__":
    main()