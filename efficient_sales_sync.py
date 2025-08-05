#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
効率的な売上同期処理
在庫同期と同じ一括処理方式で高速に売上データを同期
"""

from supabase import create_client
from datetime import datetime, timedelta
from collections import defaultdict
import logging

# ロギング設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

SUPABASE_URL = "https://equrcpeifogdrxoldkpe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ"

class EfficientSalesSync:
    """効率的な売上同期クラス"""
    
    def __init__(self):
        self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    def sync_all_sales(self):
        """全売上データを効率的に同期"""
        
        logger.info("=== 効率的な売上同期開始 ===")
        start_time = datetime.now()
        
        try:
            # ステップ1: 全注文データを一括取得
            logger.info("ステップ1: 全注文データを一括取得中...")
            orders_response = self.supabase.table("orders").select(
                "order_date, total_amount"
            ).execute()
            
            orders = orders_response.data if orders_response.data else []
            logger.info(f"取得完了: {len(orders)}件の注文データ")
            
            if not orders:
                logger.warning("注文データが見つかりません")
                return {"status": "no_data", "message": "注文データが見つかりません"}
            
            # ステップ2: メモリ上で日別集計
            logger.info("ステップ2: 日別売上を集計中...")
            daily_sales = defaultdict(lambda: {'total_amount': 0, 'order_count': 0})
            
            for order in orders:
                # 日付を抽出（YYYY-MM-DD形式）
                order_date_str = order.get('order_date', '')
                if 'T' in order_date_str:
                    date_str = order_date_str.split('T')[0]
                else:
                    date_str = order_date_str[:10]
                
                # 売上金額を加算
                total_amount = float(order.get('total_amount', 0))
                daily_sales[date_str]['total_amount'] += total_amount
                daily_sales[date_str]['order_count'] += 1
            
            logger.info(f"集計完了: {len(daily_sales)}日分のデータ")
            
            # ステップ3: platform_daily_salesテーブルに一括保存
            logger.info("ステップ3: データベースに保存中...")
            success_count = 0
            error_count = 0
            
            # 既存データを一括取得（効率化のため）
            existing_response = self.supabase.table("platform_daily_sales").select(
                "sales_date"
            ).eq("platform", "rakuten").execute()
            
            existing_dates = {item['sales_date'] for item in existing_response.data} if existing_response.data else set()
            logger.info(f"既存データ: {len(existing_dates)}日分")
            
            # バッチ処理用のリスト
            insert_batch = []
            update_batch = []
            
            for date_str, data in daily_sales.items():
                record = {
                    "sales_date": date_str,
                    "platform": "rakuten",
                    "total_amount": round(data['total_amount'], 2),
                    "order_count": data['order_count']
                }
                
                if date_str in existing_dates:
                    update_batch.append(record)
                else:
                    insert_batch.append(record)
            
            # バッチ挿入
            if insert_batch:
                logger.info(f"新規データ挿入: {len(insert_batch)}件")
                # Supabaseは一度に最大1000件まで挿入可能
                for i in range(0, len(insert_batch), 100):
                    batch = insert_batch[i:i+100]
                    try:
                        self.supabase.table("platform_daily_sales").insert(batch).execute()
                        success_count += len(batch)
                    except Exception as e:
                        logger.error(f"挿入エラー: {str(e)}")
                        error_count += len(batch)
            
            # バッチ更新（既存データの更新）
            if update_batch:
                logger.info(f"既存データ更新: {len(update_batch)}件")
                for record in update_batch:
                    try:
                        self.supabase.table("platform_daily_sales").update({
                            "total_amount": record['total_amount'],
                            "order_count": record['order_count']
                        }).eq(
                            "sales_date", record['sales_date']
                        ).eq(
                            "platform", "rakuten"
                        ).execute()
                        success_count += 1
                    except Exception as e:
                        logger.error(f"更新エラー ({record['sales_date']}): {str(e)}")
                        error_count += 1
            
            # 処理時間計算
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()
            
            # 結果サマリー
            result = {
                "status": "success",
                "processing_time": f"{processing_time:.2f}秒",
                "total_orders": len(orders),
                "total_days": len(daily_sales),
                "success_count": success_count,
                "error_count": error_count,
                "new_records": len(insert_batch),
                "updated_records": len(update_batch)
            }
            
            logger.info("=== 同期完了 ===")
            logger.info(f"処理時間: {processing_time:.2f}秒")
            logger.info(f"総注文数: {len(orders)}件")
            logger.info(f"集計日数: {len(daily_sales)}日")
            logger.info(f"成功: {success_count}件")
            logger.info(f"エラー: {error_count}件")
            
            return result
            
        except Exception as e:
            logger.error(f"同期処理でエラーが発生: {str(e)}")
            return {
                "status": "error",
                "message": str(e)
            }
    
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
            
            # 最新10日分のデータ
            recent_data = all_data.data[-10:]
            
            return {
                "status": "success",
                "period": {"start": start_date, "end": end_date},
                "totals": {
                    "amount": total_amount,
                    "orders": total_orders,
                    "days": total_days,
                    "avg_daily": total_amount / total_days if total_days > 0 else 0,
                    "avg_order": total_amount / total_orders if total_orders > 0 else 0
                },
                "recent_days": [
                    {
                        "date": item['sales_date'],
                        "amount": item['total_amount'],
                        "orders": item['order_count']
                    } for item in recent_data
                ]
            }
            
        except Exception as e:
            return {"status": "error", "message": str(e)}

def main():
    """メイン処理"""
    print("=== 効率的な売上同期（一括処理方式） ===\n")
    
    sync = EfficientSalesSync()
    
    # 同期実行
    result = sync.sync_all_sales()
    
    if result['status'] == 'success':
        print(f"\n同期成功！")
        print(f"処理時間: {result['processing_time']}")
        print(f"総注文数: {result['total_orders']}件")
        print(f"集計日数: {result['total_days']}日")
        print(f"新規: {result['new_records']}件")
        print(f"更新: {result['updated_records']}件")
        
        # サマリー表示
        print(f"\n=== 現在のデータサマリー ===")
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
            
            print(f"\n最近10日間:")
            for day in summary['recent_days']:
                print(f"  {day['date']}: {day['amount']:,.0f}円 ({day['orders']}件)")
    else:
        print(f"\n同期失敗: {result.get('message', 'Unknown error')}")
    
    print("\n在庫同期と同じ一括処理方式での同期が完了しました！")
    print("ダッシュボードで確認: https://sizuka-inventory-system-p2wv4efvja-an.a.run.app/platform-sales")

if __name__ == "__main__":
    main()