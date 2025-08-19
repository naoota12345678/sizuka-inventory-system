#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
楽天注文データの日次同期スクリプト
GitHub Actions用
"""

import os
import sys
from datetime import datetime, timedelta, timezone
from supabase import create_client
import logging

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 環境変数から設定を読み込み
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
RAKUTEN_SERVICE_SECRET = os.getenv('RAKUTEN_SERVICE_SECRET')
RAKUTEN_LICENSE_KEY = os.getenv('RAKUTEN_LICENSE_KEY')

if not all([SUPABASE_URL, SUPABASE_KEY, RAKUTEN_SERVICE_SECRET, RAKUTEN_LICENSE_KEY]):
    logger.error("必要な環境変数が設定されていません")
    sys.exit(1)

# Supabaseクライアント初期化
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def sync_recent_orders(days=1):
    """最近の注文データを同期"""
    try:
        import requests
        from xml.etree import ElementTree as ET
        
        # 期間設定
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)
        
        logger.info(f"同期期間: {start_date.strftime('%Y-%m-%d')} ～ {end_date.strftime('%Y-%m-%d')}")
        
        # 楽天APIリクエスト作成
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
        
        # APIリクエスト送信
        headers = {
            'Content-Type': 'text/xml; charset=utf-8',
            'SOAPAction': ''
        }
        
        response = requests.post(
            'https://api.rms.rakuten.co.jp/es/1.0/order/ws',
            data=request_xml.encode('utf-8'),
            headers=headers,
            timeout=60
        )
        
        if response.status_code != 200:
            logger.error(f"API エラー: {response.status_code}")
            logger.error(f"レスポンス内容: {response.text[:500]}")
            logger.error(f"リクエストURL: {response.url}")
            logger.error(f"リクエストヘッダー: {headers}")
            return False
        
        # レスポンス解析
        root = ET.fromstring(response.content)
        
        # 名前空間定義
        namespaces = {
            'SOAP-ENV': 'http://schemas.xmlsoap.org/soap/envelope/',
            'ns1': 'http://orderapi.rms.rakuten.co.jp/rms/mall/order/api/ws'
        }
        
        # 注文データ取得
        orders_element = root.find('.//ns1:searchOrderReturn', namespaces)
        if orders_element is None:
            logger.info("新規注文データなし")
            return True
        
        order_count = 0
        saved_count = 0
        
        # 各注文を処理
        for order_elem in orders_element.findall('.//orderModel', namespaces):
            try:
                order_number = order_elem.find('orderNumber').text if order_elem.find('orderNumber') is not None else None
                
                if not order_number:
                    continue
                
                order_count += 1
                
                # 注文データの作成
                order_date_str = order_elem.find('orderDate').text if order_elem.find('orderDate') is not None else None
                order_date = datetime.strptime(order_date_str, '%Y-%m-%d %H:%M:%S') if order_date_str else datetime.now(timezone.utc)
                
                order_data = {
                    'order_number': order_number,
                    'order_date': order_date.isoformat(),
                    'platform': 'rakuten',
                    'created_at': datetime.now(timezone.utc).isoformat()
                }
                
                # ordersテーブルに保存
                order_result = supabase.table('orders').upsert(
                    order_data,
                    on_conflict='order_number'
                ).execute()
                
                if order_result.data:
                    order_id = order_result.data[0]['id']
                    
                    # 商品情報を処理
                    items_element = order_elem.find('itemList')
                    if items_element:
                        for item_elem in items_element.findall('itemModel'):
                            try:
                                item_data = {
                                    'order_id': order_id,
                                    'product_code': item_elem.find('itemNumber').text if item_elem.find('itemNumber') is not None else 'unknown',
                                    'product_name': item_elem.find('itemName').text if item_elem.find('itemName') is not None else '',
                                    'quantity': int(item_elem.find('units').text) if item_elem.find('units') is not None else 1,
                                    'price': float(item_elem.find('price').text) if item_elem.find('price') is not None else 0,
                                    'created_at': datetime.now(timezone.utc).isoformat()
                                }
                                
                                # order_itemsテーブルに保存
                                supabase.table('order_items').insert(item_data).execute()
                                
                            except Exception as e:
                                logger.error(f"商品データ保存エラー: {e}")
                    
                    saved_count += 1
                    
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
    sys.exit(0 if success else 1)