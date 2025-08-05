#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
楽天API 過去1年分データ取得（シンプル版）
認証情報を直接設定して確実に動作させる
"""

import base64
import httpx
import json
from datetime import datetime, timedelta
import pytz
from supabase import create_client
import time
import logging

# ロギング設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 認証情報を直接設定
SERVICE_SECRET = "SP338531_d1NJjF2R5OwZpWH6"
LICENSE_KEY = "SL338531_kUvqO4kIHaMbr9ik"

SUPABASE_URL = "https://equrcpeifogdrxoldkpe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ"

class SimpleRakutenFetcher:
    """シンプルな楽天データ取得クラス"""
    
    def __init__(self):
        # 認証ヘッダーの生成
        auth_string = f"{SERVICE_SECRET}:{LICENSE_KEY}"
        encoded_auth = base64.b64encode(auth_string.encode('utf-8')).decode('utf-8')
        
        self.headers = {
            'Authorization': f'ESA {encoded_auth}',
            'Content-Type': 'application/json; charset=utf-8'
        }
        self.base_url = 'https://api.rms.rakuten.co.jp/es/2.0'
        self.jst = pytz.timezone('Asia/Tokyo')
        self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    def get_orders_in_period(self, start_date, end_date):
        """指定期間の注文を取得"""
        
        jst_st = start_date.strftime("%Y-%m-%dT%H:%M:%S+0900")
        jst_ed = end_date.strftime("%Y-%m-%dT%H:%M:%S+0900")
        
        url = f'{self.base_url}/purchaseItem/searchOrderItem/'
        search_data = {
            "dateType": 1,
            "startDatetime": jst_st,
            "endDatetime": jst_ed,
            "orderProgressList": [100, 200, 300, 400, 500, 600, 700],
            "PaginationRequestModel": {
                "requestRecordsAmount": 1000,
                "requestPage": 1
            }
        }
        
        try:
            with httpx.Client() as client:
                response = client.post(
                    url,
                    headers=self.headers,
                    json=search_data,
                    timeout=30.0
                )
                
                response.raise_for_status()
                data = response.json()
                order_numbers = data.get('orderNumberList', [])
                
                if order_numbers:
                    return self.get_order_details(order_numbers)
                return []
                
        except Exception as e:
            logger.error(f"注文取得エラー: {str(e)}")
            return []
    
    def get_order_details(self, order_numbers):
        """注文詳細を取得"""
        url = f'{self.base_url}/purchaseItem/getOrderItem/'
        chunk_size = 100
        all_orders = []
        
        for i in range(0, len(order_numbers), chunk_size):
            chunk = order_numbers[i:i + chunk_size]
            order_data = {'orderNumberList': chunk}
            
            try:
                with httpx.Client() as client:
                    response = client.post(
                        url,
                        headers=self.headers,
                        json=order_data,
                        timeout=30.0
                    )
                    
                    response.raise_for_status()
                    data = response.json()
                    
                    if 'OrderModelList' in data:
                        all_orders.extend(data['OrderModelList'])
                    
            except Exception as e:
                logger.error(f"詳細取得エラー: {str(e)}")
                continue
        
        return all_orders
    
    def save_orders_to_supabase(self, orders):
        """注文をSupabaseに保存"""
        success_count = 0
        error_count = 0
        
        for order in orders:
            try:
                # 注文データの準備
                order_data = {
                    "order_number": order.get('orderNumber'),
                    "order_date": order.get('orderDatetime'),
                    "total_amount": float(order.get('totalPrice', 0)),
                    "customer_name": order.get('deliveryName', ''),
                    "platform": "rakuten",
                    "raw_data": json.dumps(order, ensure_ascii=False)
                }
                
                # 重複チェック
                existing = self.supabase.table("orders").select("id").eq(
                    "order_number", order_data["order_number"]
                ).execute()
                
                if existing.data:
                    # 更新
                    self.supabase.table("orders").update(order_data).eq(
                        "order_number", order_data["order_number"]
                    ).execute()
                else:
                    # 新規挿入
                    self.supabase.table("orders").insert(order_data).execute()
                
                success_count += 1
                
            except Exception as e:
                logger.error(f"保存エラー ({order.get('orderNumber')}): {str(e)}")
                error_count += 1
        
        return {"success": success_count, "error": error_count}
    
    def fetch_yearly_data(self):
        """過去1年分のデータを取得"""
        
        logger.info("=== 過去1年分データ取得開始 ===")
        
        # 期間設定
        end_date = datetime.now(self.jst)
        start_date = end_date - timedelta(days=365)
        
        logger.info(f"取得期間: {start_date.strftime('%Y-%m-%d')} ～ {end_date.strftime('%Y-%m-%d')}")
        
        # 月単位で処理
        current_date = start_date
        total_orders = []
        monthly_summary = {}
        
        while current_date < end_date:
            # 月の期間を計算
            month_start = current_date
            if current_date.month == 12:
                month_end = datetime(current_date.year + 1, 1, 1, tzinfo=self.jst)
            else:
                month_end = datetime(current_date.year, current_date.month + 1, 1, tzinfo=self.jst)
            
            if month_end > end_date:
                month_end = end_date
            
            month_str = month_start.strftime('%Y-%m')
            logger.info(f"処理中: {month_str}")
            
            try:
                # 注文取得
                orders = self.get_orders_in_period(month_start, month_end)
                
                if orders:
                    logger.info(f"{month_str}: {len(orders)}件取得")
                    
                    # 保存
                    save_result = self.save_orders_to_supabase(orders)
                    
                    # 売上合計計算
                    month_total = sum(float(order.get('totalPrice', 0)) for order in orders)
                    
                    monthly_summary[month_str] = {
                        'orders': len(orders),
                        'saved': save_result['success'],
                        'errors': save_result['error'],
                        'amount': month_total
                    }
                    
                    total_orders.extend(orders)
                    logger.info(f"{month_str}: 保存完了 {save_result['success']}件")
                else:
                    logger.info(f"{month_str}: データなし")
                    monthly_summary[month_str] = {'orders': 0, 'saved': 0, 'errors': 0, 'amount': 0}
                
            except Exception as e:
                logger.error(f"{month_str}: エラー {str(e)}")
                monthly_summary[month_str] = {'orders': 0, 'saved': 0, 'errors': 1, 'amount': 0}
            
            current_date = month_end
            time.sleep(2)  # API制限考慮
        
        # 結果サマリー
        total_saved = sum(m['saved'] for m in monthly_summary.values())
        total_amount = sum(m['amount'] for m in monthly_summary.values())
        
        logger.info("=== 取得完了 ===")
        logger.info(f"総注文数: {len(total_orders)}件")
        logger.info(f"保存成功: {total_saved}件")
        logger.info(f"総売上: {total_amount:,.0f}円")
        
        # 日次集計更新
        logger.info("日次売上集計を更新中...")
        from efficient_sales_sync import EfficientSalesSync
        sync = EfficientSalesSync()
        sync_result = sync.sync_all_sales()
        
        return {
            'total_orders': len(total_orders),
            'total_saved': total_saved,
            'total_amount': total_amount,
            'monthly_summary': monthly_summary,
            'sync_result': sync_result
        }

def main():
    print("=== 楽天API 過去1年分データ取得（確実版） ===")
    print("在庫管理システムと同じ認証情報で楽天APIからデータを取得します\n")
    
    fetcher = SimpleRakutenFetcher()
    
    try:
        result = fetcher.fetch_yearly_data()
        
        print("\n過去1年分のデータ取得が完了しました！")
        print(f"総注文数: {result['total_orders']}件")
        print(f"保存成功: {result['total_saved']}件")
        print(f"総売上: {result['total_amount']:,.0f}円")
        
        # 月別サマリー
        print("\n月別サマリー:")
        for month, data in sorted(result['monthly_summary'].items()):
            if data['orders'] > 0:
                print(f"  {month}: {data['orders']}件, {data['amount']:,.0f}円")
        
        # 日次集計結果
        if result['sync_result']['status'] == 'success':
            print(f"\n日次売上集計: {result['sync_result']['total_days']}日分更新完了")
        
        print("\nダッシュボードで確認: https://sizuka-inventory-system-p2wv4efvja-an.a.run.app/platform-sales")
        
    except Exception as e:
        print(f"エラーが発生しました: {str(e)}")

if __name__ == "__main__":
    main()