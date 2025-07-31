"""
Period Analytics API
期間別集計API
"""

import sys
import os
from pathlib import Path
from datetime import date, datetime, timedelta
from typing import Optional, List
from fastapi import HTTPException, Query
import logging

# Supabaseクライアントのパス追加
supabase_dir = Path(__file__).parent.parent / "supabase"
sys.path.append(str(supabase_dir))

from core.database import supabase

logger = logging.getLogger(__name__)

class PeriodAnalyticsAPI:
    """期間別分析API"""
    
    def __init__(self):
        if not supabase:
            raise Exception("Supabase client not initialized")
        self.client = supabase
    
    def get_custom_period_sales(self, 
                               start_date: date, 
                               end_date: date,
                               group_by: str = 'day',
                               platform: Optional[str] = None,
                               include_profit: bool = True) -> dict:
        """カスタム期間での売上集計"""
        try:
            result = self.client.rpc('get_sales_by_custom_period', {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'group_by_period': group_by,
                'platform_filter': platform,
                'include_profit': include_profit
            }).execute()
            
            if result.data:
                # 統計情報を計算
                total_sales = sum(float(row.get('total_sales', 0)) for row in result.data)
                total_orders = sum(row.get('total_orders', 0) for row in result.data)
                total_profit = sum(float(row.get('total_profit', 0)) for row in result.data)
                
                period_count = len(result.data)
                avg_daily_sales = total_sales / max(period_count, 1) if group_by == 'day' else 0
                
                return {
                    'status': 'success',
                    'period': f'{start_date} to {end_date}',
                    'group_by': group_by,
                    'platform_filter': platform,
                    'summary': {
                        'total_sales': total_sales,
                        'total_orders': total_orders,
                        'total_profit': total_profit,
                        'overall_profit_margin': round((total_profit / max(total_sales, 1)) * 100, 2),
                        'period_count': period_count,
                        'avg_per_period_sales': round(total_sales / max(period_count, 1), 2)
                    },
                    'period_data': result.data
                }
            else:
                return {
                    'status': 'no_data',
                    'message': 'No data found for the specified period'
                }
                
        except Exception as e:
            logger.error(f"Custom period sales error: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def compare_periods(self,
                       current_start: date,
                       current_end: date,
                       previous_start: date,
                       previous_end: date,
                       platform: Optional[str] = None) -> dict:
        """期間比較分析"""
        try:
            result = self.client.rpc('compare_periods', {
                'current_start': current_start.isoformat(),
                'current_end': current_end.isoformat(),
                'previous_start': previous_start.isoformat(),
                'previous_end': previous_end.isoformat(),
                'platform_filter': platform
            }).execute()
            
            if result.data:
                # トレンド分析
                positive_trends = len([r for r in result.data if r.get('trend') == 'up'])
                negative_trends = len([r for r in result.data if r.get('trend') == 'down'])
                
                return {
                    'status': 'success',
                    'current_period': f'{current_start} to {current_end}',
                    'previous_period': f'{previous_start} to {previous_end}',
                    'platform_filter': platform,
                    'trend_summary': {
                        'positive_metrics': positive_trends,
                        'negative_metrics': negative_trends,
                        'overall_trend': 'positive' if positive_trends > negative_trends else 'negative' if negative_trends > positive_trends else 'mixed'
                    },
                    'comparison_data': result.data
                }
            else:
                return {
                    'status': 'no_data',
                    'message': 'No comparison data available'
                }
                
        except Exception as e:
            logger.error(f"Period comparison error: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def get_product_period_comparison(self,
                                    current_start: date,
                                    current_end: date,
                                    previous_start: date,
                                    previous_end: date,
                                    sku: Optional[str] = None) -> dict:
        """商品別期間比較"""
        try:
            result = self.client.rpc('get_product_period_comparison', {
                'sku_filter': sku,
                'current_start': current_start.isoformat(),
                'current_end': current_end.isoformat(),
                'previous_start': previous_start.isoformat(),
                'previous_end': previous_end.isoformat()
            }).execute()
            
            if result.data:
                # トレンド集計
                improved_products = len([r for r in result.data if r.get('trend_direction') == 'improved'])
                declined_products = len([r for r in result.data if r.get('trend_direction') == 'declined'])
                stable_products = len([r for r in result.data if r.get('trend_direction') == 'stable'])
                
                return {
                    'status': 'success',
                    'current_period': f'{current_start} to {current_end}',
                    'previous_period': f'{previous_start} to {previous_end}',
                    'sku_filter': sku,
                    'trend_overview': {
                        'improved_products': improved_products,
                        'declined_products': declined_products,
                        'stable_products': stable_products,
                        'total_products': len(result.data)
                    },
                    'product_comparisons': result.data
                }
            else:
                return {
                    'status': 'no_data',
                    'message': 'No product comparison data available'
                }
                
        except Exception as e:
            logger.error(f"Product period comparison error: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def get_preset_period_analysis(self, preset: str, platform: Optional[str] = None) -> dict:
        """プリセット期間での分析"""
        today = date.today()
        
        if preset == 'today':
            start_date = today
            end_date = today
            group_by = 'day'
        elif preset == 'yesterday':
            start_date = today - timedelta(days=1)
            end_date = today - timedelta(days=1)
            group_by = 'day'
        elif preset == 'last_7_days':
            start_date = today - timedelta(days=7)
            end_date = today - timedelta(days=1)
            group_by = 'day'
        elif preset == 'last_30_days':
            start_date = today - timedelta(days=30)
            end_date = today - timedelta(days=1)
            group_by = 'day'
        elif preset == 'this_week':
            # 今週の月曜日から
            days_since_monday = today.weekday()
            start_date = today - timedelta(days=days_since_monday)
            end_date = today
            group_by = 'day'
        elif preset == 'last_week':
            # 先週の月曜日から日曜日
            days_since_monday = today.weekday()
            last_monday = today - timedelta(days=days_since_monday + 7)
            start_date = last_monday
            end_date = last_monday + timedelta(days=6)
            group_by = 'day'
        elif preset == 'this_month':
            start_date = today.replace(day=1)
            end_date = today
            group_by = 'day'
        elif preset == 'last_month':
            # 先月の1日から末日
            first_this_month = today.replace(day=1)
            last_month_end = first_this_month - timedelta(days=1)
            start_date = last_month_end.replace(day=1)
            end_date = last_month_end
            group_by = 'day'
        elif preset == 'this_quarter':
            # 今四半期
            quarter = (today.month - 1) // 3 + 1
            start_date = date(today.year, (quarter - 1) * 3 + 1, 1)
            end_date = today
            group_by = 'month'
        elif preset == 'this_year':
            start_date = date(today.year, 1, 1)
            end_date = today
            group_by = 'month'
        else:
            return {
                'status': 'error',
                'message': f'Unknown preset: {preset}'
            }
        
        return self.get_custom_period_sales(start_date, end_date, group_by, platform)
    
    def get_period_comparison_presets(self, 
                                    preset: str, 
                                    platform: Optional[str] = None) -> dict:
        """プリセット期間比較"""
        today = date.today()
        
        if preset == 'this_vs_last_week':
            # 今週 vs 先週
            days_since_monday = today.weekday()
            this_week_start = today - timedelta(days=days_since_monday)
            this_week_end = today
            
            last_week_start = this_week_start - timedelta(days=7)
            last_week_end = this_week_start - timedelta(days=1)
            
        elif preset == 'this_vs_last_month':
            # 今月 vs 先月
            this_month_start = today.replace(day=1)
            this_month_end = today
            
            last_month_end = this_month_start - timedelta(days=1)
            last_month_start = last_month_end.replace(day=1)
            
        elif preset == 'last_30_vs_previous_30':
            # 過去30日 vs その前の30日
            this_month_end = today - timedelta(days=1)
            this_month_start = this_month_end - timedelta(days=29)
            
            last_month_end = this_month_start - timedelta(days=1)
            last_month_start = last_month_end - timedelta(days=29)
            
        else:
            return {
                'status': 'error',
                'message': f'Unknown comparison preset: {preset}'
            }
        
        return self.compare_periods(
            this_month_start, this_month_end,
            last_month_start, last_month_end,
            platform
        )


def add_period_analytics_endpoints(app, period_api: PeriodAnalyticsAPI):
    """期間別分析エンドポイントを追加"""
    
    @app.get("/period-analytics/custom")
    async def get_custom_period_analytics(
        start_date: str = Query(..., description="開始日 (YYYY-MM-DD)"),
        end_date: str = Query(..., description="終了日 (YYYY-MM-DD)"),
        group_by: str = Query('day', description="集計単位: day/week/month/quarter/year"),
        platform: Optional[str] = Query(None, description="プラットフォームフィルター"),
        include_profit: bool = Query(True, description="利益データを含む")
    ):
        """
        カスタム期間での売上分析
        
        例：
        - /period-analytics/custom?start_date=2024-01-01&end_date=2024-01-31&group_by=day
        - /period-analytics/custom?start_date=2024-01-01&end_date=2024-12-31&group_by=month&platform=rakuten
        """
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d').date()
            end = datetime.strptime(end_date, '%Y-%m-%d').date()
            
            if start > end:
                raise HTTPException(status_code=400, detail="開始日は終了日より前である必要があります")
            
            result = period_api.get_custom_period_sales(start, end, group_by, platform, include_profit)
            return result
            
        except ValueError:
            raise HTTPException(status_code=400, detail="日付形式が正しくありません (YYYY-MM-DD)")
        except Exception as e:
            logger.error(f"Custom period analytics error: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/period-analytics/preset/{preset}")
    async def get_preset_period_analytics(
        preset: str,
        platform: Optional[str] = Query(None, description="プラットフォームフィルター")
    ):
        """
        プリセット期間での売上分析
        
        利用可能なプリセット:
        - today: 今日
        - yesterday: 昨日
        - last_7_days: 過去7日
        - last_30_days: 過去30日
        - this_week: 今週
        - last_week: 先週
        - this_month: 今月
        - last_month: 先月
        - this_quarter: 今四半期
        - this_year: 今年
        """
        try:
            result = period_api.get_preset_period_analysis(preset, platform)
            return result
        except Exception as e:
            logger.error(f"Preset period analytics error: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/period-analytics/compare")
    async def compare_periods_endpoint(
        current_start: str = Query(..., description="現在期間開始日 (YYYY-MM-DD)"),
        current_end: str = Query(..., description="現在期間終了日 (YYYY-MM-DD)"),
        previous_start: str = Query(..., description="比較期間開始日 (YYYY-MM-DD)"),
        previous_end: str = Query(..., description="比較期間終了日 (YYYY-MM-DD)"),
        platform: Optional[str] = Query(None, description="プラットフォームフィルター")
    ):
        """
        期間比較分析
        
        例：
        - 今月 vs 先月の比較
        - 今週 vs 先週の比較
        """
        try:
            current_start_date = datetime.strptime(current_start, '%Y-%m-%d').date()
            current_end_date = datetime.strptime(current_end, '%Y-%m-%d').date()
            previous_start_date = datetime.strptime(previous_start, '%Y-%m-%d').date()
            previous_end_date = datetime.strptime(previous_end, '%Y-%m-%d').date()
            
            result = period_api.compare_periods(
                current_start_date, current_end_date,
                previous_start_date, previous_end_date,
                platform
            )
            return result
            
        except ValueError:
            raise HTTPException(status_code=400, detail="日付形式が正しくありません (YYYY-MM-DD)")
        except Exception as e:
            logger.error(f"Period comparison error: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/period-analytics/compare-preset/{preset}")
    async def compare_preset_periods(
        preset: str,
        platform: Optional[str] = Query(None, description="プラットフォームフィルター")
    ):
        """
        プリセット期間比較
        
        利用可能なプリセット:
        - this_vs_last_week: 今週 vs 先週
        - this_vs_last_month: 今月 vs 先月
        - last_30_vs_previous_30: 過去30日 vs その前の30日
        """
        try:
            result = period_api.get_period_comparison_presets(preset, platform)
            return result
        except Exception as e:
            logger.error(f"Preset period comparison error: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/period-analytics/products/compare")
    async def compare_product_periods(
        current_start: str = Query(..., description="現在期間開始日 (YYYY-MM-DD)"),
        current_end: str = Query(..., description="現在期間終了日 (YYYY-MM-DD)"),
        previous_start: str = Query(..., description="比較期間開始日 (YYYY-MM-DD)"),
        previous_end: str = Query(..., description="比較期間終了日 (YYYY-MM-DD)"),
        sku: Optional[str] = Query(None, description="特定商品SKU")
    ):
        """
        商品別期間比較分析
        
        商品の売上・数量の期間比較
        """
        try:
            current_start_date = datetime.strptime(current_start, '%Y-%m-%d').date()
            current_end_date = datetime.strptime(current_end, '%Y-%m-%d').date()
            previous_start_date = datetime.strptime(previous_start, '%Y-%m-%d').date()
            previous_end_date = datetime.strptime(previous_end, '%Y-%m-%d').date()
            
            result = period_api.get_product_period_comparison(
                current_start_date, current_end_date,
                previous_start_date, previous_end_date,
                sku
            )
            return result
            
        except ValueError:
            raise HTTPException(status_code=400, detail="日付形式が正しくありません (YYYY-MM-DD)")
        except Exception as e:
            logger.error(f"Product period comparison error: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))


# 統合関数
def integrate_period_analytics(app):
    """期間別分析機能をメインアプリに統合"""
    try:
        period_api = PeriodAnalyticsAPI()
        add_period_analytics_endpoints(app, period_api)
        logger.info("Period analytics endpoints added successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to integrate period analytics: {str(e)}")
        return False