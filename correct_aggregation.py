#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
正しいカラム名での売上集計システム
order_date（実際の注文日）で集計する確定版
"""

from supabase import create_client
from datetime import datetime, timedelta
import logging

# ロギング設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

SUPABASE_URL = "https://equrcpeifogdrxoldkpe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ"

class CorrectSalesAggregator:
    """正しいカラム名での売上集計クラス"""
    
    def __init__(self):
        self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        # 確定したカラム名
        self.ORDERS_COLUMNS = {
            "date": "order_date",      # 実際の注文日
            "amount": "total_amount",  # 注文総額
            "id": "id",               # 注文ID
            "status": "status"        # ステータス
        }
        
        self.PLATFORM_COLUMNS = {
            "date": "sales_date",      # 売上日
            "amount": "total_amount",  # 売上額
            "count": "order_count",    # 注文数
            "platform": "platform"    # プラットフォーム
        }
    
    def aggregate_by_order_date(self, start_date: str = None, end_date: str = None):
        """実際の注文日（order_date）で集計"""
        
        # デフォルト期間設定
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
        if not start_date:
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            
        logger.info(f"集計期間: {start_date} ~ {end_date} (order_dateベース)")
        
        try:
            # order_dateで期間指定してデータ取得
            end_date_plus_one = (datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)).strftime('%Y-%m-%d')
            
            orders_response = self.supabase.table("orders").select(
                f"{self.ORDERS_COLUMNS['date']}, {self.ORDERS_COLUMNS['amount']}"
            ).gte(self.ORDERS_COLUMNS['date'], start_date).lt(self.ORDERS_COLUMNS['date'], end_date_plus_one).execute()
            
            orders = orders_response.data if orders_response.data else []
            logger.info(f"対象注文数: {len(orders)}件")
            
            # 日別に集計
            daily_totals = {}
            
            for order in orders:
                # 実際の注文日を抽出
                order_date = order.get(self.ORDERS_COLUMNS['date'], '')
                if order_date:
                    # 日付のみ抽出（YYYY-MM-DD）
                    if 'T' in order_date:
                        sales_date = order_date.split('T')[0]
                    else:
                        sales_date = order_date[:10]
                    
                    amount = float(order.get(self.ORDERS_COLUMNS['amount'], 0))
                    
                    # 日別集計
                    if sales_date not in daily_totals:
                        daily_totals[sales_date] = {
                            'total_amount': 0,
                            'order_count': 0
                        }
                    
                    daily_totals[sales_date]['total_amount'] += amount
                    daily_totals[sales_date]['order_count'] += 1
            
            # platform_daily_salesに保存
            success_count = 0
            error_count = 0
            
            for sales_date, totals in daily_totals.items():
                success = self._upsert_daily_sales(
                    sales_date=sales_date,
                    platform='rakuten',
                    total_amount=totals['total_amount'],
                    order_count=totals['order_count']
                )
                
                if success:
                    success_count += 1
                    logger.info(f"集計完了: {sales_date} - {totals['total_amount']:,.0f}円 ({totals['order_count']}件)")
                else:
                    error_count += 1
            
            logger.info(f"集計完了: 成功 {success_count}日分, エラー {error_count}日分")
            
            return {
                'status': 'success',
                'period': {'start_date': start_date, 'end_date': end_date},
                'total_days': len(daily_totals),
                'success_count': success_count,
                'error_count': error_count,
                'daily_totals': daily_totals
            }
            
        except Exception as e:
            logger.error(f"集計エラー: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def _upsert_daily_sales(self, sales_date: str, platform: str, total_amount: float, order_count: int):
        """日次売上データをupsert"""
        try:
            # 既存データ確認
            existing = self.supabase.table("platform_daily_sales").select("*").eq(
                self.PLATFORM_COLUMNS['date'], sales_date
            ).eq(self.PLATFORM_COLUMNS['platform'], platform).execute()
            
            data = {
                self.PLATFORM_COLUMNS['date']: sales_date,
                self.PLATFORM_COLUMNS['platform']: platform,
                self.PLATFORM_COLUMNS['amount']: round(total_amount, 2),
                self.PLATFORM_COLUMNS['count']: order_count
            }
            
            if existing.data:
                # 更新
                response = self.supabase.table("platform_daily_sales").update(data).eq(
                    self.PLATFORM_COLUMNS['date'], sales_date
                ).eq(self.PLATFORM_COLUMNS['platform'], platform).execute()
            else:
                # 新規挿入
                response = self.supabase.table("platform_daily_sales").insert(data).execute()
            
            return response.data is not None
            
        except Exception as e:
            logger.error(f"Upsertエラー ({sales_date}): {str(e)}")
            return False

def main():
    """テスト実行"""
    print("=== 正しいカラム名での売上集計テスト ===\n")
    
    aggregator = CorrectSalesAggregator()
    
    # 8月のデータを正しく集計
    result = aggregator.aggregate_by_order_date('2025-08-01', '2025-08-04')
    
    if result['status'] == 'success':
        print("✅ 集計成功!")
        print(f"期間: {result['period']['start_date']} ~ {result['period']['end_date']}")
        print(f"処理日数: {result['total_days']}日")
        print(f"成功: {result['success_count']}日")
        
        total_amount = sum(totals['total_amount'] for totals in result['daily_totals'].values())
        total_count = sum(totals['order_count'] for totals in result['daily_totals'].values())
        
        print(f"\n【正しい8月の売上】")
        for date in sorted(result['daily_totals'].keys()):
            totals = result['daily_totals'][date]
            avg = totals['total_amount'] / totals['order_count'] if totals['order_count'] > 0 else 0
            print(f"{date}: {totals['total_amount']:,.0f}円 ({totals['order_count']}件) [平均: {avg:,.0f}円]")
        
        print(f"\n合計: {total_amount:,.0f}円 ({total_count}件)")
        print(f"平均単価: {total_amount/total_count:,.0f}円")
        
    else:
        print(f"❌ 集計失敗: {result['message']}")

if __name__ == "__main__":
    main()