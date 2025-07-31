"""
Sales Dashboard API Integration
楽天システム用売上ダッシュボードAPI統合
"""

import sys
import os
from pathlib import Path
from datetime import date, timedelta
from typing import Optional

# Supabaseクライアントのパスを追加
supabase_dir = Path(__file__).parent.parent / "supabase"
sys.path.append(str(supabase_dir))

from sales_dashboard_client import SalesDashboardClient
from core.database import supabase
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)

class SalesDashboardAPI:
    """売上ダッシュボードAPI統合クラス"""
    
    def __init__(self):
        if not supabase:
            raise Exception("Supabase client not initialized")
        self.dashboard = SalesDashboardClient(supabase)
    
    def get_sales_overview(self, days_back: int = 7) -> dict:
        """売上概要取得"""
        end_date = date.today()
        start_date = end_date - timedelta(days=days_back)
        
        return self.dashboard.get_consolidated_sales_summary(
            start_date, end_date, 'day'
        )
    
    def get_platform_analysis(self, days_back: int = 30) -> dict:
        """プラットフォーム分析"""
        end_date = date.today()
        start_date = end_date - timedelta(days=days_back)
        
        return self.dashboard.get_platform_comparison(start_date, end_date)
    
    def get_product_rankings(self, 
                           days_back: int = 30, 
                           platform_filter: Optional[str] = None,
                           limit: int = 50) -> dict:
        """商品ランキング"""
        end_date = date.today()
        start_date = end_date - timedelta(days=days_back)
        
        return self.dashboard.get_product_sales_ranking(
            start_date, end_date, platform_filter, limit
        )
    
    def get_product_details(self, sku: str, days_back: int = 30) -> dict:
        """商品詳細分析"""
        end_date = date.today()
        start_date = end_date - timedelta(days=days_back)
        
        return self.dashboard.get_product_detail_analysis(sku, start_date, end_date)
    
    def get_trend_data(self, 
                      days_back: int = 30, 
                      platform_filter: Optional[str] = None) -> dict:
        """トレンドデータ"""
        end_date = date.today()
        start_date = end_date - timedelta(days=days_back)
        
        return self.dashboard.get_sales_trend_chart_data(
            start_date, end_date, platform_filter
        )
    
    def get_category_analysis(self, days_back: int = 30) -> dict:
        """カテゴリ分析"""
        end_date = date.today()
        start_date = end_date - timedelta(days=days_back)
        
        return self.dashboard.get_category_performance(start_date, end_date)
    
    def get_complete_dashboard(self, days_back: int = 30) -> dict:
        """完全ダッシュボード"""
        end_date = date.today()
        start_date = end_date - timedelta(days=days_back)
        
        return self.dashboard.get_complete_dashboard(start_date, end_date)


def add_sales_dashboard_endpoints(app, dashboard_api: SalesDashboardAPI):
    """FastAPIアプリケーションに売上ダッシュボードエンドポイントを追加"""
    
    @app.get("/sales-dashboard")
    async def get_sales_dashboard(days_back: int = 30):
        """
        統合売上ダッシュボード
        - 全サイト合算売上
        - プラットフォーム別比較
        - 商品ランキング
        - トレンド分析
        """
        try:
            result = dashboard_api.get_complete_dashboard(days_back)
            return result
        except Exception as e:
            logger.error(f"Sales dashboard error: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/sales-dashboard/overview")
    async def get_sales_overview(days_back: int = 7):
        """
        売上概要
        日次/週次/月次の売上サマリー
        """
        try:
            result = dashboard_api.get_sales_overview(days_back)
            return result
        except Exception as e:
            logger.error(f"Sales overview error: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/sales-dashboard/platforms")
    async def get_platform_comparison(days_back: int = 30):
        """
        プラットフォーム比較分析
        - 楽天、Amazon、カラーミー等の比較
        - 市場シェア、成長率
        """
        try:
            result = dashboard_api.get_platform_analysis(days_back)
            return result
        except Exception as e:
            logger.error(f"Platform comparison error: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/sales-dashboard/products")
    async def get_product_rankings(
        days_back: int = 30, 
        platform: Optional[str] = None,
        limit: int = 50
    ):
        """
        商品別売上ランキング
        - 売上、利益、数量別ランキング
        - プラットフォーム別フィルター可能
        """
        try:
            result = dashboard_api.get_product_rankings(days_back, platform, limit)
            return result
        except Exception as e:
            logger.error(f"Product rankings error: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/sales-dashboard/products/{sku}")
    async def get_product_detail(sku: str, days_back: int = 30):
        """
        個別商品の詳細分析
        - プラットフォーム別売上
        - 日次トレンド
        - 利益分析
        """
        try:
            result = dashboard_api.get_product_details(sku, days_back)
            return result
        except Exception as e:
            logger.error(f"Product detail error for {sku}: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/sales-dashboard/trends")
    async def get_sales_trends(
        days_back: int = 30, 
        platform: Optional[str] = None
    ):
        """
        売上トレンドデータ（チャート用）
        - 日次売上推移
        - プラットフォーム別トレンド
        """
        try:
            result = dashboard_api.get_trend_data(days_back, platform)
            return result
        except Exception as e:
            logger.error(f"Sales trends error: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/sales-dashboard/categories")
    async def get_category_analysis(days_back: int = 30):
        """
        カテゴリ別売上分析
        - カテゴリ別パフォーマンス
        - 商品構成分析
        """
        try:
            result = dashboard_api.get_category_analysis(days_back)
            return result
        except Exception as e:
            logger.error(f"Category analysis error: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/sales-dashboard/summary-stats")
    async def get_summary_statistics(days_back: int = 30):
        """
        サマリー統計
        KPI用の主要指標
        """
        try:
            dashboard_data = dashboard_api.get_complete_dashboard(days_back)
            
            if dashboard_data['status'] != 'success':
                return dashboard_data
            
            # KPI抽出
            consolidated = dashboard_data['data']['consolidated_sales']
            platform_comp = dashboard_data['data']['platform_comparison']
            products = dashboard_data['data']['top_products']
            
            summary_stats = {
                'status': 'success',
                'period_days': days_back,
                'kpis': {
                    'total_sales': consolidated.get('summary', {}).get('total_sales', 0),
                    'total_orders': consolidated.get('summary', {}).get('total_orders', 0),
                    'total_profit': consolidated.get('summary', {}).get('total_profit', 0),
                    'profit_margin': consolidated.get('summary', {}).get('overall_profit_margin', 0),
                    'avg_daily_sales': consolidated.get('summary', {}).get('avg_daily_sales', 0),
                    'active_platforms': platform_comp.get('market_overview', {}).get('active_platforms', 0),
                    'best_performing_platform': platform_comp.get('market_overview', {}).get('best_performer', 'N/A'),
                    'total_products_sold': products.get('summary', {}).get('total_products_analyzed', 0),
                    'top_product_sku': products.get('product_rankings', [{}])[0].get('sku', 'N/A') if products.get('product_rankings') else 'N/A'
                }
            }
            
            return summary_stats
            
        except Exception as e:
            logger.error(f"Summary statistics error: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))


# 使用例（main.pyに統合）
def integrate_sales_dashboard_with_main_app(app):
    """
    main.pyのFastAPIアプリに売上ダッシュボード機能を統合
    
    main.pyに以下を追加:
    
    from sales_dashboard_api import integrate_sales_dashboard_with_main_app
    
    # アプリケーション起動後に追加
    integrate_sales_dashboard_with_main_app(app)
    """
    try:
        dashboard_api = SalesDashboardAPI()
        add_sales_dashboard_endpoints(app, dashboard_api)
        logger.info("Sales dashboard endpoints added successfully")
        
        # 既存のAPIエンドポイント一覧を更新
        @app.get("/api", include_in_schema=False)
        async def api_root():
            """APIエンドポイント一覧（更新版）"""
            return {
                "message": "楽天注文同期 & 売上分析API",
                "version": "2.0",
                "endpoints": {
                    "基本機能": [
                        "/health",
                        "/sync-orders",
                        "/sync-orders-range", 
                        "/check-connection"
                    ],
                    "在庫管理": [
                        "/initialize-inventory/rakuten",
                        "/update-sales-rakuten",
                        "/inventory-dashboard"
                    ],
                    "売上ダッシュボード": [
                        "/sales-dashboard",
                        "/sales-dashboard/overview",
                        "/sales-dashboard/platforms",
                        "/sales-dashboard/products",
                        "/sales-dashboard/products/{sku}",
                        "/sales-dashboard/trends",
                        "/sales-dashboard/categories",
                        "/sales-dashboard/summary-stats"
                    ],
                    "分析機能": [
                        "/analytics/dashboard",
                        "/analytics/product/{sku}",
                        "/analytics/weekly-report",
                        "/analytics/alerts"
                    ]
                }
            }
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to integrate sales dashboard: {str(e)}")
        return False