"""
Complete Integration Module
完全統合モジュール - 楽天システムに全機能を統合
"""

import sys
import os
from pathlib import Path

# 必要なモジュールのインポート
supabase_dir = Path(__file__).parent.parent / "supabase"
sys.path.append(str(supabase_dir))

from enhanced_client import EnhancedSupabaseClient
from sales_dashboard_client import SalesDashboardClient
from enhanced_analytics import RakutenAnalytics
from sales_dashboard_api import SalesDashboardAPI
from period_analytics_api import PeriodAnalyticsAPI

from core.database import supabase
from core.config import Config
import logging

logger = logging.getLogger(__name__)

class CompleteSystemIntegration:
    """完全システム統合クラス"""
    
    def __init__(self):
        if not supabase:
            raise Exception("Supabase client not initialized")
        
        # 各種クライアントの初期化
        self.enhanced_client = EnhancedSupabaseClient(Config.SUPABASE_URL, Config.SUPABASE_KEY)
        self.sales_dashboard = SalesDashboardClient(supabase)
        self.analytics = RakutenAnalytics(Config.SUPABASE_URL, Config.SUPABASE_KEY)
        self.dashboard_api = SalesDashboardAPI()
        self.period_api = PeriodAnalyticsAPI()
    
    def test_system_integration(self):
        """システム統合テスト"""
        results = {}
        
        try:
            # 1. 基本接続テスト
            results['connection'] = self.enhanced_client.test_connection()
            
            # 2. 在庫補充提案テスト
            restock = self.enhanced_client.get_restock_suggestions(days_to_analyze=7)
            results['restock_suggestions'] = restock['status'] == 'success'
            
            # 3. 売上ダッシュボードテスト
            dashboard = self.dashboard_api.get_sales_overview(7)
            results['sales_dashboard'] = dashboard['status'] in ['success', 'no_data']
            
            # 4. 期間分析テスト
            period_analysis = self.period_api.get_preset_period_analysis('last_7_days')
            results['period_analytics'] = period_analysis['status'] in ['success', 'no_data']
            
            # 5. アラート機能テスト
            alerts = self.analytics.get_alert_notifications()
            results['alert_system'] = alerts['status'] == 'success'
            
            logger.info("System integration test completed")
            return {
                'status': 'success',
                'test_results': results,
                'overall_health': all(results.values())
            }
            
        except Exception as e:
            logger.error(f"System integration test failed: {str(e)}")
            return {
                'status': 'error',
                'message': str(e),
                'test_results': results
            }
    
    def get_system_status(self):
        """システム全体のステータス取得"""
        try:
            # プラットフォーム情報
            platforms = supabase.table('platform').select('*').execute()
            
            # 商品数
            products = supabase.table('unified_products').select('id').execute()
            
            # 注文数（過去30日）
            from datetime import date, timedelta
            thirty_days_ago = date.today() - timedelta(days=30)
            orders = supabase.table('orders').select('id').gte('order_date', thirty_days_ago.isoformat()).execute()
            
            return {
                'status': 'success',
                'system_info': {
                    'platforms_configured': len(platforms.data) if platforms.data else 0,
                    'total_products': len(products.data) if products.data else 0,
                    'orders_last_30_days': len(orders.data) if orders.data else 0,
                    'features_available': [
                        'sales_dashboard',
                        'period_analytics', 
                        'inventory_management',
                        'alert_system',
                        'product_performance_analysis',
                        'cross_platform_comparison'
                    ]
                }
            }
            
        except Exception as e:
            logger.error(f"System status check failed: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }


def add_complete_integration_endpoints(app, integration: CompleteSystemIntegration):
    """完全統合エンドポイントを追加"""
    
    @app.get("/system/status")
    async def get_system_status():
        """システム全体のステータス"""
        return integration.get_system_status()
    
    @app.get("/system/test")
    async def test_system_integration():
        """システム統合テスト"""
        return integration.test_system_integration()
    
    @app.get("/system/health-check")
    async def comprehensive_health_check():
        """包括的ヘルスチェック"""
        try:
            # 基本ヘルスチェック
            basic_health = {
                "supabase_connected": integration.enhanced_client.test_connection(),
                "database_responsive": True
            }
            
            # 機能別ヘルスチェック
            feature_health = {}
            
            # 売上分析機能
            try:
                dashboard_test = integration.dashboard_api.get_sales_overview(1)
                feature_health['sales_analytics'] = dashboard_test['status'] in ['success', 'no_data']
            except:
                feature_health['sales_analytics'] = False
            
            # 期間分析機能
            try:
                period_test = integration.period_api.get_preset_period_analysis('today')
                feature_health['period_analytics'] = period_test['status'] in ['success', 'no_data']
            except:
                feature_health['period_analytics'] = False
            
            # 在庫管理機能
            try:
                inventory_test = integration.enhanced_client.get_restock_suggestions(days_to_analyze=1)
                feature_health['inventory_management'] = inventory_test['status'] in ['success']
            except:
                feature_health['inventory_management'] = False
            
            overall_health = all(basic_health.values()) and any(feature_health.values())
            
            return {
                'status': 'healthy' if overall_health else 'degraded',
                'basic_health': basic_health,
                'feature_health': feature_health,
                'overall_score': sum([basic_health[k] for k in basic_health] + [feature_health[k] for k in feature_health]) / (len(basic_health) + len(feature_health))
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }


def integrate_complete_system(app):
    """完全システムをメインアプリに統合"""
    try:
        # 完全統合システムの初期化
        integration = CompleteSystemIntegration()
        
        # 各種機能の統合
        from sales_dashboard_api import add_sales_dashboard_endpoints
        from period_analytics_api import add_period_analytics_endpoints
        from enhanced_analytics import create_analytics_endpoints
        
        # エンドポイントの追加
        add_sales_dashboard_endpoints(app, integration.dashboard_api)
        add_period_analytics_endpoints(app, integration.period_api)
        create_analytics_endpoints(app, integration.analytics)
        add_complete_integration_endpoints(app, integration)
        
        # APIルート一覧の更新
        @app.get("/api/complete", include_in_schema=False)
        async def complete_api_list():
            """完全統合API一覧"""
            return {
                "message": "楽天注文同期 & 完全売上分析システム",
                "version": "3.0 - Complete Edition",
                "features": {
                    "基本機能": [
                        "/health",
                        "/sync-orders",
                        "/sync-orders-range"
                    ],
                    "システム管理": [
                        "/system/status",
                        "/system/test", 
                        "/system/health-check"
                    ],
                    "売上ダッシュボード": [
                        "/sales-dashboard",
                        "/sales-dashboard/overview",
                        "/sales-dashboard/platforms",
                        "/sales-dashboard/products",
                        "/sales-dashboard/trends",
                        "/sales-dashboard/summary-stats"
                    ],
                    "期間別分析": [
                        "/period-analytics/custom",
                        "/period-analytics/preset/{preset}",
                        "/period-analytics/compare",
                        "/period-analytics/compare-preset/{preset}"
                    ],
                    "高度な分析": [
                        "/analytics/dashboard",
                        "/analytics/product/{sku}",
                        "/analytics/weekly-report",
                        "/analytics/alerts"
                    ]
                },
                "data_sources": [
                    "楽天市場API",
                    "Amazon SP-API (予定)",
                    "カラーミーショップAPI (予定)",
                    "エアレジAPI (予定)"
                ]
            }
        
        logger.info("Complete system integration successful")
        return True
        
    except Exception as e:
        logger.error(f"Complete system integration failed: {str(e)}")
        return False