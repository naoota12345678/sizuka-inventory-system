#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
過去1年分の日次売上同期処理
既存のordersデータから1日ごとにplatform_daily_salesに集計
"""

from supabase import create_client
from datetime import datetime, timedelta
import time
import logging

# ロギング設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

SUPABASE_URL = "https://equrcpeifogdrxoldkpe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ"

class HistoricalDailySync:
    """過去1年分の日次同期クラス"""
    
    def __init__(self):
        self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    def sync_daily_range(self, start_date: str, end_date: str, batch_size: int = 30):
        """指定期間を日単位で同期"""
        
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        
        total_days = (end_dt - start_dt).days + 1
        logger.info(f"同期期間: {start_date} ～ {end_date} ({total_days}日間)")
        
        results = {
            'total_days': total_days,
            'success_count': 0,
            'error_count': 0,
            'skipped_count': 0,
            'daily_results': []
        }
        
        current_date = start_dt
        processed_days = 0
        
        while current_date <= end_dt:
            date_str = current_date.strftime('%Y-%m-%d')
            
            try:
                # 1日分の同期実行
                day_result = self.sync_single_day(date_str)
                results['daily_results'].append(day_result)
                
                if day_result['status'] == 'success':
                    results['success_count'] += 1
                    if day_result['order_count'] > 0:
                        logger.info(f"✅ {date_str}: {day_result['total_amount']:,.0f}円 ({day_result['order_count']}件)")
                    else:
                        logger.debug(f"⚪ {date_str}: データなし")
                        results['skipped_count'] += 1
                elif day_result['status'] == 'error':
                    results['error_count'] += 1
                    logger.error(f"❌ {date_str}: {day_result['message']}")
                
                processed_days += 1
                
                # バッチ処理の間隔調整
                if processed_days % batch_size == 0:
                    progress = (processed_days / total_days) * 100
                    logger.info(f"進捗: {processed_days}/{total_days}日 ({progress:.1f}%) - 10秒休憩")
                    time.sleep(10)
                elif processed_days % 10 == 0:
                    # 10日ごとに短い休憩
                    time.sleep(1)
                
            except Exception as e:
                logger.error(f"❌ {date_str}: 予期しないエラー - {str(e)}")
                results['error_count'] += 1
            
            current_date += timedelta(days=1)
        
        # 結果サマリー
        logger.info(f"同期完了: 成功{results['success_count']}日, エラー{results['error_count']}日, データなし{results['skipped_count']}日")
        
        return results
    
    def sync_single_day(self, date_str: str):
        """1日分の売上を同期"""
        
        try:
            # その日のorder_dateを持つ注文を取得
            next_date = (datetime.strptime(date_str, '%Y-%m-%d') + timedelta(days=1)).strftime('%Y-%m-%d')
            
            orders_response = self.supabase.table("orders").select(
                "order_date, total_amount"
            ).gte("order_date", date_str).lt("order_date", next_date).execute()
            
            orders = orders_response.data if orders_response.data else []
            
            if not orders:
                return {
                    'status': 'success',
                    'date': date_str,
                    'order_count': 0,
                    'total_amount': 0,
                    'message': 'データなし'
                }
            
            # 集計
            total_amount = sum(float(order.get('total_amount', 0)) for order in orders)
            order_count = len(orders)
            
            # platform_daily_salesに保存
            success = self._upsert_daily_sales(date_str, 'rakuten', total_amount, order_count)
            
            if success:
                return {
                    'status': 'success',
                    'date': date_str,
                    'order_count': order_count,
                    'total_amount': total_amount
                }
            else:
                return {
                    'status': 'error',
                    'date': date_str,
                    'message': 'データ保存失敗'
                }
        
        except Exception as e:
            return {
                'status': 'error',
                'date': date_str,
                'message': str(e)
            }
    
    def _upsert_daily_sales(self, sales_date: str, platform: str, total_amount: float, order_count: int):
        """日次売上データをupsert"""
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
            else:
                # 新規挿入
                response = self.supabase.table("platform_daily_sales").insert(data).execute()
            
            return response.data is not None
            
        except Exception as e:
            logger.error(f"Upsertエラー ({sales_date}): {str(e)}")
            return False
    
    def sync_past_year(self):
        """過去1年分を同期"""
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
        
        logger.info(f"過去1年分の同期開始: {start_date} ～ {end_date}")
        
        return self.sync_daily_range(start_date, end_date)
    
    def get_sync_summary(self):
        """同期後のサマリーを取得"""
        try:
            # platform_daily_salesの全データ取得
            all_data = self.supabase.table("platform_daily_sales").select(
                "*"
            ).eq("platform", "rakuten").order("sales_date").execute()
            
            if not all_data.data:
                return {"status": "no_data"}
            
            # 統計計算
            total_amount = sum(float(item['total_amount']) for item in all_data.data)
            total_orders = sum(int(item['order_count']) for item in all_data.data)
            total_days = len(all_data.data)
            
            # 期間
            dates = [item['sales_date'] for item in all_data.data]
            start_date = min(dates)
            end_date = max(dates)
            
            return {
                "status": "success",
                "period": {"start": start_date, "end": end_date},
                "totals": {
                    "amount": total_amount,
                    "orders": total_orders,
                    "days": total_days,
                    "avg_daily": total_amount / total_days if total_days > 0 else 0,
                    "avg_order": total_amount / total_orders if total_orders > 0 else 0
                }
            }
            
        except Exception as e:
            return {"status": "error", "message": str(e)}

def main():
    """メイン処理"""
    print("=== 過去1年分の日次売上同期 ===\n")
    
    sync = HistoricalDailySync()
    
    # 確認
    print("この処理は過去1年分（365日）のデータを同期します。")
    print("処理時間: 約10-15分（APIレート制限のため）")
    
    user_input = input("\n実行しますか？ (y/N): ")
    if user_input.lower() != 'y':
        print("キャンセルしました。")
        return
    
    # 過去1年分の同期実行
    result = sync.sync_past_year()
    
    print(f"\n=== 同期結果 ===")
    print(f"総日数: {result['total_days']}日")
    print(f"成功: {result['success_count']}日")
    print(f"データなし: {result['skipped_count']}日")
    print(f"エラー: {result['error_count']}日")
    
    if result['error_count'] > 0:
        print(f"\nエラーが発生した日付:")
        for day_result in result['daily_results']:
            if day_result['status'] == 'error':
                print(f"  {day_result['date']}: {day_result.get('message', 'Unknown error')}")
    
    # 同期後のサマリー
    print(f"\n=== 同期後のサマリー ===")
    summary = sync.get_sync_summary()
    
    if summary['status'] == 'success':
        totals = summary['totals']
        period = summary['period']
        print(f"期間: {period['start']} ～ {period['end']}")
        print(f"総売上: {totals['amount']:,.0f}円")
        print(f"総注文数: {totals['orders']}件")
        print(f"データ日数: {totals['days']}日")
        print(f"日平均売上: {totals['avg_daily']:,.0f}円")
        print(f"注文単価: {totals['avg_order']:,.0f}円")
    
    print(f"\n✅ 過去1年分の同期が完了しました！")

if __name__ == "__main__":
    main()