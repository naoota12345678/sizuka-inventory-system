"""
Enhanced Analytics Module for Rakuten Order Sync
楽天注文同期システム用の拡張分析機能
"""

import sys
import os
from pathlib import Path

# Supabaseクライアントのパスを追加
supabase_dir = Path(__file__).parent.parent / "supabase"
sys.path.append(str(supabase_dir))

from enhanced_client import EnhancedSupabaseClient
from datetime import datetime, date, timedelta
from typing import Dict, List, Any, Optional
import logging

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RakutenAnalytics:
    """楽天データ分析クラス"""
    
    def __init__(self, supabase_url: str, supabase_key: str):
        self.client = EnhancedSupabaseClient(supabase_url, supabase_key)
        self.platform_code = 'rakuten'
    
    def get_daily_dashboard(self, days_back: int = 7) -> Dict[str, Any]:
        """日次ダッシュボードデータ取得"""
        end_date = date.today()
        start_date = end_date - timedelta(days=days_back)
        
        try:
            # 基本ダッシュボードデータ
            dashboard_data = self.client.get_dashboard_data(start_date, end_date)
            
            # 楽天固有のトレンド分析
            trend_data = self.client.analyze_sales_trend(
                platform_code=self.platform_code,
                days_back=days_back
            )
            
            # 在庫補充提案
            restock_suggestions = self.client.get_restock_suggestions(
                days_to_analyze=14,
                safety_stock_days=5
            )
            
            # パフォーマンススコア
            performance_scores = self.client.get_product_performance_scores()
            
            return {
                'status': 'success',
                'period': f'{start_date} to {end_date}',
                'dashboard': dashboard_data,
                'trend': trend_data,
                'restock_suggestions': restock_suggestions,
                'top_performers': performance_scores.get('scores', [])[:10],
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Daily dashboard error: {str(e)}")
            return {
                'status': 'error',
                'message': str(e),
                'generated_at': datetime.now().isoformat()
            }
    
    def analyze_product_performance(self, sku: str) -> Dict[str, Any]:
        """個別商品の詳細分析"""
        try:
            # 基本情報
            product_details = self.client.get_product_details(sku)
            
            # 在庫移動履歴
            inventory_history = self.client.get_inventory_movement_history(sku, days_back=30)
            
            # 売上トレンド
            sales_trend = self.client.analyze_sales_trend(
                product_sku=sku,
                platform_code=self.platform_code,
                days_back=30
            )
            
            return {
                'status': 'success',
                'sku': sku,
                'product_info': product_details,
                'inventory_history': inventory_history,
                'sales_trend': sales_trend,
                'analysis_date': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Product analysis error for {sku}: {str(e)}")
            return {
                'status': 'error',
                'sku': sku,
                'message': str(e)
            }
    
    def generate_weekly_report(self) -> Dict[str, Any]:
        """週次レポート生成"""
        end_date = date.today()
        start_date = end_date - timedelta(days=7)
        
        try:
            # 売上レポート
            sales_report = self.client.get_sales_report(
                start_date=start_date,
                end_date=end_date,
                platform=self.platform_code
            )
            
            # 在庫レポート
            inventory_report = self.client.get_inventory_report()
            
            # クロスプラットフォーム分析
            cross_platform = self.client.get_cross_platform_analysis()
            
            return {
                'status': 'success',
                'report_period': f'{start_date} to {end_date}',
                'sales_report': sales_report,
                'inventory_report': inventory_report,
                'cross_platform_analysis': cross_platform,
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Weekly report error: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def process_order_analytics(self, order_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """注文データの分析処理"""
        try:
            if not order_data:
                return {
                    'status': 'no_data',
                    'message': 'No order data to process'
                }
            
            # 在庫更新データを準備
            inventory_updates = []
            
            for order in order_data:
                order_items = order.get('items', [])
                for item in order_items:
                    inventory_updates.append({
                        'sku': item.get('productCode', ''),
                        'quantity': item.get('quantity', 0),
                        'type': 'sale',
                        'platform': self.platform_code,
                        'reference_id': order.get('orderNumber', ''),
                        'notes': f"Order from {order.get('orderDate', '')}"
                    })
            
            # 一括在庫更新
            if inventory_updates:
                update_result = self.client.batch_update_inventory(inventory_updates)
                
                return {
                    'status': 'success',
                    'processed_orders': len(order_data),
                    'processed_items': len(inventory_updates),
                    'inventory_update': update_result,
                    'processed_at': datetime.now().isoformat()
                }
            else:
                return {
                    'status': 'no_items',
                    'message': 'No items found in orders'
                }
                
        except Exception as e:
            logger.error(f"Order analytics processing error: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def get_alert_notifications(self) -> Dict[str, Any]:
        """アラート通知の取得"""
        try:
            alerts = []
            
            # 在庫アラート
            restock_suggestions = self.client.get_restock_suggestions(
                days_to_analyze=7,
                safety_stock_days=3
            )
            
            critical_stock = [
                item for item in restock_suggestions.get('suggestions', [])
                if item.get('urgency_level') in ['critical', 'high']
            ]
            
            if critical_stock:
                alerts.append({
                    'type': 'inventory_critical',
                    'message': f'{len(critical_stock)} products need immediate restocking',
                    'priority': 'high',
                    'details': critical_stock[:5]  # 最初の5件のみ
                })
            
            # 売上異常検知（簡易版）
            trend_data = self.client.analyze_sales_trend(
                platform_code=self.platform_code,
                days_back=7
            )
            
            if trend_data.get('status') == 'success':
                recent_trends = trend_data.get('trend_data', [])[:3]  # 最新3日分
                
                declining_days = sum(
                    1 for day in recent_trends 
                    if day.get('growth_rate', 0) < -20
                )
                
                if declining_days >= 2:
                    alerts.append({
                        'type': 'sales_decline',
                        'message': 'Sales declining for 2+ consecutive days',
                        'priority': 'medium',
                        'details': recent_trends
                    })
            
            return {
                'status': 'success',
                'alert_count': len(alerts),
                'alerts': alerts,
                'checked_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Alert notifications error: {str(e)}")
            return {
                'status': 'error',
                'message': str(e),
                'alerts': []
            }
    
    def export_analytics_data(self, export_type: str = 'sales', 
                            days_back: int = 30) -> Dict[str, Any]:
        """分析データのエクスポート"""
        try:
            end_date = date.today()
            start_date = end_date - timedelta(days=days_back)
            
            if export_type == 'sales':
                data = self.client.get_sales_report(start_date, end_date, self.platform_code)
                filename = f"rakuten_sales_report_{start_date}_{end_date}.csv"
                
                if data.get('status') == 'success':
                    export_result = self.client.export_to_csv(
                        data.get('daily_data', []), 
                        filename
                    )
                    
                    return {
                        'status': 'success',
                        'export_type': export_type,
                        'filename': filename,
                        'message': export_result
                    }
            
            elif export_type == 'inventory':
                data = self.client.get_inventory_report()
                filename = f"inventory_report_{datetime.now().strftime('%Y%m%d')}.csv"
                
                if data.get('status') == 'success':
                    export_result = self.client.export_to_csv(
                        data.get('inventory_data', []), 
                        filename
                    )
                    
                    return {
                        'status': 'success',
                        'export_type': export_type,
                        'filename': filename,
                        'message': export_result
                    }
            
            return {
                'status': 'error',
                'message': f'Unsupported export type: {export_type}'
            }
            
        except Exception as e:
            logger.error(f"Export error: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }


# FastAPI統合用のヘルパー関数
def create_analytics_endpoints(app, analytics: RakutenAnalytics):
    """FastAPIアプリにアナリティクスエンドポイントを追加"""
    
    @app.get("/analytics/dashboard")
    async def get_analytics_dashboard(days_back: int = 7):
        """分析ダッシュボード"""
        return analytics.get_daily_dashboard(days_back)
    
    @app.get("/analytics/product/{sku}")
    async def get_product_analytics(sku: str):
        """商品別分析"""
        return analytics.analyze_product_performance(sku)
    
    @app.get("/analytics/weekly-report")
    async def get_weekly_report():
        """週次レポート"""
        return analytics.generate_weekly_report()
    
    @app.get("/analytics/alerts")
    async def get_alerts():
        """アラート通知"""
        return analytics.get_alert_notifications()
    
    @app.get("/analytics/export/{export_type}")
    async def export_data(export_type: str, days_back: int = 30):
        """データエクスポート"""
        return analytics.export_analytics_data(export_type, days_back)
    
    @app.post("/analytics/process-orders")
    async def process_orders_analytics(order_data: List[Dict[str, Any]]):
        """注文データの分析処理"""
        return analytics.process_order_analytics(order_data)


# 使用例
if __name__ == "__main__":
    # 初期化（環境変数から取得することを推奨）
    analytics = RakutenAnalytics(
        supabase_url="YOUR_SUPABASE_URL",
        supabase_key="YOUR_SUPABASE_KEY"
    )
    
    # 日次ダッシュボード
    dashboard = analytics.get_daily_dashboard(days_back=7)
    print("Dashboard Status:", dashboard['status'])
    
    # アラート確認
    alerts = analytics.get_alert_notifications()
    print("Alert Count:", alerts.get('alert_count', 0))