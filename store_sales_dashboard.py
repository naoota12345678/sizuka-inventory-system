#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
販売店舗別売上ダッシュボードAPI
プラットフォーム別の売上合計を表示
"""

from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse, HTMLResponse
from datetime import datetime, timedelta
from typing import Optional
import pytz
from supabase import create_client

# Supabase接続
SUPABASE_URL = 'https://equrcpeifogdrxoldkpe.supabase.co'
SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ'

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_store_sales_summary(start_date: str = None, end_date: str = None):
    """
    販売店舗別売上サマリーを取得
    """
    try:
        # デフォルト期間（過去30日）
        if not end_date:
            end_date = datetime.now(pytz.timezone('Asia/Tokyo')).date().isoformat()
        if not start_date:
            start_date = (datetime.now(pytz.timezone('Asia/Tokyo')).date() - timedelta(days=30)).isoformat()
        
        print(f"期間: {start_date} ～ {end_date}")
        
        # 1. プラットフォーム情報を取得
        platforms_response = supabase.table('platform').select('*').execute()
        platform_map = {}
        if platforms_response.data:
            for platform in platforms_response.data:
                platform_map[platform['id']] = {
                    'name': platform.get('name', f'Platform_{platform["id"]}'),
                    'description': platform.get('description', '')
                }
        
        # 2. 期間内のordersを取得
        orders_query = supabase.table('orders').select('id, platform_id, order_date, order_number, total_amount').gte('order_date', start_date).lte('order_date', end_date)
        orders_response = orders_query.execute()
        
        if not orders_response.data:
            return {
                "status": "success", 
                "message": "該当期間にデータがありません",
                "period": {"start_date": start_date, "end_date": end_date},
                "stores": [],
                "summary": {"total_sales": 0, "total_orders": 0, "total_stores": 0}
            }
        
        # 3. order_itemsを取得して売上計算
        order_ids = [order['id'] for order in orders_response.data]
        
        # バッチ処理でorder_items取得
        batch_size = 100
        all_items = []
        
        for i in range(0, len(order_ids), batch_size):
            batch_ids = order_ids[i:i + batch_size]
            items_query = supabase.table('order_items').select('order_id, quantity, price').in_('order_id', batch_ids)
            items_response = items_query.execute()
            if items_response.data:
                all_items.extend(items_response.data)
        
        # 4. プラットフォーム別集計
        store_sales = {}
        
        for item in all_items:
            order_id = item.get('order_id')
            quantity = int(item.get('quantity', 0))
            price = float(item.get('price', 0))
            amount = quantity * price
            
            # 該当するorderのplatform_idを取得
            platform_id = None
            for order in orders_response.data:
                if order['id'] == order_id:
                    platform_id = order.get('platform_id')
                    break
            
            if platform_id is not None:
                if platform_id not in store_sales:
                    store_sales[platform_id] = {
                        'platform_id': platform_id,
                        'store_name': platform_map.get(platform_id, {}).get('name', f'店舗_{platform_id}'),
                        'total_sales': 0,
                        'total_items': 0,
                        'order_count': 0,
                        'orders': set()
                    }
                
                store_sales[platform_id]['total_sales'] += amount
                store_sales[platform_id]['total_items'] += quantity
                store_sales[platform_id]['orders'].add(order_id)
        
        # 5. 注文数を計算
        for platform_id in store_sales:
            store_sales[platform_id]['order_count'] = len(store_sales[platform_id]['orders'])
            # setは JSON serializable でないので削除
            del store_sales[platform_id]['orders']
        
        # 6. 結果をソート（売上高順）
        sorted_stores = sorted(store_sales.values(), key=lambda x: x['total_sales'], reverse=True)
        
        # 7. 全体サマリー計算
        total_sales = sum(store['total_sales'] for store in sorted_stores)
        total_orders = len(orders_response.data)
        total_stores = len(sorted_stores)
        
        # 8. パーセンテージ計算
        for store in sorted_stores:
            if total_sales > 0:
                store['percentage'] = (store['total_sales'] / total_sales) * 100
            else:
                store['percentage'] = 0
            
            # 平均注文額計算
            if store['order_count'] > 0:
                store['average_order_value'] = store['total_sales'] / store['order_count']
            else:
                store['average_order_value'] = 0
        
        return {
            "status": "success",
            "period": {
                "start_date": start_date,
                "end_date": end_date
            },
            "summary": {
                "total_sales": total_sales,
                "total_orders": total_orders,
                "total_stores": total_stores,
                "total_items": sum(store['total_items'] for store in sorted_stores)
            },
            "stores": sorted_stores,
            "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
        }

def generate_store_sales_html(data):
    """
    販売店舗別売上のHTML表示を生成
    """
    if data['status'] != 'success':
        return f"<h1>エラー</h1><p>{data.get('message', 'Unknown error')}</p>"
    
    period = data['period']
    summary = data['summary']
    stores = data['stores']
    
    html = f"""
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>販売店舗別売上ダッシュボード</title>
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                margin: 0;
                padding: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
            }}
            
            .container {{
                max-width: 1200px;
                margin: 0 auto;
            }}
            
            .header {{
                text-align: center;
                color: white;
                margin-bottom: 30px;
            }}
            
            .header h1 {{
                font-size: 2.5rem;
                margin-bottom: 10px;
            }}
            
            .period {{
                background: rgba(255, 255, 255, 0.1);
                padding: 15px;
                border-radius: 10px;
                color: white;
                text-align: center;
                margin-bottom: 20px;
            }}
            
            .summary-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }}
            
            .summary-card {{
                background: rgba(255, 255, 255, 0.95);
                padding: 20px;
                border-radius: 15px;
                text-align: center;
                box-shadow: 0 8px 32px rgba(31, 38, 135, 0.37);
            }}
            
            .summary-value {{
                font-size: 2rem;
                font-weight: bold;
                color: #2c3e50;
                margin-bottom: 5px;
            }}
            
            .summary-label {{
                color: #7f8c8d;
                font-size: 0.9rem;
            }}
            
            .stores-container {{
                background: rgba(255, 255, 255, 0.95);
                border-radius: 15px;
                padding: 25px;
                box-shadow: 0 8px 32px rgba(31, 38, 135, 0.37);
            }}
            
            .stores-title {{
                font-size: 1.5rem;
                margin-bottom: 20px;
                color: #2c3e50;
                text-align: center;
            }}
            
            .store-item {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 15px;
                margin-bottom: 10px;
                border-radius: 10px;
                background: #f8f9fa;
                border-left: 5px solid #3498db;
            }}
            
            .store-name {{
                font-weight: bold;
                font-size: 1.1rem;
                color: #2c3e50;
            }}
            
            .store-stats {{
                display: flex;
                gap: 20px;
                align-items: center;
            }}
            
            .store-amount {{
                font-size: 1.2rem;
                font-weight: bold;
                color: #27ae60;
            }}
            
            .store-percentage {{
                background: #3498db;
                color: white;
                padding: 4px 8px;
                border-radius: 15px;
                font-size: 0.9rem;
            }}
            
            .store-details {{
                color: #7f8c8d;
                font-size: 0.9rem;
            }}
            
            .refresh-btn {{
                position: fixed;
                bottom: 20px;
                right: 20px;
                background: #3498db;
                color: white;
                border: none;
                padding: 15px 20px;
                border-radius: 50px;
                cursor: pointer;
                font-size: 1rem;
                box-shadow: 0 4px 15px rgba(52, 152, 219, 0.4);
            }}
            
            .refresh-btn:hover {{
                background: #2980b9;
                transform: translateY(-2px);
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🏪 販売店舗別売上ダッシュボード</h1>
                <p>SIZUKA統合管理システム</p>
            </div>
            
            <div class="period">
                <h3>📅 集計期間: {period['start_date']} ～ {period['end_date']}</h3>
            </div>
            
            <div class="summary-grid">
                <div class="summary-card">
                    <div class="summary-value">¥{summary['total_sales']:,.0f}</div>
                    <div class="summary-label">総売上</div>
                </div>
                <div class="summary-card">
                    <div class="summary-value">{summary['total_orders']:,}</div>
                    <div class="summary-label">総注文数</div>
                </div>
                <div class="summary-card">
                    <div class="summary-value">{summary['total_stores']}</div>
                    <div class="summary-label">販売店舗数</div>
                </div>
                <div class="summary-card">
                    <div class="summary-value">{summary['total_items']:,}</div>
                    <div class="summary-label">総販売個数</div>
                </div>
            </div>
            
            <div class="stores-container">
                <h2 class="stores-title">🏬 店舗別売上詳細</h2>
    """
    
    for store in stores:
        html += f"""
                <div class="store-item">
                    <div>
                        <div class="store-name">{store['store_name']}</div>
                        <div class="store-details">
                            {store['order_count']}件の注文 • {store['total_items']:,}個販売 • 
                            平均注文額: ¥{store['average_order_value']:,.0f}
                        </div>
                    </div>
                    <div class="store-stats">
                        <div class="store-amount">¥{store['total_sales']:,.0f}</div>
                        <div class="store-percentage">{store['percentage']:.1f}%</div>
                    </div>
                </div>
        """
    
    html += """
            </div>
        </div>
        
        <button class="refresh-btn" onclick="location.reload()">🔄 更新</button>
        
        <script>
            // 5分ごとに自動更新
            setInterval(() => {
                location.reload();
            }, 5 * 60 * 1000);
        </script>
    </body>
    </html>
    """
    
    return html

if __name__ == "__main__":
    # テスト実行
    print("販売店舗別売上ダッシュボードのテスト実行")
    result = get_store_sales_summary()
    
    print("=== API結果 ===")
    print(f"ステータス: {result['status']}")
    if result['status'] == 'success':
        print(f"期間: {result['period']['start_date']} ～ {result['period']['end_date']}")
        print(f"総売上: ¥{result['summary']['total_sales']:,.0f}")
        print(f"店舗数: {result['summary']['total_stores']}")
        
        print("\n店舗別売上:")
        for store in result['stores']:
            print(f"  {store['store_name']}: ¥{store['total_sales']:,.0f} ({store['percentage']:.1f}%)")
    else:
        print(f"エラー: {result['message']}")