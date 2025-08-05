#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
2月10日からの全データを楽天APIから同期
"""

import os
import logging
from datetime import datetime

# 環境変数を設定
os.environ['SUPABASE_URL'] = 'https://equrcpeifogdrxoldkpe.supabase.co'
os.environ['SUPABASE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ'
os.environ['RAKUTEN_SERVICE_SECRET'] = 'SP338531_d1NJjF2R5OwZpWH6'
os.environ['RAKUTEN_LICENSE_KEY'] = 'SL338531_kUvqO4kIHaMbr9ik'

from api.rakuten_api import RakutenAPI
from supabase import create_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def sync_from_february():
    """2月10日からの全データを同期"""
    
    logger.info("=== 2月10日からの全データ同期開始 ===")
    
    api = RakutenAPI()
    
    # 期間を設定（2024年2月10日から今日まで）
    start_date = datetime(2024, 2, 10)
    end_date = datetime.now()
    
    logger.info(f"同期期間: {start_date.strftime('%Y-%m-%d')} ～ {end_date.strftime('%Y-%m-%d')}")
    days = (end_date - start_date).days
    logger.info(f"日数: {days}日間")
    
    try:
        # 注文データを取得
        logger.info("楽天APIから注文データを取得中...")
        orders = api.get_orders(start_date, end_date)
        logger.info(f"取得した注文数: {len(orders)}件")
        
        if orders:
            # Supabaseに保存
            logger.info("Supabaseへの保存を開始...")
            result = api.save_to_supabase(orders)
            
            logger.info("=== 同期結果 ===")
            logger.info(f"注文保存: {result['success_count']}/{result['total_orders']} ({result['success_rate']})")
            logger.info(f"商品保存成功: {result['items_success']}件")
            logger.info(f"商品保存失敗: {result['items_error']}件")
            
            # エラーの詳細
            if result['failed_orders']:
                logger.warning(f"失敗した注文: {len(result['failed_orders'])}件")
                for failed in result['failed_orders'][:5]:
                    logger.warning(f"  - {failed['order_number']}: {failed['error']}")
        else:
            logger.info("指定期間に注文データがありませんでした")
            
    except Exception as e:
        logger.error(f"同期エラー: {str(e)}")
        raise
    
    # 最終的なデータ数を確認
    supabase = create_client(
        os.environ['SUPABASE_URL'],
        os.environ['SUPABASE_KEY']
    )
    
    orders_count = len(supabase.table("orders").select("id").execute().data)
    items_count = len(supabase.table("order_items").select("id").execute().data)
    
    logger.info("=== 最終データ数 ===")
    logger.info(f"orders: {orders_count}件")
    logger.info(f"order_items: {items_count}件")
    
    # 予想される商品数
    if orders_count > 0:
        avg_items_per_order = items_count / orders_count
        logger.info(f"平均商品数/注文: {avg_items_per_order:.1f}件")
    
    logger.info("=== 同期完了 ===")

if __name__ == "__main__":
    sync_from_february()