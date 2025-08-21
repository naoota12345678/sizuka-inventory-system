#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
楽天注文データの日次同期スクリプト（v2.0 API対応版）
GitHub Actions用
"""

import os
import sys
from datetime import datetime, timedelta, timezone
from supabase import create_client
import logging
import requests
import json
import base64

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 環境変数から設定を読み込み（フォールバックあり）
SUPABASE_URL = os.getenv('SUPABASE_URL', 'https://equrcpeifogdrxoldkpe.supabase.co')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ')
RAKUTEN_SERVICE_SECRET = os.getenv('RAKUTEN_SERVICE_SECRET')
RAKUTEN_LICENSE_KEY = os.getenv('RAKUTEN_LICENSE_KEY')

if not all([SUPABASE_URL, SUPABASE_KEY, RAKUTEN_SERVICE_SECRET, RAKUTEN_LICENSE_KEY]):
    logger.error("必要な環境変数が設定されていません")
    sys.exit(1)

# Supabaseクライアント初期化
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def sync_recent_orders(days=1):
    """最近の注文データを同期（v2.0 API使用）"""
    try:
        # 期間設定
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)
        
        logger.info(f"同期期間: {start_date.strftime('%Y-%m-%d')} ～ {end_date.strftime('%Y-%m-%d')}")
        logger.info("楽天API v2.0を使用")
        
        # 認証ヘッダーの作成
        # ESA Base64(serviceSecret:licenseKey)形式
        auth_string = f"{RAKUTEN_SERVICE_SECRET}:{RAKUTEN_LICENSE_KEY}"
        auth_bytes = auth_string.encode('utf-8')
        auth_b64 = base64.b64encode(auth_bytes).decode('utf-8')
        
        headers = {
            'Authorization': f'ESA {auth_b64}',
            'Content-Type': 'application/json; charset=utf-8'
        }
        
        # リクエストボディ（JSON形式）
        # まず注文番号リストを取得するためのリクエスト
        search_request = {
            "orderSearchModel": {
                "dateType": 1,  # 1: 注文日
                "startDate": start_date.strftime('%Y-%m-%d'),
                "endDate": end_date.strftime('%Y-%m-%d')
            }
        }
        
        # 注文番号リストを取得
        search_response = requests.post(
            'https://api.rms.rakuten.co.jp/es/2.0/order/searchOrder/',
            json=search_request,
            headers=headers,
            timeout=60
        )
        
        if search_response.status_code != 200:
            logger.error(f"注文検索API エラー: {search_response.status_code}")
            logger.error(f"レスポンス内容: {search_response.text[:500]}")
            return False
            
        search_data = search_response.json()
        order_numbers = search_data.get('orderNumberList', [])
        
        if not order_numbers:
            logger.info("新規注文がありません")
            return True
            
        logger.info(f"取得した注文番号数: {len(order_numbers)}")
        
        # 注文詳細を取得するためのリクエスト
        request_body = {
            "orderNumberList": order_numbers[:100]  # 最大100件まで
        }
        
        # APIリクエスト送信
        response = requests.post(
            'https://api.rms.rakuten.co.jp/es/2.0/purchaseItem/getOrderItem/',
            json=request_body,
            headers=headers,
            timeout=60
        )
        
        logger.info(f"APIレスポンスステータス: {response.status_code}")
        
        if response.status_code != 200:
            logger.error(f"API エラー: {response.status_code}")
            logger.error(f"レスポンス内容: {response.text[:500]}")
            return False
        
        # レスポンス解析
        response_data = response.json()
        
        # エラーチェック
        if 'errors' in response_data:
            logger.error(f"楽天APIエラー: {response_data['errors']}")
            return False
        
        # 注文データ取得
        orders = response_data.get('orderItemList', [])
        logger.info(f"取得した注文数: {len(orders)}")
        
        order_count = 0
        saved_count = 0
        
        # 各注文を処理
        for order in orders:
            try:
                order_number = order.get('orderNumber')
                
                if not order_number:
                    continue
                
                order_count += 1
                
                # 既存レコードチェック
                existing = supabase.table("orders").select("id").eq("order_number", order_number).execute()
                
                if existing.data:
                    logger.info(f"既存注文をスキップ: {order_number}")
                    continue
                
                # 注文データの作成
                order_date_str = order.get('orderDatetime')
                if order_date_str:
                    # ISO形式に変換
                    order_date = datetime.strptime(order_date_str, '%Y-%m-%d %H:%M:%S')
                    order_date = order_date.replace(tzinfo=timezone.utc)
                else:
                    order_date = datetime.now(timezone.utc)
                
                order_data = {
                    'order_number': order_number,
                    'order_date': order_date.isoformat(),
                    'platform': 'rakuten',
                    'status': str(order.get('orderProgress', '')),
                    'created_at': datetime.now(timezone.utc).isoformat()
                }
                
                # ordersテーブルに保存
                order_result = supabase.table('orders').insert(order_data).execute()
                
                if order_result.data:
                    order_id = order_result.data[0]['id']
                    
                    # 商品情報を処理
                    item_list = order.get('itemList', [])
                    for item in item_list:
                        try:
                            # 商品データの作成
                            item_data = {
                                'order_id': order_id,
                                'product_code': item.get('itemNumber', 'unknown'),
                                'product_name': item.get('itemName', ''),
                                'quantity': int(item.get('units', 1)),
                                'price': float(item.get('price', 0)),
                                'rakuten_item_number': item.get('itemNumber'),
                                'choice_code': item.get('selectedChoice', ''),
                                'created_at': datetime.now(timezone.utc).isoformat()
                            }
                            
                            # 選択肢コードの抽出（もし含まれている場合）
                            selected_choice = item.get('selectedChoice', '')
                            if selected_choice:
                                # 選択肢から選択肢コードを抽出
                                import re
                                match = re.search(r'[A-Z]\d{2}', selected_choice)
                                if match:
                                    item_data['choice_code'] = match.group()
                            
                            # order_itemsテーブルに保存
                            supabase.table('order_items').insert(item_data).execute()
                            
                        except Exception as e:
                            logger.error(f"商品データ保存エラー: {e}")
                    
                    saved_count += 1
                    logger.info(f"新規注文追加: {order_number}")
                    
            except Exception as e:
                logger.error(f"注文 {order_number} 保存エラー: {e}")
        
        logger.info(f"同期完了: {saved_count}/{order_count}件保存")
        return True
        
    except Exception as e:
        logger.error(f"同期エラー: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # 実行
    success = sync_recent_orders(days=1)
    
    if success:
        logger.info("同期処理が正常に完了しました")
    else:
        logger.error("同期処理でエラーが発生しました")
        sys.exit(1)