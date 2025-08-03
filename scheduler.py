#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
1日1回の自動実行スケジューラー
毎日決まった時間にGoogle Sheets同期と楽天注文処理を実行
"""

import schedule
import time
from datetime import datetime
import logging
from daily_rakuten_processing import daily_processing

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scheduler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def run_daily_job():
    """毎日実行するジョブ"""
    logger.info("=" * 60)
    logger.info(f"Starting scheduled daily job at {datetime.now()}")
    logger.info("=" * 60)
    
    try:
        result = daily_processing()
        
        if result["overall_success"]:
            logger.info("✓ Daily job completed successfully")
        else:
            logger.error("✗ Daily job completed with errors")
            
        logger.info("=" * 60)
        
        return result
        
    except Exception as e:
        logger.error(f"Daily job failed with exception: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def setup_scheduler():
    """スケジューラーの設定"""
    # 毎日午前2時に実行（サーバーの負荷が少ない時間帯）
    schedule.every().day.at("02:00").do(run_daily_job)
    
    # テスト用：毎分実行（本番では無効化）
    # schedule.every(1).minutes.do(run_daily_job)
    
    logger.info("Scheduler configured:")
    logger.info("- Daily execution at 02:00 JST")
    logger.info("- Processing: Google Sheets sync + Rakuten order processing")

def run_scheduler():
    """スケジューラーのメインループ"""
    logger.info("Starting daily scheduler...")
    logger.info("Press Ctrl+C to stop")
    
    setup_scheduler()
    
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # 1分ごとにチェック
            
    except KeyboardInterrupt:
        logger.info("Scheduler stopped by user")
    except Exception as e:
        logger.error(f"Scheduler error: {str(e)}")
        raise

def run_manual():
    """手動実行"""
    logger.info("Running manual daily processing...")
    result = run_daily_job()
    
    if result:
        print("\nManual execution completed")
        print(f"Sync success: {result.get('sync_success', False)}")
        if result.get('processing_result'):
            pr = result['processing_result']
            print(f"Orders processed: {pr.get('processed_items', 0)}/{pr.get('total_items', 0)}")
            print(f"Unprocessed items: {pr.get('unprocessed_items', 0)}")
            print(f"Inventory changes: {len(pr.get('inventory_summary', {})) if pr.get('inventory_summary') else 0} products")
    else:
        print("\nManual execution failed")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "manual":
        # 手動実行
        run_manual()
    else:
        # スケジューラー実行
        run_scheduler()