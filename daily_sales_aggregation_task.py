#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日次売上集計タスク
毎日実行して前日の売上をplatform_daily_salesに集計
"""

from supabase import create_client
from datetime import datetime, timedelta
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://equrcpeifogdrxoldkpe.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ")

def aggregate_yesterday_sales():
    """昨日の売上を集計"""
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # 昨日の日付
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    logger.info(f"集計日: {yesterday}")
    
    try:
        # 楽天の売上集計
        orders_response = supabase.table("orders").select(
            "created_at, total_amount"
        ).gte("created_at", yesterday).lt("created_at", datetime.now().strftime('%Y-%m-%d')).execute()
        
        orders = orders_response.data if orders_response.data else []
        
        if orders:
            total_amount = sum(float(order.get('total_amount', 0)) for order in orders)
            order_count = len(orders)
            
            # platform_daily_salesに保存
            data = {
                "sales_date": yesterday,
                "platform": "rakuten",
                "total_amount": round(total_amount, 2),
                "order_count": order_count
            }
            
            # Upsert（既存データがあれば更新、なければ挿入）
            existing = supabase.table("platform_daily_sales").select("*").eq(
                "sales_date", yesterday
            ).eq("platform", "rakuten").execute()
            
            if existing.data:
                response = supabase.table("platform_daily_sales").update(data).eq(
                    "sales_date", yesterday
                ).eq("platform", "rakuten").execute()
                logger.info(f"更新: {yesterday} - {total_amount:,.0f}円 ({order_count}件)")
            else:
                response = supabase.table("platform_daily_sales").insert(data).execute()
                logger.info(f"挿入: {yesterday} - {total_amount:,.0f}円 ({order_count}件)")
            
            return {
                'status': 'success',
                'date': yesterday,
                'platform': 'rakuten',
                'total_amount': total_amount,
                'order_count': order_count
            }
        else:
            logger.info(f"売上データなし: {yesterday}")
            return {
                'status': 'no_data',
                'date': yesterday,
                'platform': 'rakuten'
            }
            
    except Exception as e:
        logger.error(f"集計エラー: {str(e)}")
        return {
            'status': 'error',
            'date': yesterday,
            'message': str(e)
        }

# Cloud Functionsやスケジューラーから呼び出すエントリーポイント
def main(request=None):
    """メインエントリーポイント"""
    result = aggregate_yesterday_sales()
    return result

if __name__ == "__main__":
    # 手動実行用
    result = main()
    print(f"結果: {result}")