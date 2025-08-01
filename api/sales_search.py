from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from datetime import datetime, timedelta
import pytz
import os
from supabase import create_client, Client
from typing import Optional

app = FastAPI()

# Supabase接続
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if SUPABASE_URL and SUPABASE_KEY:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
else:
    supabase = None

@app.get("/api/sales_search")
async def search_sales(
    start_date: Optional[str] = Query(None, description="開始日 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="終了日 (YYYY-MM-DD)"),
    days: Optional[int] = Query(7, description="過去n日間の売上"),
    product_search: Optional[str] = Query(None, description="商品名または商品コードで検索"),
    sort_by: Optional[str] = Query("date", description="並び順: date, sales, units"),
    sort_desc: Optional[bool] = Query(True, description="降順ソート"),
    limit: Optional[int] = Query(50, description="取得件数")
):
    """売上検索・分析API"""
    try:
        if not supabase:
            return {"error": "Database connection not configured", "items": []}
        
        # 日付範囲の設定
        if not start_date and not end_date:
            # デフォルト: 過去n日間
            end = datetime.now(pytz.timezone('Asia/Tokyo')).date()
            start = end - timedelta(days=days)
            start_date = start.isoformat()
            end_date = end.isoformat()
        elif start_date and not end_date:
            end_date = datetime.now(pytz.timezone('Asia/Tokyo')).date().isoformat()
        elif not start_date and end_date:
            start_date = (datetime.strptime(end_date, '%Y-%m-%d').date() - timedelta(days=days)).isoformat()
        
        # sales_dailyテーブルから売上データを取得
        query = supabase.table('sales_daily').select('''
            *,
            platform:platform_id(platform_name, platform_code)
        ''')
        
        # 日付フィルター
        if start_date:
            query = query.gte('summary_date', start_date)
        if end_date:
            query = query.lte('summary_date', end_date)
        
        # 商品検索（修正版）
        if product_search:
            query = query.ilike('product_name', f'%{product_search}%')
        
        # ソート
        if sort_by == "sales":
            query = query.order('net_sales', desc=sort_desc)
        elif sort_by == "units":
            query = query.order('units_sold', desc=sort_desc)
        else:  # date
            query = query.order('summary_date', desc=sort_desc)
        
        # 件数制限
        query = query.limit(limit)
        
        response = query.execute()
        
        # 売上サマリーを計算
        total_sales = 0
        total_units = 0
        product_summary = {}
        daily_summary = {}
        
        if response.data:
            for item in response.data:
                sales = item.get('net_sales', 0) or 0
                units = item.get('units_sold', 0) or 0
                date = item.get('summary_date', '')
                product_code = item.get('product_code', '')
                product_name = item.get('product_name', '')
                
                total_sales += sales
                total_units += units
                
                # 商品別サマリー
                if product_code not in product_summary:
                    product_summary[product_code] = {
                        "product_code": product_code,
                        "product_name": product_name,
                        "total_sales": 0,
                        "total_units": 0
                    }
                product_summary[product_code]["total_sales"] += sales
                product_summary[product_code]["total_units"] += units
                
                # 日別サマリー
                if date not in daily_summary:
                    daily_summary[date] = {
                        "date": date,
                        "total_sales": 0,
                        "total_units": 0,
                        "product_count": 0
                    }
                daily_summary[date]["total_sales"] += sales
                daily_summary[date]["total_units"] += units
                daily_summary[date]["product_count"] += 1
        
        # トップ商品（売上順）
        top_products = sorted(product_summary.values(), key=lambda x: x['total_sales'], reverse=True)[:10]
        
        # 日別売上（日付順）
        daily_sales = sorted(daily_summary.values(), key=lambda x: x['date'])
        
        return {
            "status": "success",
            "search_params": {
                "start_date": start_date,
                "end_date": end_date,
                "product_search": product_search,
                "sort_by": sort_by,
                "sort_desc": sort_desc,
                "limit": limit
            },
            "summary": {
                "total_sales": total_sales,
                "total_units": total_units,
                "period_days": (datetime.strptime(end_date, '%Y-%m-%d') - datetime.strptime(start_date, '%Y-%m-%d')).days + 1,
                "avg_daily_sales": total_sales / ((datetime.strptime(end_date, '%Y-%m-%d') - datetime.strptime(start_date, '%Y-%m-%d')).days + 1) if start_date and end_date else 0
            },
            "count": len(response.data) if response.data else 0,
            "items": response.data if response.data else [],
            "top_products": top_products,
            "daily_sales": daily_sales,
            "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
        }
        
    except Exception as e:
        return JSONResponse(
            status_code=200,
            content={
                "status": "error",
                "message": str(e),
                "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
            }
        )