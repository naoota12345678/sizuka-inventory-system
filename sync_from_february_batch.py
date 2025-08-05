#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
2025年2月10日からの全データを楽天APIから分割同期
楽天APIの制限に対応して90日ごとに分割
"""

import os
import logging
from datetime import datetime, timedelta

# 環境変数を設定
os.environ['SUPABASE_URL'] = 'https://equrcpeifogdrxoldkpe.supabase.co'
os.environ['SUPABASE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ'
os.environ['RAKUTEN_SERVICE_SECRET'] = 'SP338531_d1NJjF2R5OwZpWH6'
os.environ['RAKUTEN_LICENSE_KEY'] = 'SL338531_kUvqO4kIHaMbr9ik'

from api.rakuten_api import RakutenAPI
from supabase import create_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def sync_batch(api, start_date, end_date):
    """指定期間のデータを同期"""
    try:
        logger.info(f"バッチ同期: {start_date.strftime('%Y-%m-%d')} ～ {end_date.strftime('%Y-%m-%d')}")
        
        # 注文データを取得
        orders = api.get_orders(start_date, end_date)
        logger.info(f"  取得した注文数: {len(orders)}件")
        
        if orders:
            # Supabaseに保存
            result = api.save_to_supabase(orders)
            logger.info(f"  注文保存: {result['success_count']}/{result['total_orders']}")
            logger.info(f"  商品保存成功: {result['items_success']}件")
            return result['success_count'], result['items_success']
        return 0, 0
        
    except Exception as e:
        logger.error(f"バッチエラー: {str(e)}")
        return 0, 0

def sync_from_february_in_batches():
    """2025年2月10日からの全データを分割同期"""
    
    logger.info("=== 2025年2月10日からの全データ分割同期開始 ===")
    
    api = RakutenAPI()
    
    # 期間を設定
    start_date = datetime(2025, 2, 10)
    end_date = datetime.now()
    
    # 最大日数（楽天APIの制限を考慮）
    MAX_DAYS = 90  # 90日ごとに分割
    
    total_orders = 0
    total_items = 0
    batch_count = 0
    
    current_start = start_date
    
    while current_start < end_date:
        batch_count += 1
        current_end = min(current_start + timedelta(days=MAX_DAYS), end_date)
        
        logger.info(f"\n=== バッチ {batch_count} ===")
        orders_saved, items_saved = sync_batch(api, current_start, current_end)
        
        total_orders += orders_saved
        total_items += items_saved
        
        # 次のバッチへ
        current_start = current_end + timedelta(days=1)
        
        # API制限を考慮して少し待機
        if current_start < end_date:
            import time
            logger.info("次のバッチまで5秒待機...")
            time.sleep(5)
    
    # 最終的なデータ数を確認
    supabase = create_client(
        os.environ['SUPABASE_URL'],
        os.environ['SUPABASE_KEY']
    )
    
    orders_count = len(supabase.table("orders").select("id").execute().data)
    items_count = len(supabase.table("order_items").select("id").execute().data)
    
    logger.info("\n=== 同期完了 ===")
    logger.info(f"総バッチ数: {batch_count}")
    logger.info(f"同期した注文: {total_orders}件")
    logger.info(f"同期した商品: {total_items}件")
    logger.info(f"\n最終データ数:")
    logger.info(f"orders: {orders_count}件")
    logger.info(f"order_items: {items_count}件")
    
    # マッピングテスト
    if items_count > 0:
        logger.info("\n=== マッピングテスト ===")
        from fix_rakuten_sku_mapping import FixedMappingSystem
        
        mapping_system = FixedMappingSystem()
        
        # サンプル50件でテスト
        sample_orders = supabase.table("order_items").select("*").not_.like("product_code", "TEST%").limit(50).execute()
        
        success_count = 0
        total_count = len(sample_orders.data)
        
        for order in sample_orders.data:
            mapping = mapping_system.find_product_mapping(order)
            if mapping:
                success_count += 1
        
        mapping_rate = (success_count / total_count * 100) if total_count > 0 else 0
        logger.info(f"マッピング結果: {success_count}/{total_count} ({mapping_rate:.1f}%)")
        
        if mapping_rate >= 90:
            logger.info("🎉 マッピング率が90%以上です！")
        
    logger.info("\n=== 完了 ===")

if __name__ == "__main__":
    sync_from_february_in_batches()