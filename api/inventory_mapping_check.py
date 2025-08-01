from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from datetime import datetime
import pytz
import os
from supabase import create_client, Client
from typing import Optional, Dict, List

app = FastAPI()

# Supabase接続
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if SUPABASE_URL and SUPABASE_KEY:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
else:
    supabase = None

@app.get("/api/inventory_mapping_check")
async def check_inventory_mapping():
    """在庫情報がどこにマッピングされているか全体的に確認"""
    try:
        if not supabase:
            return {"error": "Database connection not configured"}
        
        mapping_info = {
            "status": "success",
            "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat(),
            "tables": {},
            "mapping_summary": {},
            "data_flow": []
        }
        
        # 1. 各テーブルの在庫関連データを確認
        tables_to_check = [
            'inventory',
            'product_master', 
            'unified_products',
            'sales_daily',
            'orders',
            'order_items'
        ]
        
        for table_name in tables_to_check:
            try:
                # テーブルの構造とサンプルデータを取得
                response = supabase.table(table_name).select('*').limit(3).execute()
                
                if response.data:
                    sample = response.data[0]
                    mapping_info["tables"][table_name] = {
                        "exists": True,
                        "record_count": len(response.data),
                        "columns": list(sample.keys()),
                        "sample_data": sample,
                        "inventory_related_fields": find_inventory_fields(sample)
                    }
                else:
                    mapping_info["tables"][table_name] = {
                        "exists": True,
                        "record_count": 0,
                        "columns": [],
                        "sample_data": None,
                        "inventory_related_fields": []
                    }
                    
            except Exception as e:
                mapping_info["tables"][table_name] = {
                    "exists": False,
                    "error": str(e)
                }
        
        # 2. データの相互関係を分析
        mapping_info["data_flow"] = analyze_data_flow(mapping_info["tables"])
        
        # 3. マッピングサマリーを作成
        mapping_info["mapping_summary"] = create_mapping_summary(mapping_info["tables"])
        
        # 4. 在庫データの所在を特定
        mapping_info["inventory_locations"] = identify_inventory_locations(mapping_info["tables"])
        
        return mapping_info
        
    except Exception as e:
        return JSONResponse(
            status_code=200,
            content={
                "status": "error",
                "message": str(e),
                "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
            }
        )

def find_inventory_fields(data_sample: Dict) -> List[str]:
    """在庫関連のフィールドを特定"""
    inventory_keywords = [
        'stock', 'quantity', 'amount', 'count', 'units', 
        'current', 'minimum', 'maximum', 'available',
        'product_code', 'product_name', 'sku', 'code'
    ]
    
    inventory_fields = []
    for field_name in data_sample.keys():
        field_lower = field_name.lower()
        if any(keyword in field_lower for keyword in inventory_keywords):
            inventory_fields.append(field_name)
    
    return inventory_fields

def analyze_data_flow(tables: Dict) -> List[Dict]:
    """データフローを分析"""
    flow = []
    
    # 製造データ → 在庫
    if tables.get('inventory', {}).get('exists'):
        flow.append({
            "step": 1,
            "process": "製造データ入力",
            "source": "Google Form + GAS",
            "target": "inventory テーブル",
            "description": "製造された商品が在庫に追加される"
        })
    
    # 注文データ → 売上 → 在庫減算
    if tables.get('orders', {}).get('exists') and tables.get('sales_daily', {}).get('exists'):
        flow.append({
            "step": 2,
            "process": "楽天注文同期",
            "source": "楽天API",
            "target": "orders → sales_daily",
            "description": "注文データから売上を集計"
        })
        
        flow.append({
            "step": 3,
            "process": "在庫減算",
            "source": "sales_daily",
            "target": "inventory",
            "description": "売上分だけ在庫を減算"
        })
    
    # 商品マスタ連携
    if tables.get('product_master', {}).get('exists'):
        flow.append({
            "step": 4,
            "process": "商品名寄せ",
            "source": "スプレッドシート",
            "target": "product_master → unified_products",
            "description": "商品コードと共通名のマッピング"
        })
    
    return flow

def create_mapping_summary(tables: Dict) -> Dict:
    """マッピングサマリーを作成"""
    summary = {
        "primary_inventory_table": None,
        "product_mapping_table": None,
        "sales_data_table": None,
        "key_relationships": []
    }
    
    # 主要な在庫テーブルを特定
    if tables.get('inventory', {}).get('exists'):
        summary["primary_inventory_table"] = "inventory"
        inventory_fields = tables['inventory'].get('inventory_related_fields', [])
        summary["key_relationships"].append({
            "table": "inventory",
            "role": "現在在庫管理",
            "key_fields": inventory_fields
        })
    
    # 商品マッピングテーブルを特定
    if tables.get('product_master', {}).get('exists'):
        summary["product_mapping_table"] = "product_master"
        summary["key_relationships"].append({
            "table": "product_master", 
            "role": "商品コード→共通名マッピング",
            "key_fields": tables['product_master'].get('inventory_related_fields', [])
        })
    
    # 売上データテーブルを特定
    if tables.get('sales_daily', {}).get('exists'):
        summary["sales_data_table"] = "sales_daily"
        summary["key_relationships"].append({
            "table": "sales_daily",
            "role": "日別売上集計",
            "key_fields": tables['sales_daily'].get('inventory_related_fields', [])
        })
    
    return summary

def identify_inventory_locations(tables: Dict) -> Dict:
    """在庫データの所在を特定"""
    locations = {
        "current_stock": [],
        "product_info": [],
        "sales_data": [],
        "mapping_data": []
    }
    
    for table_name, table_info in tables.items():
        if not table_info.get('exists'):
            continue
            
        sample_data = table_info.get('sample_data', {})
        if not sample_data:
            continue
        
        # 現在在庫
        stock_fields = [f for f in sample_data.keys() if 'stock' in f.lower()]
        if stock_fields:
            locations["current_stock"].append({
                "table": table_name,
                "fields": stock_fields,
                "sample_value": {f: sample_data.get(f) for f in stock_fields[:3]}
            })
        
        # 商品情報
        product_fields = [f for f in sample_data.keys() if any(kw in f.lower() for kw in ['product', 'name', 'code'])]
        if product_fields:
            locations["product_info"].append({
                "table": table_name,
                "fields": product_fields,
                "sample_value": {f: sample_data.get(f) for f in product_fields[:3]}
            })
        
        # 売上データ
        sales_fields = [f for f in sample_data.keys() if any(kw in f.lower() for kw in ['sales', 'sold', 'units', 'amount'])]
        if sales_fields:
            locations["sales_data"].append({
                "table": table_name,
                "fields": sales_fields,
                "sample_value": {f: sample_data.get(f) for f in sales_fields[:3]}
            })
        
        # マッピングデータ
        mapping_fields = [f for f in sample_data.keys() if any(kw in f.lower() for kw in ['common', 'unified', 'mapping'])]
        if mapping_fields:
            locations["mapping_data"].append({
                "table": table_name,
                "fields": mapping_fields,
                "sample_value": {f: sample_data.get(f) for f in mapping_fields[:3]}
            })
    
    return locations

@app.get("/api/inventory_data_trace")
async def trace_inventory_data(
    search_term: Optional[str] = Query(None, description="商品名や商品コードで検索")
):
    """特定の商品の在庫データがどこにあるかトレース"""
    try:
        if not supabase:
            return {"error": "Database connection not configured"}
        
        if not search_term:
            return {"error": "検索キーワードを指定してください"}
        
        trace_result = {
            "status": "success",
            "search_term": search_term,
            "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat(),
            "found_in": []
        }
        
        # 各テーブルで検索
        tables_to_search = ['inventory', 'product_master', 'sales_daily', 'orders', 'order_items']
        
        for table_name in tables_to_search:
            try:
                # テーブルから検索（複数フィールドで検索）
                response = supabase.table(table_name).select('*').limit(100).execute()
                
                if response.data:
                    matching_records = []
                    for record in response.data:
                        # 全フィールドを検索
                        for field_name, field_value in record.items():
                            if field_value and search_term.lower() in str(field_value).lower():
                                matching_records.append({
                                    "record": record,
                                    "matched_field": field_name,
                                    "matched_value": field_value
                                })
                                break
                    
                    if matching_records:
                        trace_result["found_in"].append({
                            "table": table_name,
                            "match_count": len(matching_records),
                            "matches": matching_records[:3]  # 最初の3件
                        })
                        
            except Exception as e:
                trace_result["found_in"].append({
                    "table": table_name,
                    "error": str(e)
                })
        
        return trace_result
        
    except Exception as e:
        return JSONResponse(
            status_code=200,
            content={
                "status": "error",
                "message": str(e),
                "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
            }
        )