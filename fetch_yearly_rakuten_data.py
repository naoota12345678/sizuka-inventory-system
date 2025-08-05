#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
楽天APIから過去1年分の注文データを取得
在庫管理システムと同様に楽天APIを使用してデータを取得
"""

import os
import sys
from datetime import datetime, timedelta
import pytz
import logging

# プロジェクトのルートディレクトリをパスに追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from api.rakuten_api import RakutenAPI

# ロギング設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 環境変数の設定
os.environ['SUPABASE_URL'] = "https://equrcpeifogdrxoldkpe.supabase.co"
os.environ['SUPABASE_KEY'] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ"
os.environ['RAKUTEN_SERVICE_SECRET'] = "SP338531_d1NJjF2R5OwZpWH6"
os.environ['RAKUTEN_LICENSE_KEY'] = "SL338531_kUvqO4kIHaMbr9ik"

def fetch_yearly_data():
    """過去1年分のデータを月単位で取得"""
    
    logger.info("=== 楽天API 過去1年分データ取得開始 ===")
    
    try:
        # RakutenAPIクラスのインスタンス化
        rakuten_api = RakutenAPI()
        jst = pytz.timezone('Asia/Tokyo')
        
        # 今日から過去1年間を定義
        end_date = datetime.now(jst)
        start_date = end_date - timedelta(days=365)
        
        logger.info(f"取得期間: {start_date.strftime('%Y-%m-%d')} ～ {end_date.strftime('%Y-%m-%d')}")
        
        # 月単位で処理（APIの負荷を考慮）
        current_date = start_date
        total_orders = []
        monthly_summary = {}
        
        while current_date < end_date:
            # 月の開始日と終了日を計算
            month_start = current_date
            # 次の月の1日を計算
            if current_date.month == 12:
                month_end = datetime(current_date.year + 1, 1, 1, tzinfo=jst)
            else:
                month_end = datetime(current_date.year, current_date.month + 1, 1, tzinfo=jst)
            
            # 月末が取得期間を超えないように調整
            if month_end > end_date:
                month_end = end_date
            
            month_str = month_start.strftime('%Y-%m')
            logger.info(f"\n処理中: {month_str} ({month_start.strftime('%Y-%m-%d')} ～ {month_end.strftime('%Y-%m-%d')})")
            
            try:
                # 楽天APIから注文データを取得
                orders = rakuten_api.get_orders(month_start, month_end)
                
                if orders:
                    logger.info(f"{month_str}: {len(orders)}件の注文を取得")
                    
                    # Supabaseに保存
                    save_result = rakuten_api.save_to_supabase(orders)
                    
                    monthly_summary[month_str] = {
                        'orders_fetched': len(orders),
                        'orders_saved': save_result.get('orders_created', 0) + save_result.get('orders_updated', 0),
                        'errors': save_result.get('orders_errors', 0)
                    }
                    
                    total_orders.extend(orders)
                    
                    # 月別の売上合計を計算
                    month_total = sum(float(order.get('totalPrice', 0)) for order in orders)
                    monthly_summary[month_str]['total_amount'] = month_total
                    
                    logger.info(f"{month_str}: 保存成功 {save_result.get('orders_created', 0)}件（新規）, {save_result.get('orders_updated', 0)}件（更新）")
                else:
                    logger.info(f"{month_str}: 注文データなし")
                    monthly_summary[month_str] = {
                        'orders_fetched': 0,
                        'orders_saved': 0,
                        'errors': 0,
                        'total_amount': 0
                    }
                
            except Exception as e:
                logger.error(f"{month_str} の処理でエラー: {str(e)}")
                monthly_summary[month_str] = {
                    'orders_fetched': 0,
                    'orders_saved': 0,
                    'errors': 1,
                    'total_amount': 0,
                    'error_message': str(e)
                }
            
            # 次の月へ
            current_date = month_end
            
            # API制限を考慮して少し待機
            import time
            time.sleep(2)
        
        # 結果サマリー
        logger.info("\n=== 取得完了サマリー ===")
        logger.info(f"総注文数: {len(total_orders)}件")
        
        total_saved = sum(m['orders_saved'] for m in monthly_summary.values())
        total_errors = sum(m['errors'] for m in monthly_summary.values())
        total_amount = sum(m['total_amount'] for m in monthly_summary.values())
        
        logger.info(f"保存成功: {total_saved}件")
        logger.info(f"エラー: {total_errors}件")
        logger.info(f"総売上: {total_amount:,.0f}円")
        
        logger.info("\n月別詳細:")
        for month, data in sorted(monthly_summary.items()):
            if data['orders_fetched'] > 0:
                logger.info(f"{month}: {data['orders_fetched']}件取得, {data['orders_saved']}件保存, {data['total_amount']:,.0f}円")
            else:
                logger.info(f"{month}: データなし")
        
        # platform_daily_salesの再集計を実行
        logger.info("\n=== 日次売上集計を更新 ===")
        from efficient_sales_sync import EfficientSalesSync
        sync = EfficientSalesSync()
        sync_result = sync.sync_all_sales()
        
        if sync_result['status'] == 'success':
            logger.info(f"日次集計更新完了: {sync_result['total_days']}日分")
        
        return {
            'status': 'success',
            'total_orders': len(total_orders),
            'total_saved': total_saved,
            'total_errors': total_errors,
            'total_amount': total_amount,
            'monthly_summary': monthly_summary
        }
        
    except Exception as e:
        logger.error(f"処理中にエラーが発生: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            'status': 'error',
            'message': str(e)
        }

def main():
    """メイン処理"""
    print("=== 楽天API 過去1年分データ取得 ===")
    print("在庫管理システムと同様の方法で楽天APIからデータを取得します。")
    print("処理には時間がかかる場合があります。\n")
    
    # 環境変数チェック
    print(f"楽天API認証情報: SERVICE_SECRET={'SET' if os.getenv('RAKUTEN_SERVICE_SECRET') else 'NOT SET'}")
    print(f"楽天API認証情報: LICENSE_KEY={'SET' if os.getenv('RAKUTEN_LICENSE_KEY') else 'NOT SET'}")
    
    result = fetch_yearly_data()
    
    if result['status'] == 'success':
        print("\n過去1年分のデータ取得が完了しました！")
        print(f"総注文数: {result['total_orders']}件")
        print(f"保存成功: {result['total_saved']}件")
        print(f"総売上: {result['total_amount']:,.0f}円")
        print("\nダッシュボードで確認: https://sizuka-inventory-system-p2wv4efvja-an.a.run.app/platform-sales")
    else:
        print(f"\nエラーが発生しました: {result.get('message', 'Unknown error')}")

if __name__ == "__main__":
    main()