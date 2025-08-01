from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from datetime import datetime, timedelta
import pytz
import os
from supabase import create_client, Client
from typing import Optional, List, Dict

app = FastAPI()

# Supabase接続
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if SUPABASE_URL and SUPABASE_KEY:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
else:
    supabase = None

@app.get("/api/sales_summary")
async def sales_summary(
    start_date: Optional[str] = Query(None, description="開始日 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="終了日 (YYYY-MM-DD)"),
    group_by: Optional[str] = Query("platform", description="集計単位 (platform/product/date)")
):
    """売上サマリー分析"""
    try:
        if not supabase:
            return {"error": "Database connection not configured"}

        # デフォルト期間（過去30日）
        if not end_date:
            end_date = datetime.now(pytz.timezone('Asia/Tokyo')).date().isoformat()
        if not start_date:
            start_date = (datetime.now(pytz.timezone('Asia/Tokyo')).date() - timedelta(days=30)).isoformat()

        results = {
            "period": {"start_date": start_date, "end_date": end_date},
            "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat(),
            "summary": {}
        }

        if group_by == "platform":
            platform_summary = await get_platform_summary(start_date, end_date)
            results["summary"] = platform_summary
        elif group_by == "product":
            product_summary = await get_product_summary(start_date, end_date)
            results["summary"] = product_summary
        elif group_by == "date":
            daily_summary = await get_daily_summary(start_date, end_date)
            results["summary"] = daily_summary

        return results

    except Exception as e:
        return JSONResponse(
            status_code=200,
            content={
                "status": "error",
                "message": str(e),
                "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
            }
        )

async def get_platform_summary(start_date: str, end_date: str):
    """プラットフォーム別売上サマリー"""
    try:
        # 全売上データを取得
        sales_data = supabase.table('sales_master').select('platform_name, quantity, total_amount, common_code').gte('sale_date', start_date).lte('sale_date', end_date).execute()

        platform_stats = {}
        
        if sales_data.data:
            for sale in sales_data.data:
                platform = sale['platform_name']
                amount = float(sale.get('total_amount', 0))
                quantity = int(sale.get('quantity', 0))
                common_code = sale.get('common_code', '')
                
                if platform not in platform_stats:
                    platform_stats[platform] = {
                        "platform_name": platform,
                        "total_amount": 0,
                        "total_quantity": 0,
                        "order_count": 0,
                        "mapped_products": 0,
                        "unmapped_products": 0,
                        "product_variety": set()
                    }
                
                platform_stats[platform]["total_amount"] += amount
                platform_stats[platform]["total_quantity"] += quantity
                platform_stats[platform]["order_count"] += 1
                platform_stats[platform]["product_variety"].add(common_code)
                
                if common_code.startswith('UNMAPPED_'):
                    platform_stats[platform]["unmapped_products"] += 1
                else:
                    platform_stats[platform]["mapped_products"] += 1

        # setを数値に変換
        for platform in platform_stats.values():
            platform["unique_products"] = len(platform["product_variety"])
            del platform["product_variety"]

        return {
            "type": "platform_summary",
            "platforms": list(platform_stats.values()),
            "total_platforms": len(platform_stats)
        }

    except Exception as e:
        return {"error": f"プラットフォーム別集計エラー: {str(e)}"}

async def get_product_summary(start_date: str, end_date: str):
    """商品別売上サマリー（マッピング済みのみ詳細表示）"""
    try:
        # マッピング済み商品の売上
        mapped_sales = supabase.table('sales_master').select('common_code, platform_name, quantity, total_amount').gte('sale_date', start_date).lte('sale_date', end_date).not_.like('common_code', 'UNMAPPED_%').execute()
        
        # 未マッピング商品の売上
        unmapped_sales = supabase.table('sales_master').select('common_code, platform_name, quantity, total_amount').gte('sale_date', start_date).lte('sale_date', end_date).like('common_code', 'UNMAPPED_%').execute()

        product_stats = {}
        unmapped_total = {"total_amount": 0, "total_quantity": 0, "count": 0}

        # マッピング済み商品の集計
        if mapped_sales.data:
            for sale in mapped_sales.data:
                common_code = sale['common_code']
                amount = float(sale.get('total_amount', 0))
                quantity = int(sale.get('quantity', 0))
                platform = sale['platform_name']

                if common_code not in product_stats:
                    # 商品名を取得
                    product_name = await get_product_name_from_master(common_code)
                    product_stats[common_code] = {
                        "common_code": common_code,
                        "product_name": product_name,
                        "total_amount": 0,
                        "total_quantity": 0,
                        "platforms": {}
                    }

                product_stats[common_code]["total_amount"] += amount
                product_stats[common_code]["total_quantity"] += quantity
                
                if platform not in product_stats[common_code]["platforms"]:
                    product_stats[common_code]["platforms"][platform] = {"amount": 0, "quantity": 0}
                
                product_stats[common_code]["platforms"][platform]["amount"] += amount
                product_stats[common_code]["platforms"][platform]["quantity"] += quantity

        # 未マッピング商品の集計
        if unmapped_sales.data:
            for sale in unmapped_sales.data:
                unmapped_total["total_amount"] += float(sale.get('total_amount', 0))
                unmapped_total["total_quantity"] += int(sale.get('quantity', 0))
                unmapped_total["count"] += 1

        # 売上順でソート
        sorted_products = sorted(product_stats.values(), key=lambda x: x["total_amount"], reverse=True)

        return {
            "type": "product_summary",
            "mapped_products": sorted_products,
            "unmapped_summary": unmapped_total,
            "total_mapped_products": len(sorted_products)
        }

    except Exception as e:
        return {"error": f"商品別集計エラー: {str(e)}"}

async def get_daily_summary(start_date: str, end_date: str):
    """日別売上サマリー"""
    try:
        sales_data = supabase.table('sales_master').select('sale_date, platform_name, total_amount, quantity').gte('sale_date', start_date).lte('sale_date', end_date).execute()

        daily_stats = {}
        
        if sales_data.data:
            for sale in sales_data.data:
                sale_date = sale['sale_date']
                platform = sale['platform_name']
                amount = float(sale.get('total_amount', 0))
                quantity = int(sale.get('quantity', 0))

                if sale_date not in daily_stats:
                    daily_stats[sale_date] = {
                        "date": sale_date,
                        "total_amount": 0,
                        "total_quantity": 0,
                        "platforms": {}
                    }

                daily_stats[sale_date]["total_amount"] += amount
                daily_stats[sale_date]["total_quantity"] += quantity
                
                if platform not in daily_stats[sale_date]["platforms"]:
                    daily_stats[sale_date]["platforms"][platform] = {"amount": 0, "quantity": 0}
                
                daily_stats[sale_date]["platforms"][platform]["amount"] += amount
                daily_stats[sale_date]["platforms"][platform]["quantity"] += quantity

        # 日付順でソート
        sorted_daily = sorted(daily_stats.values(), key=lambda x: x["date"])

        return {
            "type": "daily_summary",
            "daily_data": sorted_daily,
            "total_days": len(sorted_daily)
        }

    except Exception as e:
        return {"error": f"日別集計エラー: {str(e)}"}

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

@app.get("/api/platform_comparison")
async def platform_comparison(
    start_date: Optional[str] = Query(None, description="開始日 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="終了日 (YYYY-MM-DD)")
):
    """プラットフォーム比較分析"""
    try:
        if not supabase:
            return {"error": "Database connection not configured"}

        # デフォルト期間（過去30日）
        if not end_date:
            end_date = datetime.now(pytz.timezone('Asia/Tokyo')).date().isoformat()
        if not start_date:
            start_date = (datetime.now(pytz.timezone('Asia/Tokyo')).date() - timedelta(days=30)).isoformat()

        platform_summary = await get_platform_summary(start_date, end_date)
        
        # 比較メトリクスを追加
        if platform_summary.get("platforms"):
            platforms = platform_summary["platforms"]
            total_amount = sum(p["total_amount"] for p in platforms)
            total_quantity = sum(p["total_quantity"] for p in platforms)
            
            for platform in platforms:
                if total_amount > 0:
                    platform["amount_share"] = round((platform["total_amount"] / total_amount) * 100, 2)
                if total_quantity > 0:
                    platform["quantity_share"] = round((platform["total_quantity"] / total_quantity) * 100, 2)
                if platform["order_count"] > 0:
                    platform["avg_order_value"] = round(platform["total_amount"] / platform["order_count"], 2)

        return {
            "period": {"start_date": start_date, "end_date": end_date},
            "comparison": platform_summary,
            "totals": {
                "total_amount": sum(p["total_amount"] for p in platform_summary.get("platforms", [])),
                "total_quantity": sum(p["total_quantity"] for p in platform_summary.get("platforms", [])),
                "total_orders": sum(p["order_count"] for p in platform_summary.get("platforms", []))
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

@app.get("/api/bestseller_analysis")
async def bestseller_analysis(
    start_date: Optional[str] = Query(None, description="開始日 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="終了日 (YYYY-MM-DD)"),
    limit: Optional[int] = Query(10, description="上位何件まで表示")
):
    """売れ筋商品分析（マッピング済み商品のみ）"""
    try:
        if not supabase:
            return {"error": "Database connection not configured"}

        # デフォルト期間（過去30日）
        if not end_date:
            end_date = datetime.now(pytz.timezone('Asia/Tokyo')).date().isoformat()
        if not start_date:
            start_date = (datetime.now(pytz.timezone('Asia/Tokyo')).date() - timedelta(days=30)).isoformat()

        product_summary = await get_product_summary(start_date, end_date)
        
        if product_summary.get("mapped_products"):
            top_by_amount = product_summary["mapped_products"][:limit]
            top_by_quantity = sorted(product_summary["mapped_products"], key=lambda x: x["total_quantity"], reverse=True)[:limit]
        else:
            top_by_amount = []
            top_by_quantity = []

        return {
            "period": {"start_date": start_date, "end_date": end_date},
            "bestsellers": {
                "by_amount": top_by_amount,
                "by_quantity": top_by_quantity
            },
            "unmapped_summary": product_summary.get("unmapped_summary", {}),
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