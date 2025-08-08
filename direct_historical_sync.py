#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
2月10日以降の楽天データ直接同期
main_cloudrun.pyと同じ設定を使用して安全に同期

⚠️ このスクリプトは在庫システムに影響しません（売上データのみ同期）
"""

import os
import sys
from datetime import datetime, timedelta
import pytz
import logging
import time

# 環境変数を直接設定（main_cloudrun.pyと同じ）
os.environ['SUPABASE_URL'] = 'https://equrcpeifogdrxoldkpe.supabase.co'
os.environ['SUPABASE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ'
os.environ['RAKUTEN_SERVICE_SECRET'] = 'SP338531_d1NJjF2R5OwZpWH6'
os.environ['RAKUTEN_LICENSE_KEY'] = 'SL338531_kUvqO4kIHaMbr9ik'

# プロジェクトのルートディレクトリをパスに追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from api.rakuten_api import RakutenAPI

# ロギング設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def sync_period_data(start_date_str, end_date_str):
    """指定期間のデータを同期"""
    
    logger.info(f"=== {start_date_str} ～ {end_date_str} データ同期開始 ===")
    logger.info("⚠️  在庫システムには影響しません（売上データのみ同期）")
    
    try:
        # RakutenAPIクラスのインスタンス化
        rakuten_api = RakutenAPI()
        jst = pytz.timezone('Asia/Tokyo')
        
        # 同期期間の設定
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').replace(tzinfo=jst)
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59, tzinfo=jst)
        
        logger.info(f"同期期間: {start_date.strftime('%Y-%m-%d %H:%M:%S')} ～ {end_date.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 月単位で処理
        current_date = start_date
        total_summary = {
            'total_orders_fetched': 0,
            'total_orders_saved': 0,
            'total_items_saved': 0,
            'total_errors': 0,
            'monthly_details': {}
        }
        
        while current_date <= end_date:
            # 月の範囲を計算
            month_start = current_date
            
            # 次の月の1日を計算
            if current_date.month == 12:
                month_end = datetime(current_date.year + 1, 1, 1, tzinfo=jst) - timedelta(seconds=1)
            else:
                month_end = datetime(current_date.year, current_date.month + 1, 1, tzinfo=jst) - timedelta(seconds=1)
            
            # 月末が取得期間を超えないように調整
            if month_end > end_date:
                month_end = end_date
            
            month_str = month_start.strftime('%Y-%m')
            logger.info(f"\n📅 処理中: {month_str}")
            logger.info(f"   期間: {month_start.strftime('%Y-%m-%d')} ～ {month_end.strftime('%Y-%m-%d')}")
            
            try:
                # 楽天APIから注文データを取得
                logger.info(f"🔍 楽天APIからデータ取得中...")
                orders = rakuten_api.get_orders(month_start, month_end)
                
                if orders:
                    logger.info(f"✅ {len(orders)}件の注文を取得")
                    
                    # Supabaseに保存
                    logger.info(f"💾 Supabaseに保存中...")
                    save_result = rakuten_api.save_to_supabase(orders)
                    
                    # 結果を記録
                    total_summary['total_orders_fetched'] += len(orders)
                    total_summary['total_orders_saved'] += save_result.get('success_count', 0)
                    total_summary['total_items_saved'] += save_result.get('items_success', 0)
                    total_summary['total_errors'] += save_result.get('error_count', 0)
                    
                    # 月別詳細
                    total_summary['monthly_details'][month_str] = {
                        'orders_fetched': len(orders),
                        'orders_saved': save_result.get('success_count', 0),
                        'items_saved': save_result.get('items_success', 0),
                        'errors': save_result.get('error_count', 0),
                        'success_rate': save_result.get('success_rate', '0%')
                    }
                    
                    logger.info(f"✅ 保存完了:")
                    logger.info(f"   注文: {save_result.get('success_count', 0)}件保存")
                    logger.info(f"   商品: {save_result.get('items_success', 0)}件保存")
                    logger.info(f"   成功率: {save_result.get('success_rate', '0%')}")
                    
                    if save_result.get('error_count', 0) > 0:
                        logger.warning(f"⚠️ {save_result.get('error_count', 0)}件のエラー")
                    
                else:
                    logger.info(f"📭 データなし")
                    total_summary['monthly_details'][month_str] = {
                        'orders_fetched': 0,
                        'orders_saved': 0,
                        'items_saved': 0,
                        'errors': 0,
                        'success_rate': '100%'
                    }
                
                # API負荷軽減のため待機
                logger.info("⏳ API負荷軽減のため2秒待機...")
                time.sleep(2)
                
            except Exception as e:
                logger.error(f"❌ {month_str} 処理エラー: {str(e)}")
                total_summary['total_errors'] += 1
                total_summary['monthly_details'][month_str] = {
                    'orders_fetched': 0,
                    'orders_saved': 0,
                    'items_saved': 0,
                    'errors': 1,
                    'error_message': str(e)
                }
            
            # 次の月へ
            if current_date.month == 12:
                current_date = datetime(current_date.year + 1, 1, 1, tzinfo=jst)
            else:
                current_date = datetime(current_date.year, current_date.month + 1, 1, tzinfo=jst)
        
        # 最終サマリー
        logger.info("\n" + "="*60)
        logger.info("🎉 データ同期完了")
        logger.info("="*60)
        logger.info(f"📊 総取得注文数: {total_summary['total_orders_fetched']}件")
        logger.info(f"💾 総保存注文数: {total_summary['total_orders_saved']}件")
        logger.info(f"🛒 総保存商品数: {total_summary['total_items_saved']}件")
        logger.info(f"❌ 総エラー数: {total_summary['total_errors']}件")
        
        if total_summary['total_orders_fetched'] > 0:
            success_rate = (total_summary['total_orders_saved'] / total_summary['total_orders_fetched']) * 100
            logger.info(f"✅ 全体成功率: {success_rate:.1f}%")
        
        logger.info("\n📋 月別サマリー:")
        for month, details in total_summary['monthly_details'].items():
            if details.get('error_message'):
                logger.info(f"  {month}: エラー - {details['error_message']}")
            else:
                logger.info(f"  {month}: 取得{details['orders_fetched']}件 → 保存{details['orders_saved']}件 (商品{details['items_saved']}件)")
        
        logger.info("\n✅ 同期完了: 売上ダッシュボードで過去データを確認できます")
        
        return total_summary
        
    except Exception as e:
        logger.error(f"❌ 同期処理でエラー: {str(e)}")
        raise

if __name__ == "__main__":
    print("2月10日以降 楽天データ同期")
    print("在庫システムに影響しません（売上データのみ）")
    
    # 自動で2月10日～7月31日を同期
    try:
        result = sync_period_data("2025-02-10", "2025-07-31")
        print("\n🎉 同期が正常に完了しました")
        print("売上ダッシュボードで過去データを確認してください")
    except Exception as e:
        print(f"\n❌ 同期でエラーが発生しました: {str(e)}")