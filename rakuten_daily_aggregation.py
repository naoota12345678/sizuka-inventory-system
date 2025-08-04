#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
楽天データから日次売上集計処理
Phase 1 Step 2: 既存の orders/order_items から platform_daily_sales へ集計
"""

from supabase import create_client
from datetime import datetime, timedelta
from decimal import Decimal
import logging

# ロギング設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

SUPABASE_URL = "https://equrcpeifogdrxoldkpe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ"

class RakutenDailyAggregator:
    """楽天売上日次集計クラス"""
    
    def __init__(self):
        self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        
    def aggregate_daily_sales(self, start_date: str = None, end_date: str = None):
        """指定期間の日次売上を集計"""
        
        # デフォルト期間設定（過去30日）
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
        if not start_date:
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            
        logger.info(f"集計期間: {start_date} ~ {end_date}")
        
        # 期間内の注文データを取得
        try:
            # ordersテーブルから日別集計を取得
            # 注意: lte()ではなくlt()を使用（タイムスタンプ対応）
            from datetime import datetime, timedelta
            end_date_plus_one = (datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)).strftime('%Y-%m-%d')
            
            orders_response = self.supabase.table("orders").select(
                "created_at, total_amount"
            ).gte("created_at", start_date).lt("created_at", end_date_plus_one).execute()
            
            orders = orders_response.data if orders_response.data else []
            logger.info(f"対象注文数: {len(orders)}件")
            
            # 日別に集計
            daily_totals = {}
            
            for order in orders:
                # 日付を抽出（YYYY-MM-DD形式）
                created_at = order.get('created_at', '')
                if 'T' in created_at:
                    sales_date = created_at.split('T')[0]
                else:
                    sales_date = created_at[:10]
                
                total_amount = float(order.get('total_amount', 0))
                
                # 日別集計
                if sales_date not in daily_totals:
                    daily_totals[sales_date] = {
                        'total_amount': 0,
                        'order_count': 0
                    }
                
                daily_totals[sales_date]['total_amount'] += total_amount
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
        """日次売上データをupsert（挿入または更新）"""
        try:
            # 既存データ確認
            existing = self.supabase.table("platform_daily_sales").select("*").eq(
                "sales_date", sales_date
            ).eq("platform", platform).execute()
            
            data = {
                "sales_date": sales_date,
                "platform": platform,
                "total_amount": round(total_amount, 2),
                "order_count": order_count
            }
            
            if existing.data:
                # 更新
                response = self.supabase.table("platform_daily_sales").update(data).eq(
                    "sales_date", sales_date
                ).eq("platform", platform).execute()
                logger.debug(f"更新: {sales_date} - {total_amount:,.0f}円")
            else:
                # 新規挿入
                response = self.supabase.table("platform_daily_sales").insert(data).execute()
                logger.debug(f"挿入: {sales_date} - {total_amount:,.0f}円")
            
            return response.data is not None
            
        except Exception as e:
            logger.error(f"Upsertエラー ({sales_date}): {str(e)}")
            return False
    
    def get_aggregated_summary(self, start_date: str = None, end_date: str = None):
        """集計済みデータのサマリーを取得"""
        
        # デフォルト期間設定
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
        if not start_date:
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        
        try:
            # platform_daily_salesから取得
            response = self.supabase.table("platform_daily_sales").select("*").eq(
                "platform", "rakuten"
            ).gte("sales_date", start_date).lte("sales_date", end_date).order(
                "sales_date", desc=False
            ).execute()
            
            data = response.data if response.data else []
            
            # 合計計算
            total_amount = sum(item['total_amount'] for item in data)
            total_orders = sum(item['order_count'] for item in data)
            
            return {
                'status': 'success',
                'period': {'start_date': start_date, 'end_date': end_date},
                'summary': {
                    'total_amount': total_amount,
                    'total_orders': total_orders,
                    'total_days': len(data),
                    'daily_average': total_amount / len(data) if data else 0
                },
                'daily_data': data
            }
            
        except Exception as e:
            logger.error(f"サマリー取得エラー: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }


def main():
    """メイン処理"""
    aggregator = RakutenDailyAggregator()
    
    print("=== 楽天売上日次集計処理 ===\n")
    
    # 過去のデータを集計（最初の実行時）
    print("【1】初回集計実行（過去30日分）")
    result = aggregator.aggregate_daily_sales()
    
    if result['status'] == 'success':
        print(f"✅ 集計成功: {result['total_days']}日分")
        print(f"   成功: {result['success_count']}日")
        print(f"   エラー: {result['error_count']}日")
    else:
        print(f"❌ 集計失敗: {result['message']}")
        return
    
    # 集計結果の確認
    print(f"\n【2】集計結果確認")
    summary = aggregator.get_aggregated_summary()
    
    if summary['status'] == 'success':
        print(f"✅ 期間: {summary['period']['start_date']} ~ {summary['period']['end_date']}")
        print(f"   総売上: {summary['summary']['total_amount']:,.0f}円")
        print(f"   総注文数: {summary['summary']['total_orders']}件")
        print(f"   日数: {summary['summary']['total_days']}日")
        print(f"   日平均: {summary['summary']['daily_average']:,.0f}円")
        
        # 最新5日分を表示
        print(f"\n   最新5日分:")
        for item in summary['daily_data'][-5:]:
            print(f"   {item['sales_date']}: {item['total_amount']:,.0f}円 ({item['order_count']}件)")
    else:
        print(f"❌ 確認失敗: {summary['message']}")
    
    print(f"\n=== Phase 1 Step 2 完了! ===")
    print("✅ 楽天データの日次集計処理が完了しました")
    print("\n次のステップ:")
    print("1. /api/sales/platform_summary API作成")
    print("2. 期間選択UI作成")


if __name__ == "__main__":
    main()