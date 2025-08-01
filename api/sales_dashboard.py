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

@app.get("/api/sales_dashboard")
async def sales_dashboard(
    start_date: Optional[str] = Query(None, description="開始日 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="終了日 (YYYY-MM-DD)"),
    page: Optional[int] = Query(1, description="ページ番号"),
    per_page: Optional[int] = Query(50, description="1ページあたりの件数"),
    sort_by: Optional[str] = Query("total_amount", description="ソート項目 (total_amount/total_quantity/sale_date)"),
    sort_order: Optional[str] = Query("desc", description="ソート順序 (asc/desc)"),
    platform_filter: Optional[str] = Query(None, description="プラットフォームフィルター"),
    mapping_filter: Optional[str] = Query(None, description="マッピングフィルター (mapped/unmapped/all)")
):
    """売上ダッシュボード - 在庫画面と同じUI構造"""
    try:
        if not supabase:
            return {"error": "Database connection not configured"}
        
        # デフォルト期間（過去30日）
        if not end_date:
            end_date = datetime.now(pytz.timezone('Asia/Tokyo')).date().isoformat()
        if not start_date:
            start_date = (datetime.now(pytz.timezone('Asia/Tokyo')).date() - timedelta(days=30)).isoformat()
        
        # 基本クエリ（売上データを取得）
        query = supabase.table('sales_master').select('*').gte('sale_date', start_date).lte('sale_date', end_date)
        
        # プラットフォームフィルター
        if platform_filter:
            query = query.eq('platform_name', platform_filter)
        
        # マッピングフィルター
        if mapping_filter == 'mapped':
            query = query.not_.like('common_code', 'UNMAPPED_%')
        elif mapping_filter == 'unmapped':
            query = query.like('common_code', 'UNMAPPED_%')
        
        # 全件取得
        all_response = query.execute()
        all_sales = all_response.data if all_response.data else []
        
        # 合計・統計情報を計算（一番上に表示）
        summary = await calculate_sales_summary(all_sales, start_date, end_date)
        
        # 商品別に集約してソート
        product_sales = await aggregate_by_product(all_sales)
        
        # ソート処理
        if sort_by == "total_amount":
            product_sales.sort(key=lambda x: x["total_amount"], reverse=(sort_order == "desc"))
        elif sort_by == "total_quantity":
            product_sales.sort(key=lambda x: x["total_quantity"], reverse=(sort_order == "desc"))
        elif sort_by == "sale_date":
            product_sales.sort(key=lambda x: x.get("latest_sale_date", ""), reverse=(sort_order == "desc"))
        
        # ページネーション
        total_items = len(product_sales)
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        page_items = product_sales[start_idx:end_idx]
        
        # プラットフォーム一覧を取得（フィルター用）
        platforms = list(set(item.get('platform_name') for item in all_sales if item.get('platform_name')))
        
        return {
            "status": "success",
            "period": {
                "start_date": start_date,
                "end_date": end_date,
                "days_count": (datetime.fromisoformat(end_date) - datetime.fromisoformat(start_date)).days + 1
            },
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total_items": total_items,
                "total_pages": (total_items + per_page - 1) // per_page
            },
            "summary": summary,  # 一番上に表示する合計情報
            "items": page_items,  # 商品別売上一覧
            "filters": {
                "platforms": platforms,
                "mapping_status": ["all", "mapped", "unmapped"]
            },
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

async def calculate_sales_summary(all_sales, start_date, end_date):
    """売上サマリー計算（画面上部に表示）"""
    try:
        total_amount = 0
        total_quantity = 0
        total_orders = len(set(item.get('platform_order_id') for item in all_sales if item.get('platform_order_id')))
        
        platform_breakdown = {}
        mapped_amount = 0
        unmapped_amount = 0
        unique_products = set()
        
        for sale in all_sales:
            amount = float(sale.get('total_amount', 0))
            quantity = int(sale.get('quantity', 0))
            platform = sale.get('platform_name', 'unknown')
            common_code = sale.get('common_code', 'unknown')
            
            total_amount += amount
            total_quantity += quantity
            unique_products.add(common_code)
            
            # プラットフォーム別集計
            if platform not in platform_breakdown:
                platform_breakdown[platform] = {"amount": 0, "quantity": 0, "orders": set()}
            
            platform_breakdown[platform]["amount"] += amount
            platform_breakdown[platform]["quantity"] += quantity
            platform_breakdown[platform]["orders"].add(sale.get('platform_order_id'))
            
            # マッピング状況別集計
            if common_code.startswith('UNMAPPED_'):
                unmapped_amount += amount
            else:
                mapped_amount += amount
        
        # プラットフォーム別の注文数を計算
        for platform in platform_breakdown:
            platform_breakdown[platform]["order_count"] = len(platform_breakdown[platform]["orders"])
            del platform_breakdown[platform]["orders"]  # setは削除
        
        return {
            "period_summary": {
                "total_amount": round(total_amount, 2),
                "total_quantity": total_quantity,
                "total_orders": total_orders,
                "unique_products": len(unique_products),
                "average_order_value": round(total_amount / total_orders, 2) if total_orders > 0 else 0,
                "average_product_price": round(total_amount / total_quantity, 2) if total_quantity > 0 else 0
            },
            "platform_breakdown": [
                {
                    "platform_name": platform,
                    "total_amount": round(data["amount"], 2),
                    "total_quantity": data["quantity"],
                    "order_count": data["order_count"],
                    "share_percentage": round((data["amount"] / total_amount) * 100, 1) if total_amount > 0 else 0
                }
                for platform, data in platform_breakdown.items()
            ],
            "mapping_status": {
                "mapped_amount": round(mapped_amount, 2),
                "unmapped_amount": round(unmapped_amount, 2),
                "mapped_percentage": round((mapped_amount / total_amount) * 100, 1) if total_amount > 0 else 0,
                "unmapped_percentage": round((unmapped_amount / total_amount) * 100, 1) if total_amount > 0 else 0
            }
        }
        
    except Exception as e:
        return {
            "error": f"サマリー計算エラー: {str(e)}"
        }

async def aggregate_by_product(all_sales):
    """商品別に売上を集約"""
    try:
        product_aggregation = {}
        
        for sale in all_sales:
            common_code = sale.get('common_code', 'unknown')
            
            if common_code not in product_aggregation:
                # 商品名を取得
                if common_code.startswith('UNMAPPED_'):
                    product_name = f"未マッピング商品 ({common_code.replace('UNMAPPED_', '')})"
                else:
                    product_name = await get_product_name_from_master(common_code)
                
                product_aggregation[common_code] = {
                    "common_code": common_code,
                    "product_name": product_name,
                    "total_amount": 0,
                    "total_quantity": 0,
                    "order_count": 0,
                    "platforms": {},
                    "is_mapped": not common_code.startswith('UNMAPPED_'),
                    "latest_sale_date": "",
                    "first_sale_date": ""
                }
            
            product = product_aggregation[common_code]
            amount = float(sale.get('total_amount', 0))
            quantity = int(sale.get('quantity', 0))
            platform = sale.get('platform_name', 'unknown')
            sale_date = sale.get('sale_date', '')
            
            # 商品別合計
            product["total_amount"] += amount
            product["total_quantity"] += quantity
            product["order_count"] += 1
            
            # プラットフォーム別内訳
            if platform not in product["platforms"]:
                product["platforms"][platform] = {"amount": 0, "quantity": 0}
            product["platforms"][platform]["amount"] += amount
            product["platforms"][platform]["quantity"] += quantity
            
            # 売上日付の更新
            if not product["latest_sale_date"] or sale_date > product["latest_sale_date"]:
                product["latest_sale_date"] = sale_date
            if not product["first_sale_date"] or sale_date < product["first_sale_date"]:
                product["first_sale_date"] = sale_date
        
        # 小数点を丸める
        for product in product_aggregation.values():
            product["total_amount"] = round(product["total_amount"], 2)
            product["average_unit_price"] = round(product["total_amount"] / product["total_quantity"], 2) if product["total_quantity"] > 0 else 0
            
            for platform_data in product["platforms"].values():
                platform_data["amount"] = round(platform_data["amount"], 2)
        
        return list(product_aggregation.values())
        
    except Exception as e:
        print(f"商品別集約エラー: {str(e)}")
        return []

async def get_product_name_from_master(common_code: str) -> str:
    """商品マスターから商品名を取得"""
    try:
        result = supabase.table('product_mapping_master').select('product_name').eq('common_code', common_code).execute()
        if result.data:
            return result.data[0]['product_name']
        else:
            return f"商品名不明 ({common_code})"
    except:
        return f"商品名不明 ({common_code})"

@app.get("/api/sales_daily_trend")
async def sales_daily_trend(
    start_date: Optional[str] = Query(None, description="開始日 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="終了日 (YYYY-MM-DD)"),
    platform_filter: Optional[str] = Query(None, description="プラットフォームフィルター")
):
    """日別売上推移（グラフ用データ）"""
    try:
        if not supabase:
            return {"error": "Database connection not configured"}
        
        # デフォルト期間（過去30日）
        if not end_date:
            end_date = datetime.now(pytz.timezone('Asia/Tokyo')).date().isoformat()
        if not start_date:
            start_date = (datetime.now(pytz.timezone('Asia/Tokyo')).date() - timedelta(days=30)).isoformat()
        
        # 売上データを取得
        query = supabase.table('sales_master').select('sale_date, platform_name, total_amount, quantity').gte('sale_date', start_date).lte('sale_date', end_date)
        
        if platform_filter:
            query = query.eq('platform_name', platform_filter)
        
        response = query.execute()
        all_sales = response.data if response.data else []
        
        # 日別に集約
        daily_data = {}
        for sale in all_sales:
            sale_date = sale.get('sale_date')
            amount = float(sale.get('total_amount', 0))
            quantity = int(sale.get('quantity', 0))
            
            if sale_date not in daily_data:
                daily_data[sale_date] = {
                    "date": sale_date,
                    "total_amount": 0,
                    "total_quantity": 0,
                    "order_count": 0
                }
            
            daily_data[sale_date]["total_amount"] += amount
            daily_data[sale_date]["total_quantity"] += quantity
            daily_data[sale_date]["order_count"] += 1
        
        # 日付順でソート
        sorted_daily = sorted(daily_data.values(), key=lambda x: x["date"])
        
        # 小数点を丸める
        for day in sorted_daily:
            day["total_amount"] = round(day["total_amount"], 2)
        
        return {
            "period": {"start_date": start_date, "end_date": end_date},
            "platform_filter": platform_filter,
            "daily_trend": sorted_daily,
            "total_days": len(sorted_daily),
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