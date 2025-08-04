#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
プラットフォーム別売上集計API
Phase 1 Step 3: /api/sales/platform_summary エンドポイント
"""

from fastapi import Query
from supabase import create_client
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import logging

# ロギング設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SUPABASE_URL = "https://equrcpeifogdrxoldkpe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ"


async def get_platform_sales_summary(
    start_date: Optional[str] = Query(None, description="開始日 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="終了日 (YYYY-MM-DD)")
) -> Dict:
    """
    プラットフォーム別売上集計を取得
    
    Parameters:
    - start_date: 開始日（省略時は30日前）
    - end_date: 終了日（省略時は今日）
    
    Returns:
    - 期間内の取引先別売上集計
    """
    
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    try:
        # デフォルト期間設定
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
        if not start_date:
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        
        logger.info(f"売上集計取得: {start_date} ~ {end_date}")
        
        # platform_daily_salesから期間内のデータを取得
        response = supabase.table("platform_daily_sales").select("*").gte(
            "sales_date", start_date
        ).lte(
            "sales_date", end_date
        ).order(
            "sales_date", desc=False
        ).execute()
        
        data = response.data if response.data else []
        
        # プラットフォーム別集計
        platform_totals = {}
        daily_trends = []
        
        # 日別データを整理
        daily_data = {}
        
        for item in data:
            sales_date = item['sales_date']
            platform = item['platform']
            amount = float(item['total_amount'])
            order_count = item['order_count']
            
            # プラットフォーム別合計
            if platform not in platform_totals:
                platform_totals[platform] = {
                    'total_amount': 0,
                    'total_orders': 0
                }
            
            platform_totals[platform]['total_amount'] += amount
            platform_totals[platform]['total_orders'] += order_count
            
            # 日別データ
            if sales_date not in daily_data:
                daily_data[sales_date] = {
                    'date': sales_date,
                    'total': 0
                }
            
            daily_data[sales_date]['total'] += amount
            daily_data[sales_date][platform] = amount
        
        # 日別データをリスト化
        daily_trends = list(daily_data.values())
        daily_trends.sort(key=lambda x: x['date'])
        
        # 全体集計
        total_sales = sum(p['total_amount'] for p in platform_totals.values())
        total_orders = sum(p['total_orders'] for p in platform_totals.values())
        
        # プラットフォーム別売上（簡易版）
        platform_breakdown = {
            platform: data['total_amount'] 
            for platform, data in platform_totals.items()
        }
        
        # レスポンス構築
        response_data = {
            'status': 'success',
            'period': {
                'start_date': start_date,
                'end_date': end_date
            },
            'total_sales': total_sales,
            'total_orders': total_orders,
            'platform_breakdown': platform_breakdown,
            'platform_details': platform_totals,
            'daily_trends': daily_trends,
            'metadata': {
                'total_days': len(daily_trends),
                'platforms': list(platform_totals.keys()),
                'daily_average': total_sales / len(daily_trends) if daily_trends else 0
            }
        }
        
        return response_data
        
    except Exception as e:
        logger.error(f"Error in get_platform_sales_summary: {str(e)}")
        return {
            'status': 'error',
            'message': str(e),
            'period': {
                'start_date': start_date,
                'end_date': end_date
            }
        }


# FastAPIエンドポイント定義（main_cloudrun.pyに統合用）
def create_platform_sales_endpoint(app):
    """FastAPIアプリケーションにエンドポイントを追加"""
    
    @app.get("/api/sales/platform_summary")
    async def platform_sales_endpoint(
        start_date: Optional[str] = Query(None, description="開始日 (YYYY-MM-DD)"),
        end_date: Optional[str] = Query(None, description="終了日 (YYYY-MM-DD)")
    ):
        """プラットフォーム別売上集計API"""
        return await get_platform_sales_summary(start_date, end_date)


# テスト用
if __name__ == "__main__":
    import asyncio
    
    async def test_api():
        print("=== プラットフォーム別売上集計API テスト ===\n")
        
        # 最近7日間のテスト
        result = await get_platform_sales_summary(
            start_date="2025-07-28",
            end_date="2025-08-04"
        )
        
        if result['status'] == 'success':
            print(f"期間: {result['period']['start_date']} ~ {result['period']['end_date']}")
            print(f"総売上: {result['total_sales']:,.0f}円")
            print(f"総注文数: {result['total_orders']}件")
            print(f"\nプラットフォーム別売上:")
            
            for platform, amount in result['platform_breakdown'].items():
                percentage = (amount / result['total_sales'] * 100) if result['total_sales'] > 0 else 0
                print(f"  {platform}: {amount:,.0f}円 ({percentage:.1f}%)")
            
            print(f"\n日別売上推移（最新5日）:")
            for trend in result['daily_trends'][-5:]:
                print(f"  {trend['date']}: {trend['total']:,.0f}円")
        else:
            print(f"エラー: {result['message']}")
        
        print("\n✅ API作成完了!")
        print("次のステップ: main_cloudrun.pyに統合")
    
    asyncio.run(test_api())