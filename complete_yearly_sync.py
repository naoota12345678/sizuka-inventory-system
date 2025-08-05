#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
1年分完全同期実行（時間制限なし）
全期間を確実に同期完了まで実行
"""

import logging
from datetime import datetime
from historical_daily_sync import HistoricalDailySync

# ログファイル設定
log_filename = f"yearly_sync_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def complete_yearly_sync():
    """1年分完全同期（途中から再開対応）"""
    
    logger.info("=== 1年分完全同期開始 ===")
    
    sync = HistoricalDailySync()
    
    try:
        # 現在の状況確認
        summary = sync.get_sync_summary()
        if summary['status'] == 'success':
            logger.info(f"現在の同期状況: {summary['totals']['days']}日分完了")
        
        # 全期間同期（未完了分も含めて）
        logger.info("過去1年分の完全同期を実行します...")
        result = sync.sync_past_year()
        
        logger.info("=== 同期結果 ===")
        logger.info(f"総日数: {result['total_days']}日")
        logger.info(f"成功: {result['success_count']}日")
        logger.info(f"データなし: {result['skipped_count']}日")
        logger.info(f"エラー: {result['error_count']}日")
        
        # エラー詳細
        if result['error_count'] > 0:
            logger.warning("エラーが発生した日付:")
            for day_result in result['daily_results']:
                if day_result['status'] == 'error':
                    logger.warning(f"  {day_result['date']}: {day_result.get('message', 'Unknown error')}")
        
        # 最終サマリー
        final_summary = sync.get_sync_summary()
        if final_summary['status'] == 'success':
            totals = final_summary['totals']
            period = final_summary['period']
            
            logger.info("=== 最終サマリー ===")
            logger.info(f"同期完了期間: {period['start']} ～ {period['end']}")
            logger.info(f"総売上: {totals['amount']:,.0f}円")
            logger.info(f"総注文数: {totals['orders']}件")
            logger.info(f"データ日数: {totals['days']}日")
            logger.info(f"日平均売上: {totals['avg_daily']:,.0f}円")
            logger.info(f"注文単価: {totals['avg_order']:,.0f}円")
            
            # 1年分確認
            from datetime import datetime, timedelta
            one_year_ago = datetime.now() - timedelta(days=365)
            start_date = datetime.strptime(period['start'], '%Y-%m-%d')
            
            if start_date <= one_year_ago:
                logger.info("✅ 1年分以上のデータ同期完了")
                logger.info("✅ ダッシュボードで過去1年分の売上分析が可能です")
            else:
                missing_days = (start_date - one_year_ago).days
                logger.warning(f"⚠️ {missing_days}日分のデータが不足（ordersテーブルにデータなし）")
        
        logger.info("✅ 1年分同期処理が完了しました")
        return True
        
    except Exception as e:
        logger.error(f"❌ 同期処理でエラーが発生: {str(e)}")
        return False

if __name__ == "__main__":
    print("1年分完全同期を開始します...")
    print("処理時間: 約15-20分")
    print(f"ログファイル: {log_filename}")
    print()
    
    success = complete_yearly_sync()
    
    if success:
        print("\n✅ 1年分同期が完了しました！")
        print("ダッシュボードURL: https://sizuka-inventory-system-p2wv4efvja-an.a.run.app/platform-sales")
        print("過去1年分の売上分析が可能になりました。")
    else:
        print("\n❌ 同期処理でエラーが発生しました。")
        print("ログファイルを確認してください。")