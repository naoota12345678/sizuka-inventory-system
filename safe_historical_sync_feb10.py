#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
2月10日以降の楽天データ安全同期
在庫システムに影響を与えずに売上データのみ同期

注意: この処理は在庫マッピングシステムと完全に分離されています
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

def sync_historical_data_feb10():
    """2月10日以降のデータを安全に同期"""
    
    logger.info("=== 2月10日以降 楽天データ同期開始 ===")
    logger.info("⚠️  在庫システムには影響しません（売上データのみ同期）")
    
    try:
        # RakutenAPIクラスのインスタンス化
        rakuten_api = RakutenAPI()
        jst = pytz.timezone('Asia/Tokyo')
        
        # 同期期間の定義: 2025年2月10日～7月31日
        start_date = datetime(2025, 2, 10, 0, 0, 0, tzinfo=jst)
        end_date = datetime(2025, 7, 31, 23, 59, 59, tzinfo=jst)
        
        logger.info(f"同期期間: {start_date.strftime('%Y-%m-%d')} ～ {end_date.strftime('%Y-%m-%d')}")
        
        # 月単位で処理（APIの負荷を考慮）
        current_date = start_date
        total_summary = {
            'total_orders_fetched': 0,
            'total_orders_saved': 0,
            'total_items_saved': 0,
            'total_errors': 0,
            'monthly_details': {}
        }
        
        while current_date < end_date:
            # 月の開始日と終了日を計算
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
            logger.info(f"\n📅 処理中: {month_str} ({month_start.strftime('%Y-%m-%d')} ～ {month_end.strftime('%Y-%m-%d')})")
            
            try:
                # 楽天APIから注文データを取得
                logger.info(f"🔍 {month_str}: 楽天APIからデータ取得中...")
                orders = rakuten_api.get_orders(month_start, month_end)
                
                if orders:
                    logger.info(f"✅ {month_str}: {len(orders)}件の注文を取得")
                    
                    # Supabaseに保存（ordersテーブルとorder_itemsテーブル）
                    logger.info(f"💾 {month_str}: Supabaseに保存中...")
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
                    
                    logger.info(f"✅ {month_str}: 保存完了")
                    logger.info(f"   - 注文: {save_result.get('success_count', 0)}件保存")
                    logger.info(f"   - 商品: {save_result.get('items_success', 0)}件保存")
                    logger.info(f"   - 成功率: {save_result.get('success_rate', '0%')}")
                    
                    if save_result.get('error_count', 0) > 0:
                        logger.warning(f"⚠️ {month_str}: {save_result.get('error_count', 0)}件のエラー")
                    
                else:
                    logger.info(f"📭 {month_str}: 注文データなし")
                    total_summary['monthly_details'][month_str] = {
                        'orders_fetched': 0,
                        'orders_saved': 0,
                        'items_saved': 0,
                        'errors': 0,
                        'success_rate': '100%'
                    }
                
                # API負荷軽減のため少し待機
                import time
                time.sleep(2)
                
            except Exception as e:
                logger.error(f"❌ {month_str} の処理でエラー: {str(e)}")
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
        logger.info("🎉 2月10日以降データ同期完了")
        logger.info("="*60)
        logger.info(f"📊 総取得注文数: {total_summary['total_orders_fetched']}件")
        logger.info(f"💾 総保存注文数: {total_summary['total_orders_saved']}件")
        logger.info(f"🛒 総保存商品数: {total_summary['total_items_saved']}件")
        logger.info(f"❌ 総エラー数: {total_summary['total_errors']}件")
        
        if total_summary['total_orders_fetched'] > 0:
            success_rate = (total_summary['total_orders_saved'] / total_summary['total_orders_fetched']) * 100
            logger.info(f"✅ 全体成功率: {success_rate:.1f}%")
        
        logger.info("\n📋 月別詳細:")
        for month, details in total_summary['monthly_details'].items():
            logger.info(f"  {month}: 取得{details['orders_fetched']}件 → 保存{details['orders_saved']}件 (商品{details['items_saved']}件)")
        
        logger.info("\n✅ 同期完了: 売上ダッシュボードで過去データを確認できます")
        logger.info("⚠️  在庫への反映は別途実行してください")
        
        return total_summary
        
    except Exception as e:
        logger.error(f"❌ 同期処理でエラー: {str(e)}")
        raise

def main():
    """メイン実行関数"""
    logger.info("2月10日以降 楽天データ同期ツール")
    logger.info("このツールは在庫システムに影響しません")
    
    confirm = input("\n2月10日～7月31日のデータ同期を開始しますか？ (y/N): ")
    
    if confirm.lower() == 'y':
        try:
            result = sync_historical_data_feb10()
            logger.info("\n🎉 同期が正常に完了しました")
            return result
        except Exception as e:
            logger.error(f"\n❌ 同期でエラーが発生しました: {str(e)}")
            return None
    else:
        logger.info("同期をキャンセルしました")
        return None

if __name__ == "__main__":
    main()