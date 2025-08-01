from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from datetime import datetime
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

@app.get("/api/product_mapping_check")
async def check_product_mapping(
    search: Optional[str] = Query(None, description="商品名で検索"),
    show_duplicates: Optional[bool] = Query(False, description="重複の可能性がある商品のみ表示")
):
    """商品名寄せ（統合）状況の確認"""
    try:
        if not supabase:
            return {"error": "Database connection not configured"}
        
        # 1. unified_productsテーブルの確認
        unified_query = supabase.table('unified_products').select('*')
        if search:
            unified_query = unified_query.ilike('common_name', f'%{search}%')
        
        unified_response = unified_query.execute()
        unified_products = unified_response.data if unified_response.data else []
        
        # 2. product_masterテーブルから商品を取得
        master_query = supabase.table('product_master').select('*')
        if search:
            master_query = master_query.or_(
                f'product_name.ilike.%{search}%,common_name.ilike.%{search}%'
            )
        
        master_response = master_query.execute()
        product_masters = master_response.data if master_response.data else []
        
        # 3. 実際の在庫・売上データから商品名を収集
        inventory_query = supabase.table('inventory').select('product_code, product_name')
        if search:
            inventory_query = inventory_query.ilike('product_name', f'%{search}%')
        inventory_response = inventory_query.execute()
        
        sales_query = supabase.table('sales_daily').select('product_code, product_name').limit(100)
        if search:
            sales_query = sales_query.ilike('product_name', f'%{search}%')
        sales_response = sales_query.execute()
        
        # 4. 名寄せ分析
        mapping_analysis = analyze_product_mapping(
            unified_products,
            product_masters,
            inventory_response.data or [],
            sales_response.data or []
        )
        
        # 5. 重複候補の検出
        duplicate_candidates = []
        if show_duplicates:
            duplicate_candidates = find_duplicate_candidates(
                inventory_response.data or [],
                sales_response.data or []
            )
        
        return {
            "status": "success",
            "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat(),
            "summary": {
                "unified_products_count": len(unified_products),
                "product_master_count": len(product_masters),
                "inventory_products": len(set(item['product_code'] for item in inventory_response.data or [])),
                "sales_products": len(set(item['product_code'] for item in sales_response.data or []))
            },
            "unified_products": unified_products[:10],  # 最初の10件
            "product_masters": product_masters[:10],    # 最初の10件
            "mapping_analysis": mapping_analysis,
            "duplicate_candidates": duplicate_candidates,
            "search_term": search
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

def analyze_product_mapping(unified: List[Dict], masters: List[Dict], 
                          inventory: List[Dict], sales: List[Dict]) -> Dict:
    """名寄せ状況の分析"""
    analysis = {
        "mapped_products": [],
        "unmapped_products": [],
        "mapping_coverage": 0
    }
    
    # 統合マスターのcommon_codeリスト
    unified_codes = {u.get('common_code', '') for u in unified}
    
    # 在庫・売上の全商品コード
    all_product_codes = set()
    all_product_codes.update(item.get('product_code', '') for item in inventory)
    all_product_codes.update(item.get('product_code', '') for item in sales)
    
    # マッピング済み商品の確認
    for master in masters:
        if master.get('common_code') in unified_codes:
            analysis["mapped_products"].append({
                "product_code": master.get('product_code'),
                "product_name": master.get('product_name'),
                "common_code": master.get('common_code'),
                "common_name": master.get('common_name')
            })
    
    # 未マッピング商品の検出
    master_codes = {m.get('product_code', '') for m in masters}
    for code in all_product_codes:
        if code not in master_codes:
            # 在庫または売上から商品名を取得
            product_name = None
            for item in inventory:
                if item.get('product_code') == code:
                    product_name = item.get('product_name')
                    break
            if not product_name:
                for item in sales:
                    if item.get('product_code') == code:
                        product_name = item.get('product_name')
                        break
            
            analysis["unmapped_products"].append({
                "product_code": code,
                "product_name": product_name,
                "source": "inventory/sales"
            })
    
    # カバレッジ計算
    if all_product_codes:
        mapped_count = len([c for c in all_product_codes if c in master_codes])
        analysis["mapping_coverage"] = round(mapped_count / len(all_product_codes) * 100, 2)
    
    return analysis

def find_duplicate_candidates(inventory: List[Dict], sales: List[Dict]) -> List[Dict]:
    """重複の可能性がある商品を検出"""
    from difflib import SequenceMatcher
    
    candidates = []
    all_products = {}
    
    # 全商品を収集
    for item in inventory + sales:
        code = item.get('product_code', '')
        name = item.get('product_name', '')
        if code and name:
            all_products[code] = name
    
    # 類似度チェック
    codes = list(all_products.keys())
    for i in range(len(codes)):
        for j in range(i + 1, len(codes)):
            name1 = all_products[codes[i]]
            name2 = all_products[codes[j]]
            
            # 文字列の類似度を計算
            similarity = SequenceMatcher(None, name1, name2).ratio()
            
            # 70%以上の類似度がある場合は重複候補
            if similarity > 0.7:
                candidates.append({
                    "product1": {
                        "code": codes[i],
                        "name": name1
                    },
                    "product2": {
                        "code": codes[j],
                        "name": name2
                    },
                    "similarity": round(similarity * 100, 2)
                })
    
    # 類似度の高い順にソート
    candidates.sort(key=lambda x: x['similarity'], reverse=True)
    
    return candidates[:20]  # 上位20件まで

@app.post("/api/create_product_mapping")
async def create_product_mapping(
    product_code: str = Query(..., description="商品コード"),
    common_code: str = Query(..., description="統合商品コード"),
    common_name: str = Query(..., description="統合商品名")
):
    """商品マッピングの作成/更新"""
    try:
        if not supabase:
            return {"error": "Database connection not configured"}
        
        # product_masterに登録/更新
        data = {
            "product_code": product_code,
            "common_code": common_code,
            "common_name": common_name,
            "updated_at": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
        }
        
        # Upsert操作
        response = supabase.table('product_master').upsert(data).execute()
        
        # unified_productsにも登録（存在しない場合）
        unified_check = supabase.table('unified_products').select('*').eq('common_code', common_code).execute()
        
        if not unified_check.data:
            unified_data = {
                "common_code": common_code,
                "common_name": common_name,
                "created_at": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
            }
            supabase.table('unified_products').insert(unified_data).execute()
        
        return {
            "status": "success",
            "message": f"商品マッピングを作成しました: {product_code} → {common_code}",
            "data": response.data,
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