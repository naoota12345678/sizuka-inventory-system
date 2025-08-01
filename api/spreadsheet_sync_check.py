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

@app.get("/api/spreadsheet_sync_check")
async def check_spreadsheet_sync():
    """スプレッドシート同期状況の確認"""
    try:
        if not supabase:
            return {"error": "Database connection not configured"}
        
        result = {
            "status": "success",
            "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat(),
            "sync_status": {},
            "data_samples": {},
            "mapping_stats": {}
        }
        
        # 1. 商品マスター（product_master）の確認
        try:
            product_master = supabase.table('product_master').select('*').limit(50).execute()
            master_data = product_master.data if product_master.data else []
            
            # 共通コードを持つ商品の統計
            with_common_code = [p for p in master_data if p.get('common_code')]
            without_common_code = [p for p in master_data if not p.get('common_code')]
            
            result["sync_status"]["product_master"] = {
                "total_count": len(master_data),
                "with_common_code": len(with_common_code),
                "without_common_code": len(without_common_code),
                "mapping_rate": round(len(with_common_code) / len(master_data) * 100, 2) if master_data else 0
            }
            
            # サンプルデータ
            result["data_samples"]["product_master"] = master_data[:5]
            
        except Exception as e:
            result["sync_status"]["product_master"] = {"error": str(e)}
        
        # 2. 統合商品テーブル（unified_products）の確認
        try:
            unified = supabase.table('unified_products').select('*').limit(50).execute()
            unified_data = unified.data if unified.data else []
            
            result["sync_status"]["unified_products"] = {
                "total_count": len(unified_data),
                "unique_common_codes": len(set(u.get('common_code', '') for u in unified_data if u.get('common_code')))
            }
            
            result["data_samples"]["unified_products"] = unified_data[:5]
            
        except Exception as e:
            result["sync_status"]["unified_products"] = {"error": str(e)}
        
        # 3. 選択肢コードのマッピング状況確認
        try:
            # 実際の商品データから選択肢コードを収集
            inventory = supabase.table('inventory').select('product_code, product_name').limit(100).execute()
            inventory_codes = {item['product_code'] for item in (inventory.data or [])}
            
            # 商品マスターでマッピングされているコード
            mapped_codes = {p['product_code'] for p in master_data if p.get('common_code')}
            
            # マッピング統計
            result["mapping_stats"] = {
                "inventory_products": len(inventory_codes),
                "mapped_products": len(inventory_codes & mapped_codes),
                "unmapped_products": len(inventory_codes - mapped_codes),
                "coverage_percentage": round(len(inventory_codes & mapped_codes) / len(inventory_codes) * 100, 2) if inventory_codes else 0
            }
            
            # 未マッピング商品のサンプル
            unmapped_samples = []
            for item in (inventory.data or []):
                if item['product_code'] not in mapped_codes:
                    unmapped_samples.append({
                        "product_code": item['product_code'],
                        "product_name": item['product_name']
                    })
                if len(unmapped_samples) >= 10:
                    break
            
            result["mapping_stats"]["unmapped_samples"] = unmapped_samples
            
        except Exception as e:
            result["mapping_stats"]["error"] = str(e)
        
        # 4. スプレッドシート同期の履歴確認
        try:
            # sync_logs テーブルがあれば確認
            sync_logs = supabase.table('sync_logs').select('*').order('created_at', desc=True).limit(5).execute()
            if sync_logs.data:
                result["sync_history"] = sync_logs.data
            else:
                result["sync_history"] = []
        except:
            result["sync_history"] = []
        
        return result
        
    except Exception as e:
        return JSONResponse(
            status_code=200,
            content={
                "status": "error",
                "message": str(e),
                "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
            }
        )

@app.get("/api/common_code_search")
async def search_common_code(
    code: Optional[str] = Query(None, description="商品コードまたは共通コード"),
    name: Optional[str] = Query(None, description="商品名")
):
    """共通コードマッピングの検索"""
    try:
        if not supabase:
            return {"error": "Database connection not configured"}
        
        results = []
        
        # 商品コードで検索
        if code:
            # product_masterから検索
            master_query = supabase.table('product_master').select('*').eq('product_code', code)
            master_result = master_query.execute()
            
            if master_result.data:
                for item in master_result.data:
                    common_code = item.get('common_code')
                    if common_code:
                        # 同じ共通コードを持つ他の商品を検索
                        related_query = supabase.table('product_master').select('*').eq('common_code', common_code)
                        related_result = related_query.execute()
                        
                        results.append({
                            "searched_code": code,
                            "common_code": common_code,
                            "common_name": item.get('common_name'),
                            "related_products": related_result.data if related_result.data else []
                        })
        
        # 商品名で検索
        if name:
            # product_masterから検索
            name_query = supabase.table('product_master').select('*').ilike('product_name', f'%{name}%').limit(20)
            name_result = name_query.execute()
            
            if name_result.data:
                # 共通コードでグループ化
                grouped = {}
                for item in name_result.data:
                    common_code = item.get('common_code', 'NO_MAPPING')
                    if common_code not in grouped:
                        grouped[common_code] = {
                            "common_code": common_code,
                            "common_name": item.get('common_name', ''),
                            "products": []
                        }
                    grouped[common_code]["products"].append({
                        "product_code": item.get('product_code'),
                        "product_name": item.get('product_name'),
                        "platform": item.get('platform', '')
                    })
                
                results.extend(list(grouped.values()))
        
        return {
            "status": "success",
            "search_params": {
                "code": code,
                "name": name
            },
            "results": results,
            "count": len(results),
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