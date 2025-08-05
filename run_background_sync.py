#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
バックグラウンドでの過去1年分同期実行
ログファイルに結果を出力
"""

import logging
from datetime import datetime
from historical_daily_sync import HistoricalDailySync

# ファイルログ設定
log_filename = f"sync_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def background_sync():
    """バックグラウンド同期実行"""
    logger.info("=== 過去1年分バックグラウンド同期開始 ===")
    
    sync = HistoricalDailySync()
    
    try:
        # 過去1年分同期
        result = sync.sync_past_year()
        
        logger.info("=== 同期完了 ===")
        logger.info(f"総日数: {result['total_days']}日")
        logger.info(f"成功: {result['success_count']}日")
        logger.info(f"データなし: {result['skipped_count']}日")
        logger.info(f"エラー: {result['error_count']}日")
        
        # 最終サマリー
        summary = sync.get_sync_summary()
        if summary['status'] == 'success':
            totals = summary['totals']
            period = summary['period']
            logger.info("=== 最終サマリー ===")
            logger.info(f"期間: {period['start']} ～ {period['end']}")
            logger.info(f"総売上: {totals['amount']:,.0f}円")
            logger.info(f"総注文数: {totals['orders']}件")
            logger.info(f"データ日数: {totals['days']}日")
            logger.info(f"日平均売上: {totals['avg_daily']:,.0f}円")
            logger.info(f"注文単価: {totals['avg_order']:,.0f}円")
        
        logger.info("✅ 過去1年分の同期が正常完了しました")
        return True
        
    except Exception as e:
        logger.error(f"❌ 同期処理でエラーが発生: {str(e)}")
        return False

if __name__ == "__main__":
    success = background_sync()
    if success:
        print("同期完了！ログファイルを確認してください。")
    else:
        print("同期エラー。ログファイルを確認してください。")