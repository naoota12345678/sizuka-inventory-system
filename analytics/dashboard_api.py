#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
統合分析ダッシュボード API
売上・在庫・利益分析のエンドポイント
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel

from core.database import supabase

router = APIRouter(prefix="/analytics", tags=["analytics"])

class DateRange(BaseModel):
    start_date: str
    end_date: str

class SalesAnalytics(BaseModel):
    total_sales: float
    total_transactions: int
    avg_order_value: float
    top_products: List[Dict]
    platform_breakdown: List[Dict]

@router.get("/sales-summary")
async def get_sales_summary(
    start_date: str = Query(..., description="開始日 (YYYY-MM-DD)"),
    end_date: str = Query(..., description="終了日 (YYYY-MM-DD)"),
    platform: Optional[str] = Query(None, description="特定プラットフォーム")
):
    """売上サマリーを取得"""
    try:
        # 基本的な売上集計クエリ
        query = supabase.table('sales_transactions').select(
            '''
            *,
            platform:platform_id(name, platform_code),
            product:common_code(product_name, product_type)
            '''
        ).gte('sale_date', start_date).lte('sale_date', end_date)
        
        if platform:
            platform_result = supabase.table('platform').select('id').eq('platform_code', platform).execute()
            if platform_result.data:
                query = query.eq('platform_id', platform_result.data[0]['id'])
        
        result = query.execute()
        transactions = result.data
        
        if not transactions:
            return {
                "total_sales": 0,
                "total_transactions": 0,
                "avg_order_value": 0,
                "top_products": [],
                "platform_breakdown": []
            }
        
        # 集計計算
        total_sales = sum(t['net_amount'] for t in transactions)
        total_transactions = len(transactions)
        avg_order_value = total_sales / total_transactions if total_transactions > 0 else 0
        
        # 商品別売上トップ10
        product_sales = {}
        for t in transactions:
            key = t['common_code']
            if key not in product_sales:
                product_sales[key] = {
                    'common_code': key,
                    'product_name': t['product']['product_name'],
                    'total_sales': 0,
                    'quantity_sold': 0
                }
            product_sales[key]['total_sales'] += t['net_amount']
            product_sales[key]['quantity_sold'] += t['quantity']
        
        top_products = sorted(
            product_sales.values(), 
            key=lambda x: x['total_sales'], 
            reverse=True
        )[:10]
        
        # プラットフォーム別売上
        platform_sales = {}
        for t in transactions:
            platform_name = t['platform']['name']
            if platform_name not in platform_sales:
                platform_sales[platform_name] = {
                    'platform': platform_name,
                    'total_sales': 0,
                    'transaction_count': 0
                }
            platform_sales[platform_name]['total_sales'] += t['net_amount']
            platform_sales[platform_name]['transaction_count'] += 1
        
        platform_breakdown = list(platform_sales.values())
        
        return {
            "total_sales": total_sales,
            "total_transactions": total_transactions,
            "avg_order_value": avg_order_value,
            "top_products": top_products,
            "platform_breakdown": platform_breakdown
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/inventory-analysis")
async def get_inventory_analysis():
    """在庫分析データを取得"""
    try:
        # 在庫評価ビューから取得
        result = supabase.table('inventory_valuation').select('*').execute()
        inventory_data = result.data
        
        # 集計
        total_value = sum(item['inventory_value'] for item in inventory_data)
        total_items = len(inventory_data)
        out_of_stock = len([item for item in inventory_data if item['stock_status'] == 'out_of_stock'])
        low_stock = len([item for item in inventory_data if item['stock_status'] == 'low_stock'])
        
        # 在庫金額上位商品
        top_value_items = sorted(
            inventory_data, 
            key=lambda x: x['inventory_value'], 
            reverse=True
        )[:10]
        
        # 在庫切れ・少ない商品
        critical_items = [
            item for item in inventory_data 
            if item['stock_status'] in ['out_of_stock', 'low_stock']
        ][:20]
        
        return {
            "summary": {
                "total_inventory_value": total_value,
                "total_items": total_items,
                "out_of_stock_count": out_of_stock,
                "low_stock_count": low_stock
            },
            "top_value_items": top_value_items,
            "critical_items": critical_items
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/profit-analysis")
async def get_profit_analysis(
    start_date: str = Query(..., description="開始日 (YYYY-MM-DD)"),
    end_date: str = Query(..., description="終了日 (YYYY-MM-DD)")
):
    """利益分析を取得"""
    try:
        # 商品別売上サマリービューから取得
        result = supabase.rpc('get_profit_analysis', {
            'start_date': start_date,
            'end_date': end_date
        }).execute()
        
        if not result.data:
            # ビューが存在しない場合の代替クエリ
            return await _calculate_profit_manual(start_date, end_date)
        
        return result.data
        
    except Exception as e:
        # フォールバック処理
        return await _calculate_profit_manual(start_date, end_date)

async def _calculate_profit_manual(start_date: str, end_date: str):
    """手動で利益計算を行う"""
    try:
        # 売上データ取得
        sales_result = supabase.table('sales_transactions').select(
            '''
            common_code,
            quantity,
            net_amount,
            product:common_code(product_name)
            '''
        ).gte('sale_date', start_date).lte('sale_date', end_date).execute()
        
        # 商品別集計
        product_profits = {}
        for sale in sales_result.data:
            code = sale['common_code']
            if code not in product_profits:
                # 最新の原価を取得
                cost_result = supabase.table('product_costs').select('cost_amount').eq(
                    'common_code', code
                ).eq('cost_type', 'total').order('cost_date', desc=True).limit(1).execute()
                
                unit_cost = cost_result.data[0]['cost_amount'] if cost_result.data else 0
                
                product_profits[code] = {
                    'common_code': code,
                    'product_name': sale['product']['product_name'],
                    'total_revenue': 0,
                    'total_quantity': 0,
                    'unit_cost': unit_cost,
                    'total_cost': 0,
                    'profit': 0
                }
            
            product_profits[code]['total_revenue'] += sale['net_amount']
            product_profits[code]['total_quantity'] += sale['quantity']
            product_profits[code]['total_cost'] += sale['quantity'] * product_profits[code]['unit_cost']
        
        # 利益計算
        for product in product_profits.values():
            product['profit'] = product['total_revenue'] - product['total_cost']
            product['profit_margin'] = (
                (product['profit'] / product['total_revenue']) * 100 
                if product['total_revenue'] > 0 else 0
            )
        
        # ソート
        sorted_products = sorted(
            product_profits.values(), 
            key=lambda x: x['profit'], 
            reverse=True
        )
        
        # 全体サマリー
        total_revenue = sum(p['total_revenue'] for p in product_profits.values())
        total_cost = sum(p['total_cost'] for p in product_profits.values())
        total_profit = total_revenue - total_cost
        
        return {
            "summary": {
                "total_revenue": total_revenue,
                "total_cost": total_cost,
                "total_profit": total_profit,
                "profit_margin": (total_profit / total_revenue * 100) if total_revenue > 0 else 0
            },
            "product_profits": sorted_products[:20]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/trend-analysis")
async def get_trend_analysis(
    days: int = Query(30, description="分析期間（日数）"),
    metric: str = Query("sales", description="分析指標: sales, quantity, profit")
):
    """トレンド分析（日別推移）"""
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # 日別売上サマリービューから取得
        result = supabase.table('daily_sales_summary').select('*').gte(
            'sale_date', start_date.date()
        ).lte('sale_date', end_date.date()).order('sale_date').execute()
        
        daily_data = result.data
        
        # 指標別にデータを整理
        trend_data = []
        for day in daily_data:
            if metric == "sales":
                value = day['net_sales']
            elif metric == "quantity":
                value = day['total_quantity']
            elif metric == "profit":
                # 利益は別途計算が必要（簡易版）
                value = day['net_sales'] * 0.3  # 仮定: 30%の利益率
            else:
                value = day['net_sales']
            
            trend_data.append({
                'date': day['sale_date'],
                'value': value,
                'platform_breakdown': {
                    'platform': day['platform_name'],
                    'value': value
                }
            })
        
        return {
            "metric": metric,
            "period_days": days,
            "trend_data": trend_data
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/platform-comparison")
async def get_platform_comparison(
    start_date: str = Query(..., description="開始日 (YYYY-MM-DD)"),
    end_date: str = Query(..., description="終了日 (YYYY-MM-DD)")
):
    """プラットフォーム比較分析"""
    try:
        result = supabase.table('daily_sales_summary').select(
            '''
            platform_name,
            sum(net_sales) as total_sales,
            sum(total_quantity) as total_quantity,
            sum(transaction_count) as total_transactions,
            avg(avg_unit_price) as avg_unit_price
            '''
        ).gte('sale_date', start_date).lte('sale_date', end_date).group(
            'platform_name'
        ).execute()
        
        platforms_data = result.data
        
        # 全体に占める割合を計算
        total_sales = sum(p['total_sales'] for p in platforms_data)
        
        for platform in platforms_data:
            platform['sales_share'] = (
                (platform['total_sales'] / total_sales * 100) 
                if total_sales > 0 else 0
            )
            platform['avg_order_value'] = (
                platform['total_sales'] / platform['total_transactions']
                if platform['total_transactions'] > 0 else 0
            )
        
        return {
            "period": {"start_date": start_date, "end_date": end_date},
            "platforms": platforms_data,
            "total_sales": total_sales
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))