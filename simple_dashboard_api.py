"""
Simple Dashboard API
シンプルな売上ダッシュボードAPI
"""

from datetime import date, timedelta
from core.database import supabase
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)

class SimpleDashboardAPI:
    """シンプルな売上ダッシュボードAPI"""
    
    def __init__(self):
        if not supabase:
            raise Exception("Supabase client not initialized")
        self.client = supabase
    
    def get_simple_sales_summary(self, days_back: int = 30) -> dict:
        """シンプルな売上サマリー"""
        try:
            start_date = date.today() - timedelta(days=days_back)
            
            # 直接SQLクエリで売上データを取得
            query = f"""
            SELECT 
                p.platform_code,
                p.name as platform_name,
                SUM(oi.price * oi.quantity) as total_sales,
                COUNT(DISTINCT o.id) as order_count,
                SUM(oi.quantity) as total_quantity
            FROM orders o
            INNER JOIN order_items oi ON o.id = oi.order_id  
            INNER JOIN platform p ON o.platform_id = p.id
            WHERE o.order_date >= '{start_date}'
                AND o.status = 'completed'
            GROUP BY p.platform_code, p.name
            ORDER BY total_sales DESC
            """
            
            result = self.client.rpc('exec_sql', {'query': query}).execute()
            
            if not result.data:
                # RPCが使えない場合の代替方法
                return self._get_fallback_summary(days_back)
            
            # 集計計算
            total_sales = sum(float(row.get('total_sales', 0)) for row in result.data)
            total_orders = sum(row.get('order_count', 0) for row in result.data)
            total_quantity = sum(row.get('total_quantity', 0) for row in result.data)
            
            return {
                'status': 'success',
                'period_days': days_back,
                'summary': {
                    'total_sales': total_sales,
                    'total_orders': total_orders,
                    'total_quantity': total_quantity,
                    'avg_order_value': round(total_sales / max(total_orders, 1), 2),
                    'platforms': len(result.data)
                },
                'platform_breakdown': result.data
            }
            
        except Exception as e:
            logger.error(f"Simple sales summary error: {str(e)}")
            return self._get_fallback_summary(days_back)
    
    def _get_fallback_summary(self, days_back: int) -> dict:
        """フォールバック用のサマリー取得"""
        try:
            start_date = date.today() - timedelta(days=days_back)
            
            # 注文データを直接取得
            orders_result = self.client.table('orders')\
                .select('id, platform_id, total_amount, order_date')\
                .gte('order_date', start_date.isoformat())\
                .eq('status', 'completed')\
                .execute()
            
            if not orders_result.data:
                return {
                    'status': 'success',
                    'period_days': days_back,
                    'message': 'No data found in the specified period',
                    'summary': {
                        'total_sales': 0,
                        'total_orders': 0,
                        'total_quantity': 0
                    }
                }
            
            # プラットフォーム情報を取得
            platforms_result = self.client.table('platform').select('*').execute()
            platform_map = {p['id']: p for p in platforms_result.data} if platforms_result.data else {}
            
            # 注文明細を取得
            order_ids = [order['id'] for order in orders_result.data]
            items_result = self.client.table('order_items')\
                .select('order_id, quantity, price')\
                .in_('order_id', order_ids)\
                .execute()
            
            # 手動で集計
            total_sales = 0
            total_quantity = 0
            platform_sales = {}
            
            if items_result.data:
                for item in items_result.data:
                    item_total = float(item.get('price', 0)) * item.get('quantity', 0)
                    total_sales += item_total
                    total_quantity += item.get('quantity', 0)
                    
                    # プラットフォーム別集計
                    order_id = item['order_id']
                    order = next((o for o in orders_result.data if o['id'] == order_id), None)
                    if order:
                        platform_id = order['platform_id']
                        platform_info = platform_map.get(platform_id, {'platform_code': 'unknown', 'name': 'Unknown'})
                        platform_code = platform_info['platform_code']
                        
                        if platform_code not in platform_sales:
                            platform_sales[platform_code] = {
                                'platform_name': platform_info['name'],
                                'total_sales': 0,
                                'order_count': 0
                            }
                        
                        platform_sales[platform_code]['total_sales'] += item_total
            
            # 注文数をプラットフォーム別に集計
            for order in orders_result.data:
                platform_id = order['platform_id']
                platform_info = platform_map.get(platform_id, {'platform_code': 'unknown'})
                platform_code = platform_info['platform_code']
                
                if platform_code in platform_sales:
                    platform_sales[platform_code]['order_count'] += 1
            
            return {
                'status': 'success',
                'period_days': days_back,
                'summary': {
                    'total_sales': round(total_sales, 2),
                    'total_orders': len(orders_result.data),
                    'total_quantity': total_quantity,
                    'avg_order_value': round(total_sales / max(len(orders_result.data), 1), 2),
                    'platforms': len(platform_sales)
                },
                'platform_breakdown': [
                    {
                        'platform_code': code,
                        'platform_name': data['platform_name'],
                        'total_sales': round(data['total_sales'], 2),
                        'order_count': data['order_count']
                    }
                    for code, data in platform_sales.items()
                ]
            }
            
        except Exception as e:
            logger.error(f"Fallback summary error: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }


def add_simple_dashboard_endpoints(app, simple_api: SimpleDashboardAPI):
    """シンプルダッシュボードエンドポイントを追加"""
    
    @app.get("/simple-dashboard/summary")
    async def get_simple_summary(days_back: int = 30):
        """シンプルな売上サマリー"""
        try:
            result = simple_api.get_simple_sales_summary(days_back)
            return result
        except Exception as e:
            logger.error(f"Simple dashboard error: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/simple-dashboard/test")
    async def test_simple_dashboard():
        """テスト用エンドポイント"""
        try:
            # 基本的なデータ取得テスト
            orders = simple_api.client.table('orders').select('*').limit(5).execute()
            platforms = simple_api.client.table('platform').select('*').execute()
            
            return {
                'status': 'success',
                'test_results': {
                    'orders_count': len(orders.data) if orders.data else 0,
                    'platforms_count': len(platforms.data) if platforms.data else 0,
                    'sample_orders': orders.data[:3] if orders.data else []
                }
            }
        except Exception as e:
            logger.error(f"Simple dashboard test error: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }