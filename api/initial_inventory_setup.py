from fastapi import FastAPI
from fastapi.responses import JSONResponse
from datetime import datetime, date
import pytz
import os
from supabase import create_client, Client
from typing import List, Dict

app = FastAPI()

# Supabase接続
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if SUPABASE_URL and SUPABASE_KEY:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
else:
    supabase = None

# 2月10日の初期在庫データ
INITIAL_INVENTORY_DATA = [
    {"product_name": "ふわふわスモークサーモン", "price": 800, "unit": "15g", "quantity": 119, "product_code": "457326558401"},
    {"product_name": "スモークサーモンチップ", "price": 800, "unit": "30g", "quantity": 122, "product_code": "457326558403"},
    {"product_name": "コーンフレーク", "price": 800, "unit": "20g", "quantity": 60, "product_code": "457326558421"},
    {"product_name": "かぼちゃフレーク", "price": 800, "unit": "20g", "quantity": 58, "product_code": "457326558422"},
    {"product_name": "にんじんフレーク", "price": 800, "unit": "20g", "quantity": 56, "product_code": "457326558423"},
    {"product_name": "ビーツフレーク", "price": 800, "unit": "15g", "quantity": 96, "product_code": "457326558424"},
    {"product_name": "ポテトフレーク", "price": 800, "unit": "15g", "quantity": 107, "product_code": "457326558425"},
    {"product_name": "ころころクッキー", "price": 800, "unit": "30粒", "quantity": 32, "product_code": "457326558426"},
    {"product_name": "エゾ鹿カットジャーキー", "price": 800, "unit": "70g", "quantity": 16, "product_code": "457326558427"},
    {"product_name": "ラムカットジャーキー", "price": 800, "unit": "70g", "quantity": 29, "product_code": "457326558428"},
    {"product_name": "鮭カットジャーキー", "price": 800, "unit": "70g", "quantity": 42, "product_code": "457326558429"},
    {"product_name": "たらカットジャーキー", "price": 800, "unit": "70g", "quantity": 0, "product_code": "457326558430"},
    {"product_name": "ほっけカットジャーキー", "price": 800, "unit": "70g", "quantity": 16, "product_code": "457326558431"},
    # 物販
    {"product_name": "犬缶", "price": 600, "unit": "50g", "quantity": 16, "product_code": "457326558601"},
    {"product_name": "猫缶", "price": 500, "unit": "35g", "quantity": 58, "product_code": "457326558602"},
    {"product_name": "犬猫缶", "price": 500, "unit": "35g", "quantity": 0, "product_code": "457326558603"},
    {"product_name": "SALT BUBBLE", "price": 3500, "unit": "80g", "quantity": 7, "product_code": "457326558604"},
    {"product_name": "エゾディアハンドクリーム", "price": 1500, "unit": "20g", "quantity": 32, "product_code": "457326558605"},
    {"product_name": "エゾディア肉球クリーム", "price": 2400, "unit": "20g", "quantity": 29, "product_code": "457326558606"},
    {"product_name": "おさんぽセット", "price": 3700, "unit": "", "quantity": 0, "product_code": "457326558607"},
    {"product_name": "SIZUKA濃縮クマザサエキス", "price": 3000, "unit": "10ml", "quantity": 3, "product_code": "457326558608"},
    {"product_name": "ミニチュア木箱（エゾ鹿）", "price": 1300, "unit": "20g", "quantity": 27, "product_code": "457326558609"},
    {"product_name": "ミニチュア木箱（サーモン）", "price": 1300, "unit": "20g", "quantity": 50, "product_code": "457326558610"},
    {"product_name": "トートバッグ（リボン付き）", "price": 1000, "unit": "", "quantity": 9, "product_code": "457326558611"},
    {"product_name": "SIZUKAショルダーバック", "price": 100, "unit": "", "quantity": 0, "product_code": "457326558612"},
    {"product_name": "SIZUKA梨地袋", "price": 30, "unit": "", "quantity": 0, "product_code": "457326558613"},
    {"product_name": "おやつ入ポチ袋", "price": 1000, "unit": "", "quantity": 0, "product_code": "457326558614"},
    {"product_name": "ハッピーセット", "price": 6000, "unit": "", "quantity": 0, "product_code": "457326558615"}
]

@app.post("/api/setup_initial_inventory")
async def setup_initial_inventory():
    """2月10日の初期在庫をセットアップ"""
    try:
        if not supabase:
            return {"error": "Database connection not configured"}
        
        base_date = date(2025, 2, 10)  # 2025年2月10日を基準日とする
        
        results = {
            "status": "started",
            "base_date": base_date.isoformat(),
            "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat(),
            "processed": [],
            "errors": []
        }
        
        for item in INITIAL_INVENTORY_DATA:
            try:
                # 在庫テーブルへの登録/更新
                inventory_data = {
                    "product_code": item["product_code"],
                    "product_name": item["product_name"],
                    "current_stock": item["quantity"],
                    "minimum_stock": 5,  # デフォルト最小在庫
                    "unit": item["unit"] or "個",
                    "unit_price": item["price"],
                    "category": "食品" if item["price"] == 800 else "物販",
                    "updated_at": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
                }
                
                # Upsert（既存データがあれば更新、なければ挿入）
                inventory_response = supabase.table('inventory').upsert(inventory_data).execute()
                
                # 在庫履歴テーブルへの基準日登録
                history_data = {
                    "date": base_date.isoformat(),
                    "product_code": item["product_code"],
                    "product_name": item["product_name"],
                    "opening_stock": item["quantity"],
                    "production_qty": 0,
                    "sales_qty": 0,
                    "adjustment_qty": 0,
                    "closing_stock": item["quantity"],
                    "notes": "初期在庫設定（2025/2/10基準）",
                    "created_at": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
                }
                
                # 在庫履歴に記録（inventory_historyテーブルが存在する場合）
                try:
                    history_response = supabase.table('inventory_history').upsert(history_data).execute()
                    
                    results["processed"].append({
                        "product_code": item["product_code"],
                        "product_name": item["product_name"],
                        "quantity": item["quantity"],
                        "status": "success"
                    })
                    
                except Exception as history_error:
                    # 履歴テーブルがない場合は在庫テーブルのみ更新
                    results["processed"].append({
                        "product_code": item["product_code"],
                        "product_name": item["product_name"],
                        "quantity": item["quantity"],
                        "status": "inventory_only",
                        "note": "履歴テーブル未作成"
                    })
                
            except Exception as e:
                results["errors"].append({
                    "product_code": item["product_code"],
                    "product_name": item["product_name"],
                    "error": str(e)
                })
        
        results["status"] = "completed"
        results["summary"] = {
            "total_items": len(INITIAL_INVENTORY_DATA),
            "processed": len(results["processed"]),
            "errors": len(results["errors"])
        }
        
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

@app.post("/api/calculate_current_inventory")
async def calculate_current_inventory():
    """2月10日から現在までの売上を差し引いて現在の在庫を計算"""
    try:
        if not supabase:
            return {"error": "Database connection not configured"}
        
        base_date = date(2025, 2, 10)
        current_date = date.today()
        
        results = {
            "status": "started",
            "calculation_period": f"{base_date} to {current_date}",
            "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat(),
            "updates": []
        }
        
        # 基準日以降の売上データを取得
        sales_response = supabase.table('sales_daily').select('*').gte(
            'summary_date', base_date.isoformat()
        ).execute()
        
        # 商品コード別の売上数量を集計
        sales_totals = {}
        for sale in sales_response.data or []:
            product_code = sale.get('product_code')
            units_sold = sale.get('units_sold', 0)
            
            if product_code:
                if product_code not in sales_totals:
                    sales_totals[product_code] = 0
                sales_totals[product_code] += units_sold
        
        # 各商品の在庫を更新
        for item in INITIAL_INVENTORY_DATA:
            product_code = item["product_code"]
            initial_stock = item["quantity"]
            sold_quantity = sales_totals.get(product_code, 0)
            
            # 現在在庫 = 初期在庫 - 売上数量
            current_stock = max(0, initial_stock - sold_quantity)
            
            # 在庫テーブルを更新
            update_response = supabase.table('inventory').update({
                "current_stock": current_stock,
                "updated_at": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
            }).eq('product_code', product_code).execute()
            
            results["updates"].append({
                "product_code": product_code,
                "product_name": item["product_name"],
                "initial_stock": initial_stock,
                "sold_quantity": sold_quantity,
                "current_stock": current_stock,
                "status": "updated" if update_response.data else "not_found"
            })
        
        results["status"] = "completed"
        results["summary"] = {
            "days_calculated": (current_date - base_date).days,
            "products_updated": len([u for u in results["updates"] if u["status"] == "updated"]),
            "total_sales_records": len(sales_response.data) if sales_response.data else 0
        }
        
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