#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
楽天商品別売上API
期間選択可能な売上集計・分析機能
"""

from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import HTMLResponse
from datetime import datetime, date, timedelta
from typing import Optional
from supabase import create_client
import logging
from collections import defaultdict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Supabase接続情報
SUPABASE_URL = "https://equrcpeifogdrxoldkpe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ"

app = FastAPI(title="楽天売上分析API")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

@app.get("/api/sales/products")
async def get_product_sales(
    start_date: Optional[str] = Query(None, description="開始日 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="終了日 (YYYY-MM-DD)")
):
    """
    商品別売上一覧を取得
    期間指定可能（デフォルト：過去30日間）
    """
    try:
        # デフォルト期間設定
        if not end_date:
            end_date = date.today().strftime('%Y-%m-%d')
        if not start_date:
            start_date = (date.today() - timedelta(days=30)).strftime('%Y-%m-%d')
        
        # 注文データ取得
        query = supabase.table("order_items").select("*")
        query = query.gte("order_date", start_date)
        query = query.lte("order_date", end_date)
        
        response = query.execute()
        items = response.data if response.data else []
        
        # 商品別集計
        product_sales = defaultdict(lambda: {
            'product_name': '',
            'quantity': 0,
            'total_amount': 0,
            'orders_count': 0,
            'rakuten_sku': '',
            'common_code': ''
        })
        
        for item in items:
            key = item.get('product_code', 'unknown')
            
            # 商品情報更新
            if not product_sales[key]['product_name']:
                product_sales[key]['product_name'] = item.get('product_name', '不明')
                product_sales[key]['rakuten_sku'] = item.get('rakuten_item_number', '')
                
                # 共通コード取得（product_masterから）
                master_response = supabase.table("product_master").select("common_code").eq("rakuten_sku", key).limit(1).execute()
                if master_response.data:
                    product_sales[key]['common_code'] = master_response.data[0].get('common_code', '')
            
            # 数量・金額集計
            quantity = item.get('quantity', 0)
            price = item.get('price', 0)
            
            product_sales[key]['quantity'] += quantity
            product_sales[key]['total_amount'] += price * quantity
            product_sales[key]['orders_count'] += 1
        
        # リスト形式に変換（売上高順）
        sales_list = []
        for product_code, data in product_sales.items():
            sales_list.append({
                'product_code': product_code,
                'product_name': data['product_name'],
                'rakuten_sku': data['rakuten_sku'],
                'common_code': data['common_code'],
                'quantity': data['quantity'],
                'total_amount': data['total_amount'],
                'orders_count': data['orders_count'],
                'average_price': data['total_amount'] / data['quantity'] if data['quantity'] > 0 else 0
            })
        
        # 売上高順にソート
        sales_list.sort(key=lambda x: x['total_amount'], reverse=True)
        
        # サマリー情報
        total_sales = sum(item['total_amount'] for item in sales_list)
        total_quantity = sum(item['quantity'] for item in sales_list)
        total_orders = sum(item['orders_count'] for item in sales_list)
        
        return {
            'status': 'success',
            'period': {
                'start_date': start_date,
                'end_date': end_date
            },
            'summary': {
                'total_sales': total_sales,
                'total_quantity': total_quantity,
                'total_orders': total_orders,
                'unique_products': len(sales_list)
            },
            'products': sales_list[:100]  # 上位100商品
        }
        
    except Exception as e:
        logger.error(f"Error in get_product_sales: {str(e)}")
        return {
            'status': 'error',
            'message': str(e)
        }

@app.get("/api/sales/summary")
async def get_sales_summary(
    start_date: Optional[str] = Query(None, description="開始日 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="終了日 (YYYY-MM-DD)"),
    group_by: str = Query("day", description="集計単位 (day/week/month)")
):
    """
    期間別売上サマリー
    日別・週別・月別で集計可能
    """
    try:
        # デフォルト期間設定
        if not end_date:
            end_date = date.today().strftime('%Y-%m-%d')
        if not start_date:
            start_date = (date.today() - timedelta(days=30)).strftime('%Y-%m-%d')
        
        # 注文データ取得
        query = supabase.table("order_items").select("order_date, quantity, price")
        query = query.gte("order_date", start_date)
        query = query.lte("order_date", end_date)
        
        response = query.execute()
        items = response.data if response.data else []
        
        # 期間別集計
        period_sales = defaultdict(lambda: {
            'quantity': 0,
            'total_amount': 0,
            'orders_count': 0
        })
        
        for item in items:
            order_date = item.get('order_date', '')
            if not order_date:
                continue
                
            # 期間キー生成
            dt = datetime.strptime(order_date[:10], '%Y-%m-%d')
            if group_by == 'day':
                period_key = dt.strftime('%Y-%m-%d')
            elif group_by == 'week':
                # 週の開始日（月曜日）
                week_start = dt - timedelta(days=dt.weekday())
                period_key = week_start.strftime('%Y-%m-%d')
            else:  # month
                period_key = dt.strftime('%Y-%m')
            
            # 集計
            quantity = item.get('quantity', 0)
            price = item.get('price', 0)
            
            period_sales[period_key]['quantity'] += quantity
            period_sales[period_key]['total_amount'] += price * quantity
            period_sales[period_key]['orders_count'] += 1
        
        # リスト形式に変換（日付順）
        sales_timeline = []
        for period, data in sorted(period_sales.items()):
            sales_timeline.append({
                'period': period,
                'quantity': data['quantity'],
                'total_amount': data['total_amount'],
                'orders_count': data['orders_count']
            })
        
        # 全体サマリー
        total_sales = sum(item['total_amount'] for item in sales_timeline)
        total_quantity = sum(item['quantity'] for item in sales_timeline)
        total_orders = sum(item['orders_count'] for item in sales_timeline)
        
        return {
            'status': 'success',
            'period': {
                'start_date': start_date,
                'end_date': end_date,
                'group_by': group_by
            },
            'summary': {
                'total_sales': total_sales,
                'total_quantity': total_quantity,
                'total_orders': total_orders,
                'periods_count': len(sales_timeline)
            },
            'timeline': sales_timeline
        }
        
    except Exception as e:
        logger.error(f"Error in get_sales_summary: {str(e)}")
        return {
            'status': 'error',
            'message': str(e)
        }

@app.get("/api/sales/ranking")
async def get_sales_ranking(
    start_date: Optional[str] = Query(None, description="開始日 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="終了日 (YYYY-MM-DD)"),
    limit: int = Query(20, description="表示件数")
):
    """
    売上ランキング
    売上高・数量・注文数でランキング表示
    """
    try:
        # 商品別売上データ取得
        product_sales = await get_product_sales(start_date, end_date)
        
        if product_sales['status'] != 'success':
            return product_sales
        
        products = product_sales['products'][:limit]
        
        # ランキング情報追加
        rankings = {
            'by_amount': sorted(products, key=lambda x: x['total_amount'], reverse=True),
            'by_quantity': sorted(products, key=lambda x: x['quantity'], reverse=True),
            'by_orders': sorted(products, key=lambda x: x['orders_count'], reverse=True)
        }
        
        return {
            'status': 'success',
            'period': product_sales['period'],
            'rankings': rankings
        }
        
    except Exception as e:
        logger.error(f"Error in get_sales_ranking: {str(e)}")
        return {
            'status': 'error',
            'message': str(e)
        }

@app.get("/", response_class=HTMLResponse)
async def sales_dashboard():
    """
    売上ダッシュボードUI（在庫管理と同じスタイル）
    """
    html_content = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>楽天売上分析ダッシュボード</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Hiragino Sans', sans-serif;
            background-color: #f5f5f5;
            color: #333;
            line-height: 1.6;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }
        
        .header {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        
        .header h1 {
            font-size: 24px;
            color: #2c3e50;
            margin-bottom: 10px;
        }
        
        .filters {
            display: flex;
            gap: 15px;
            flex-wrap: wrap;
            align-items: center;
        }
        
        .filter-group {
            display: flex;
            flex-direction: column;
            gap: 5px;
        }
        
        .filter-group label {
            font-size: 12px;
            color: #666;
            font-weight: 500;
        }
        
        .filter-group input,
        .filter-group select {
            padding: 8px 12px;
            border: 1px solid #ddd;
            border-radius: 5px;
            font-size: 14px;
        }
        
        .btn {
            padding: 8px 20px;
            background: #3498db;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
            transition: background 0.3s;
        }
        
        .btn:hover {
            background: #2980b9;
        }
        
        .dashboard-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        
        .card {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .card h2 {
            font-size: 16px;
            color: #2c3e50;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 2px solid #e9ecef;
        }
        
        .stat-value {
            font-size: 32px;
            font-weight: bold;
            color: #3498db;
            margin-bottom: 5px;
        }
        
        .stat-label {
            font-size: 14px;
            color: #666;
        }
        
        .table-container {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            overflow-x: auto;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
        }
        
        th, td {
            text-align: left;
            padding: 12px;
            border-bottom: 1px solid #e9ecef;
        }
        
        th {
            background: #f8f9fa;
            font-weight: 600;
            color: #2c3e50;
            position: sticky;
            top: 0;
        }
        
        tr:hover {
            background: #f8f9fa;
        }
        
        .number {
            text-align: right;
            font-family: 'SF Mono', Monaco, monospace;
        }
        
        .loading {
            text-align: center;
            padding: 40px;
            color: #666;
        }
        
        .error {
            background: #fee;
            color: #c33;
            padding: 10px;
            border-radius: 5px;
            margin: 10px 0;
        }
        
        .tabs {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
            border-bottom: 2px solid #e9ecef;
        }
        
        .tab {
            padding: 10px 20px;
            background: none;
            border: none;
            cursor: pointer;
            font-size: 14px;
            color: #666;
            transition: all 0.3s;
        }
        
        .tab.active {
            color: #3498db;
            border-bottom: 2px solid #3498db;
        }
        
        .chart-container {
            height: 300px;
            position: relative;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>楽天売上分析ダッシュボード</h1>
            <div class="filters">
                <div class="filter-group">
                    <label>開始日</label>
                    <input type="date" id="startDate" value="">
                </div>
                <div class="filter-group">
                    <label>終了日</label>
                    <input type="date" id="endDate" value="">
                </div>
                <div class="filter-group">
                    <label>集計単位</label>
                    <select id="groupBy">
                        <option value="day">日別</option>
                        <option value="week">週別</option>
                        <option value="month">月別</option>
                    </select>
                </div>
                <button class="btn" onclick="loadData()">更新</button>
            </div>
        </div>

        <div class="dashboard-grid">
            <div class="card">
                <h2>売上高</h2>
                <div class="stat-value" id="totalSales">-</div>
                <div class="stat-label">円</div>
            </div>
            <div class="card">
                <h2>販売数量</h2>
                <div class="stat-value" id="totalQuantity">-</div>
                <div class="stat-label">個</div>
            </div>
            <div class="card">
                <h2>注文数</h2>
                <div class="stat-value" id="totalOrders">-</div>
                <div class="stat-label">件</div>
            </div>
            <div class="card">
                <h2>商品数</h2>
                <div class="stat-value" id="uniqueProducts">-</div>
                <div class="stat-label">種類</div>
            </div>
        </div>

        <div class="tabs">
            <button class="tab active" onclick="showTab('products')">商品別売上</button>
            <button class="tab" onclick="showTab('timeline')">期間別推移</button>
            <button class="tab" onclick="showTab('ranking')">ランキング</button>
        </div>

        <div id="productsTab" class="table-container">
            <h2>商品別売上一覧</h2>
            <table id="productsTable">
                <thead>
                    <tr>
                        <th>商品コード</th>
                        <th>商品名</th>
                        <th>共通コード</th>
                        <th class="number">販売数量</th>
                        <th class="number">売上高</th>
                        <th class="number">注文数</th>
                        <th class="number">平均単価</th>
                    </tr>
                </thead>
                <tbody id="productsBody">
                    <tr><td colspan="7" class="loading">データを読み込んでいます...</td></tr>
                </tbody>
            </table>
        </div>

        <div id="timelineTab" class="table-container" style="display:none;">
            <h2>期間別売上推移</h2>
            <div class="chart-container" id="timelineChart"></div>
            <table id="timelineTable">
                <thead>
                    <tr>
                        <th>期間</th>
                        <th class="number">売上高</th>
                        <th class="number">販売数量</th>
                        <th class="number">注文数</th>
                    </tr>
                </thead>
                <tbody id="timelineBody">
                    <tr><td colspan="4" class="loading">データを読み込んでいます...</td></tr>
                </tbody>
            </table>
        </div>

        <div id="rankingTab" class="table-container" style="display:none;">
            <h2>売上ランキング TOP20</h2>
            <div class="ranking-grid">
                <div class="ranking-section">
                    <h3>売上高ランキング</h3>
                    <table id="amountRanking">
                        <thead>
                            <tr>
                                <th>順位</th>
                                <th>商品名</th>
                                <th class="number">売上高</th>
                            </tr>
                        </thead>
                        <tbody id="amountBody"></tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>

    <script>
        // 初期設定
        document.addEventListener('DOMContentLoaded', function() {
            const today = new Date();
            const thirtyDaysAgo = new Date(today);
            thirtyDaysAgo.setDate(today.getDate() - 30);
            
            document.getElementById('endDate').value = today.toISOString().split('T')[0];
            document.getElementById('startDate').value = thirtyDaysAgo.toISOString().split('T')[0];
            
            loadData();
        });

        async function loadData() {
            const startDate = document.getElementById('startDate').value;
            const endDate = document.getElementById('endDate').value;
            const groupBy = document.getElementById('groupBy').value;
            
            // 商品別売上取得
            try {
                const response = await fetch(`/api/sales/products?start_date=${startDate}&end_date=${endDate}`);
                const data = await response.json();
                
                if (data.status === 'success') {
                    updateSummary(data.summary);
                    updateProductsTable(data.products);
                }
            } catch (error) {
                console.error('Error loading products:', error);
            }
            
            // 期間別売上取得
            try {
                const response = await fetch(`/api/sales/summary?start_date=${startDate}&end_date=${endDate}&group_by=${groupBy}`);
                const data = await response.json();
                
                if (data.status === 'success') {
                    updateTimelineTable(data.timeline);
                }
            } catch (error) {
                console.error('Error loading timeline:', error);
            }
            
            // ランキング取得
            try {
                const response = await fetch(`/api/sales/ranking?start_date=${startDate}&end_date=${endDate}&limit=20`);
                const data = await response.json();
                
                if (data.status === 'success') {
                    updateRankings(data.rankings);
                }
            } catch (error) {
                console.error('Error loading rankings:', error);
            }
        }

        function updateSummary(summary) {
            document.getElementById('totalSales').textContent = summary.total_sales.toLocaleString();
            document.getElementById('totalQuantity').textContent = summary.total_quantity.toLocaleString();
            document.getElementById('totalOrders').textContent = summary.total_orders.toLocaleString();
            document.getElementById('uniqueProducts').textContent = summary.unique_products.toLocaleString();
        }

        function updateProductsTable(products) {
            const tbody = document.getElementById('productsBody');
            tbody.innerHTML = products.map(product => `
                <tr>
                    <td>${product.product_code}</td>
                    <td>${product.product_name}</td>
                    <td>${product.common_code || '-'}</td>
                    <td class="number">${product.quantity.toLocaleString()}</td>
                    <td class="number">¥${product.total_amount.toLocaleString()}</td>
                    <td class="number">${product.orders_count.toLocaleString()}</td>
                    <td class="number">¥${Math.round(product.average_price).toLocaleString()}</td>
                </tr>
            `).join('');
        }

        function updateTimelineTable(timeline) {
            const tbody = document.getElementById('timelineBody');
            tbody.innerHTML = timeline.map(period => `
                <tr>
                    <td>${period.period}</td>
                    <td class="number">¥${period.total_amount.toLocaleString()}</td>
                    <td class="number">${period.quantity.toLocaleString()}</td>
                    <td class="number">${period.orders_count.toLocaleString()}</td>
                </tr>
            `).join('');
        }

        function updateRankings(rankings) {
            const amountBody = document.getElementById('amountBody');
            amountBody.innerHTML = rankings.by_amount.slice(0, 20).map((product, index) => `
                <tr>
                    <td>${index + 1}</td>
                    <td>${product.product_name}</td>
                    <td class="number">¥${product.total_amount.toLocaleString()}</td>
                </tr>
            `).join('');
        }

        function showTab(tabName) {
            // タブ切り替え
            document.querySelectorAll('.tab').forEach(tab => {
                tab.classList.remove('active');
            });
            event.target.classList.add('active');
            
            // コンテンツ切り替え
            document.getElementById('productsTab').style.display = tabName === 'products' ? 'block' : 'none';
            document.getElementById('timelineTab').style.display = tabName === 'timeline' ? 'block' : 'none';
            document.getElementById('rankingTab').style.display = tabName === 'ranking' ? 'block' : 'none';
        }
    </script>
</body>
</html>
    """
    return html_content

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)