#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
楽天過去データ同期スクリプト
2024年6月から現在まで段階的にデータを同期
"""

import os
import requests
import json
import time
from datetime import datetime, timedelta
from supabase import create_client
import logging

# ロギング設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 環境変数（Cloud Runと同じ設定）
SUPABASE_URL = "https://equrcpeifogdrxoldkpe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6Im56nYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ"

# 楽天API設定（環境変数から取得）
RAKUTEN_SERVICE_SECRET = os.getenv('RAKUTEN_SERVICE_SECRET')
RAKUTEN_LICENSE_KEY = os.getenv('RAKUTEN_LICENSE_KEY')

class HistoricalRakutenSync:
    """楽天過去データ同期クラス"""
    
    def __init__(self):
        self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        self.service_secret = RAKUTEN_SERVICE_SECRET
        self.license_key = RAKUTEN_LICENSE_KEY
        
        if not self.service_secret or not self.license_key:
            raise ValueError("楽天API認証情報が設定されていません")
    
    def sync_monthly_data(self, year: int, month: int):
        """指定月のデータを同期"""
        
        # 月の開始日と終了日を計算
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = datetime(year, month + 1, 1) - timedelta(days=1)
        
        period_name = f"{year}年{month}月"
        logger.info(f"{period_name}のデータ同期を開始")
        
        try:
            # 楽天APIから注文データを取得
            orders = self.fetch_rakuten_orders(start_date, end_date)
            logger.info(f"{period_name}: {len(orders)}件の注文を取得")
            
            if not orders:
                logger.info(f"{period_name}: データなし")
                return {
                    'status': 'success',
                    'period': period_name,
                    'orders_count': 0,
                    'items_count': 0
                }
            
            # Supabaseに保存
            saved_orders = 0
            saved_items = 0
            
            for order in orders:
                # 注文データをSupabaseに保存
                if self.save_order_to_supabase(order):
                    saved_orders += 1
                
                # 注文商品データを保存
                for item in order.get('OrderItems', []):
                    if self.save_order_item_to_supabase(order['OrderId'], item):
                        saved_items += 1
                
                # APIレート制限対応（200ms待機）
                time.sleep(0.2)
            
            # platform_daily_salesも更新
            self.update_platform_daily_sales(year, month)
            
            logger.info(f"{period_name}同期完了: 注文{saved_orders}件、商品{saved_items}件")
            
            return {
                'status': 'success',
                'period': period_name,
                'orders_count': saved_orders,
                'items_count': saved_items
            }
            
        except Exception as e:
            logger.error(f"{period_name}同期エラー: {str(e)}")
            return {
                'status': 'error',
                'period': period_name,
                'message': str(e)
            }
    
    def fetch_rakuten_orders(self, start_date: datetime, end_date: datetime):
        """楽天APIから指定期間の注文データを取得"""
        
        orders = []
        page = 1
        max_pages = 100  # 安全のための上限
        
        while page <= max_pages:
            try:
                # 楽天注文検索API呼び出し
                params = {
                    'serviceSecret': self.service_secret,
                    'licenseKey': self.license_key,
                    'dateType': 1,  # 注文日
                    'startDate': start_date.strftime('%Y-%m-%d'),
                    'endDate': end_date.strftime('%Y-%m-%d'),
                    'PaginationRequestModel.requestRecordsAmount': 1000,
                    'PaginationRequestModel.requestPage': page
                }
                
                response = requests.get(
                    'https://api.rms.rakuten.co.jp/es/1.0/order/searchOrder/',
                    params=params,
                    timeout=30
                )
                
                if response.status_code != 200:
                    logger.error(f"楽天API呼び出しエラー: {response.status_code}")
                    break
                
                data = response.json()
                
                if 'orderModelList' not in data:
                    logger.warning(f"注文データが見つからない（ページ{page}）")
                    break
                
                page_orders = data['orderModelList']
                if not page_orders:
                    logger.info(f"データ終了（ページ{page}）")
                    break
                
                orders.extend(page_orders)
                logger.info(f"ページ{page}: {len(page_orders)}件取得（累計{len(orders)}件）")
                
                # 次のページへ
                page += 1
                
                # APIレート制限対応
                time.sleep(0.2)
                
            except Exception as e:
                logger.error(f"楽天API呼び出しエラー（ページ{page}）: {str(e)}")
                break
        
        return orders
    
    def save_order_to_supabase(self, order_data):
        """注文データをSupabaseに保存"""
        try:
            # 既存データ確認
            existing = self.supabase.table("orders").select("id").eq(
                "id", order_data['OrderId']
            ).execute()
            
            if existing.data:
                logger.debug(f"注文{order_data['OrderId']}は既存のためスキップ")
                return True
            
            # 注文データ変換
            order_record = {
                'id': order_data['OrderId'],
                'created_at': order_data['OrderDatetime'],
                'total_amount': float(order_data.get('TotalPrice', 0)),
                'order_status': order_data.get('OrderStatus', ''),
                'customer_name': order_data.get('DeliveryName', ''),
                'rakuten_order_data': json.dumps(order_data, ensure_ascii=False)
            }
            
            response = self.supabase.table("orders").insert(order_record).execute()
            return response.data is not None
            
        except Exception as e:
            logger.error(f"注文保存エラー({order_data.get('OrderId', 'N/A')}): {str(e)}")
            return False
    
    def save_order_item_to_supabase(self, order_id, item_data):
        """注文商品データをSupabaseに保存"""
        try:
            # 商品データ変換
            item_record = {
                'order_id': order_id,
                'rakuten_variant_id': item_data.get('VariantId', ''),
                'rakuten_item_number': item_data.get('ManageNumber', ''),
                'item_name': item_data.get('ItemName', ''),
                'unit_price': float(item_data.get('ItemPrice', 0)),
                'quantity': int(item_data.get('Units', 1)),
                'total_price': float(item_data.get('ItemPrice', 0)) * int(item_data.get('Units', 1)),
                'choice_code': self.extract_choice_code(item_data),
                'extended_rakuten_data': json.dumps(item_data, ensure_ascii=False)
            }
            
            response = self.supabase.table("order_items").insert(item_record).execute()
            return response.data is not None
            
        except Exception as e:
            logger.error(f"商品保存エラー({order_id}): {str(e)}")
            return False
    
    def extract_choice_code(self, item_data):
        """商品データから選択肢コードを抽出"""
        # 管理番号から選択肢コードを抽出
        manage_number = item_data.get('ManageNumber', '')
        if '-' in manage_number:
            return manage_number.split('-')[1]
        return ''
    
    def update_platform_daily_sales(self, year: int, month: int):
        """指定月のplatform_daily_salesを更新"""
        try:
            from rakuten_daily_aggregation import RakutenDailyAggregator
            
            aggregator = RakutenDailyAggregator()
            
            # 月の範囲を指定して集計
            start_date = f"{year}-{month:02d}-01"
            if month == 12:
                end_date = f"{year + 1}-01-31"
            else:
                end_date = f"{year}-{month + 1:02d}-31"
            
            result = aggregator.aggregate_daily_sales(start_date, end_date)
            
            if result['status'] == 'success':
                logger.info(f"{year}年{month}月のplatform_daily_sales更新完了")
            else:
                logger.error(f"platform_daily_sales更新エラー: {result['message']}")
                
        except Exception as e:
            logger.error(f"platform_daily_sales更新エラー: {str(e)}")
    
    def sync_period_range(self, start_year: int, start_month: int, end_year: int = None, end_month: int = None):
        """期間範囲での一括同期"""
        
        if not end_year:
            now = datetime.now()
            end_year = now.year
            end_month = now.month
        
        logger.info(f"期間同期開始: {start_year}年{start_month}月 ～ {end_year}年{end_month}月")
        
        results = []
        current_year = start_year
        current_month = start_month
        
        while (current_year < end_year) or (current_year == end_year and current_month <= end_month):
            result = self.sync_monthly_data(current_year, current_month)
            results.append(result)
            
            # 次の月へ
            if current_month == 12:
                current_year += 1
                current_month = 1
            else:
                current_month += 1
            
            # 月間での間隔調整（60秒待機）
            if result['status'] == 'success' and result['orders_count'] > 0:
                logger.info("次の月の処理まで60秒待機中...")
                time.sleep(60)
        
        # 結果サマリー
        total_orders = sum(r['orders_count'] for r in results if r['status'] == 'success')
        total_items = sum(r['items_count'] for r in results if r['status'] == 'success')
        success_months = len([r for r in results if r['status'] == 'success'])
        error_months = len([r for r in results if r['status'] == 'error'])
        
        logger.info(f"期間同期完了: 成功{success_months}ヶ月、エラー{error_months}ヶ月")
        logger.info(f"同期データ: 注文{total_orders}件、商品{total_items}件")
        
        return {
            'status': 'success',
            'summary': {
                'total_orders': total_orders,
                'total_items': total_items,
                'success_months': success_months,
                'error_months': error_months
            },
            'details': results
        }


def main():
    """メイン処理"""
    
    print("=== 楽天過去データ同期ツール ===\n")
    
    try:
        sync = HistoricalRakutenSync()
        
        # 2024年6月からの同期実行
        print("2024年6月から現在まで の同期を開始します...")
        print("注意: この処理には時間がかかります（各月60秒間隔）\n")
        
        result = sync.sync_period_range(2024, 6)
        
        if result['status'] == 'success':
            print("同期完了!")
            print(f"総注文数: {result['summary']['total_orders']}件")
            print(f"総商品数: {result['summary']['total_items']}件")
            print(f"成功月数: {result['summary']['success_months']}ヶ月")
            print(f"エラー月数: {result['summary']['error_months']}ヶ月")
        else:
            print(f"同期失敗: {result.get('message', 'Unknown error')}")
            
    except Exception as e:
        print(f"エラー: {str(e)}")
        print("楽天API認証情報を確認してください")


if __name__ == "__main__":
    main()