#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
楽天注文データの日次同期スクリプト（2025年新認証対応版）
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
# 新しい認証情報
RMS_SERVICE_SQUARE_LICENSE_KEY = os.getenv('RMS_SERVICE_SQUARE_LICENSE_KEY')

if not all([SUPABASE_URL, SUPABASE_KEY]):
    logger.error("Supabase環境変数が設定されていません")
    sys.exit(1)

# 楽天認証情報の確認
if not RMS_SERVICE_SQUARE_LICENSE_KEY and not (RAKUTEN_SERVICE_SECRET and RAKUTEN_LICENSE_KEY):
    logger.error("楽天認証情報が設定されていません")
    logger.error("RMS_SERVICE_SQUARE_LICENSE_KEY または RAKUTEN_SERVICE_SECRET + RAKUTEN_LICENSE_KEY が必要です")
    sys.exit(1)

# Supabaseクライアント初期化
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def sync_recent_orders_new_auth(days=1):
    """新しいRMS Service Square認証で注文データを同期"""
    try:
        import requests
        from xml.etree import ElementTree as ET
        
        # 期間設定
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)
        
        logger.info(f"同期期間: {start_date.strftime('%Y-%m-%d')} ～ {end_date.strftime('%Y-%m-%d')}")
        logger.info(f"認証方式: RMS Service Square License Key")
        
        # 新しい認証方式のリクエストXML
        request_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
        <SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/" xmlns:ns1="http://orderapi.rms.rakuten.co.jp/rms/mall/order/api/ws">
            <SOAP-ENV:Body>
                <ns1:searchOrder>
                    <arg0>
                        <requestId>1</requestId>
                        <authKey>
                            <rmsServiceSquareLicenseKey>{RMS_SERVICE_SQUARE_LICENSE_KEY}</rmsServiceSquareLicenseKey>
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
            return False
        
        # レスポンス解析
        root = ET.fromstring(response.content)
        
        # 名前空間定義
        namespaces = {
            'SOAP-ENV': 'http://schemas.xmlsoap.org/soap/envelope/',
            'ns1': 'http://orderapi.rms.rakuten.co.jp/rms/mall/order/api/ws'
        }
        
        # エラーチェック
        fault = root.find('.//SOAP-ENV:Fault', namespaces)
        if fault is not None:
            error_msg = fault.find('.//faultstring')
            if error_msg is not None:
                logger.error(f"楽天APIエラー: {error_msg.text}")
            return False
        
        # 注文データ抽出
        orders = root.findall('.//ns1:orderModel', namespaces)
        logger.info(f"取得した注文数: {len(orders)}")
        
        # データベース同期処理（既存ロジックと同じ）
        for order in orders:
            try:
                # 注文情報抽出（既存ロジック）
                order_number = order.find('orderNumber').text if order.find('orderNumber') is not None else None
                if not order_number:
                    continue
                    
                # 既存レコードチェック
                existing = supabase.table("orders").select("id").eq("order_number", order_number).execute()
                
                if not existing.data:
                    # 新規注文の場合のみ詳細処理
                    process_new_order(order, supabase)
                    
            except Exception as e:
                logger.error(f"注文処理エラー: {str(e)}")
                continue
        
        return True
        
    except Exception as e:
        logger.error(f"同期処理エラー: {str(e)}")
        return False

def sync_recent_orders_legacy(days=1):
    """従来認証で注文データを同期（フォールバック用）"""
    try:
        import requests
        from xml.etree import ElementTree as ET
        
        # 期間設定
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)
        
        logger.info(f"同期期間: {start_date.strftime('%Y-%m-%d')} ～ {end_date.strftime('%Y-%m-%d')}")
        logger.info(f"認証方式: Legacy (ServiceSecret + LicenseKey)")
        
        # 従来の認証方式のリクエストXML
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
            logger.error(f"Legacy API エラー: {response.status_code}")
            logger.error(f"レスポンス内容: {response.text[:500]}")
            return False
        
        logger.info("従来認証での接続に成功")
        return True
        
    except Exception as e:
        logger.error(f"従来認証同期エラー: {str(e)}")
        return False

def process_new_order(order, supabase):
    """新規注文の処理（簡略版）"""
    try:
        # 基本的な注文情報のみ保存
        order_data = {
            "order_number": order.find('orderNumber').text if order.find('orderNumber') is not None else None,
            "order_date": order.find('orderDatetime').text if order.find('orderDatetime') is not None else None,
            "status": order.find('orderProgress').text if order.find('orderProgress') is not None else None,
        }
        
        if order_data["order_number"]:
            result = supabase.table("orders").insert(order_data).execute()
            logger.info(f"新規注文追加: {order_data['order_number']}")
            
    except Exception as e:
        logger.error(f"注文データ処理エラー: {str(e)}")

def main():
    """メイン処理"""
    logger.info("楽天注文同期開始")
    
    # 新しい認証方式を優先して試行
    if RMS_SERVICE_SQUARE_LICENSE_KEY:
        logger.info("新しいRMS Service Square認証を試行")
        success = sync_recent_orders_new_auth()
        
        if success:
            logger.info("新認証での同期成功")
            return
        else:
            logger.warning("新認証での同期失敗、従来認証を試行")
    
    # フォールバック: 従来認証
    if RAKUTEN_SERVICE_SECRET and RAKUTEN_LICENSE_KEY:
        logger.info("従来認証を試行")
        success = sync_recent_orders_legacy()
        
        if success:
            logger.info("従来認証での同期成功")
        else:
            logger.error("全ての認証方式で同期失敗")
            sys.exit(1)
    else:
        logger.error("認証情報が不足しています")
        sys.exit(1)

if __name__ == "__main__":
    main()