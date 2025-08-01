from fastapi import FastAPI
from fastapi.responses import JSONResponse
from datetime import datetime
import pytz
import os
from supabase import create_client, Client
import requests
import pandas as pd
from io import StringIO

app = FastAPI()

# Supabase接続
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# スプレッドシートのCSV export URL
SPREADSHEET_BASE_URL = "https://docs.google.com/spreadsheets/d/1mLg1N0a1wubEIdKSouiW_jDaWUnuFLBxj8greczuS3E/export?format=csv&gid="

# 各シートのGID
SHEET_GIDS = {
    "platform_mapping": "1355500366",  # 選択肢コード対応表
    "bundle_components": "2056477845",  # まとめ商品内訳テーブル  
    "product_master": "0"               # 商品番号マッピング基本表
}

if SUPABASE_URL and SUPABASE_KEY:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
else:
    supabase = None

@app.get("/api/sync_spreadsheet_mappings")
async def sync_spreadsheet_mappings():
    """スプレッドシートの3つのマッピングテーブルをSupabaseに同期"""
    try:
        if not supabase:
            return {"error": "Database connection not configured"}
        
        results = {
            "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat(),
            "sync_results": {}
        }
        
        # 1. 商品番号マッピング基本表の同期
        platform_data = await fetch_sheet_data("platform_mapping")
        if platform_data:
            platform_result = await sync_platform_mapping(platform_data)
            results["sync_results"]["platform_mapping"] = platform_result
        
        # 2. まとめ商品内訳テーブルの同期
        bundle_data = await fetch_sheet_data("bundle_components")
        if bundle_data:
            bundle_result = await sync_bundle_components(bundle_data)
            results["sync_results"]["bundle_components"] = bundle_result
        
        # 3. 商品番号マッピング基本表の同期
        master_data = await fetch_sheet_data("product_master")
        if master_data:
            master_result = await sync_product_master(master_data)
            results["sync_results"]["product_master"] = master_result
        
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

async def fetch_sheet_data(sheet_type: str):
    """スプレッドシートからデータを取得"""
    try:
        gid = SHEET_GIDS.get(sheet_type)
        if not gid:
            return None
        
        url = f"{SPREADSHEET_BASE_URL}{gid}"
        response = requests.get(url, timeout=30)
        
        if response.status_code == 200:
            # CSVデータをDataFrameに変換
            csv_data = StringIO(response.text)
            df = pd.read_csv(csv_data)
            return df.to_dict('records')
        else:
            return None
            
    except Exception as e:
        print(f"Error fetching sheet {sheet_type}: {str(e)}")
        return None

async def sync_platform_mapping(data):
    """選択肢コード対応表の同期"""
    try:
        # 既存データをクリア
        supabase.table('platform_product_mapping').delete().neq('id', 0).execute()
        
        # 新しいデータを挿入
        mapping_records = []
        for row in data:
            # スプレッドシートの列名に応じて調整
            if 'プラットフォーム' in row and '商品コード' in row and '共通コード' in row:
                mapping_records.append({
                    'platform_name': row['プラットフォーム'].lower(),
                    'platform_product_code': str(row['商品コード']),
                    'common_code': row['共通コード'],
                    'platform_product_name': row.get('商品名', ''),
                    'is_active': True
                })
        
        if mapping_records:
            result = supabase.table('platform_product_mapping').insert(mapping_records).execute()
            return {
                "status": "success",
                "records_synced": len(mapping_records),
                "message": "選択肢コード対応表の同期完了"
            }
        else:
            return {
                "status": "warning", 
                "message": "同期するデータがありません"
            }
            
    except Exception as e:
        return {
            "status": "error",
            "message": f"選択肢コード対応表の同期エラー: {str(e)}"
        }

async def sync_bundle_components(data):
    """まとめ商品内訳テーブルの同期"""
    try:
        # 既存データをクリア
        supabase.table('product_bundle_components').delete().neq('id', 0).execute()
        
        # 新しいデータを挿入
        component_records = []
        for row in data:
            # スプレッドシートの列名に応じて調整
            if 'セット商品コード' in row and '構成商品コード' in row:
                component_records.append({
                    'bundle_common_code': row['セット商品コード'],
                    'component_common_code': row['構成商品コード'],
                    'quantity': int(row.get('数量', 1)),
                    'is_selectable': row.get('選択可能', 'FALSE').upper() == 'TRUE',
                    'selection_group': row.get('選択グループ', ''),
                    'required_count': int(row.get('必須選択数', 0)),
                    'display_order': int(row.get('表示順', 0)),
                    'is_active': True
                })
        
        if component_records:
            result = supabase.table('product_bundle_components').insert(component_records).execute()
            return {
                "status": "success",
                "records_synced": len(component_records),
                "message": "まとめ商品内訳テーブルの同期完了"
            }
        else:
            return {
                "status": "warning",
                "message": "同期するデータがありません"
            }
            
    except Exception as e:
        return {
            "status": "error",
            "message": f"まとめ商品内訳テーブルの同期エラー: {str(e)}"
        }

async def sync_product_master(data):
    """商品番号マッピング基本表の同期"""
    try:
        # 既存データをクリア（在庫データとの整合性に注意）
        supabase.table('product_mapping_master').delete().neq('id', 0).execute()
        
        # 新しいデータを挿入
        master_records = []
        for row in data:
            # スプレッドシートの列名に応じて調整
            if '共通コード' in row and '商品名' in row:
                master_records.append({
                    'common_code': row['共通コード'],
                    'product_name': row['商品名'],
                    'product_type': row.get('商品タイプ', 'single'),
                    'price': float(row['価格']) if row.get('価格') else None,
                    'description': row.get('説明', ''),
                    'is_active': True
                })
        
        if master_records:
            result = supabase.table('product_mapping_master').insert(master_records).execute()
            return {
                "status": "success", 
                "records_synced": len(master_records),
                "message": "商品番号マッピング基本表の同期完了"
            }
        else:
            return {
                "status": "warning",
                "message": "同期するデータがありません"
            }
            
    except Exception as e:
        return {
            "status": "error",
            "message": f"商品番号マッピング基本表の同期エラー: {str(e)}"
        }

@app.get("/api/validate_mappings")
async def validate_mappings():
    """マッピングデータの整合性チェック"""
    try:
        if not supabase:
            return {"error": "Database connection not configured"}
        
        validation_results = {
            "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat(),
            "validation_results": {}
        }
        
        # 1. プラットフォームマッピングの存在しない共通コードチェック
        platform_mappings = supabase.table('platform_product_mapping').select('common_code').execute()
        product_masters = supabase.table('product_mapping_master').select('common_code').execute()
        
        master_codes = set(item['common_code'] for item in product_masters.data) if product_masters.data else set()
        platform_codes = set(item['common_code'] for item in platform_mappings.data) if platform_mappings.data else set()
        
        orphan_platform_codes = platform_codes - master_codes
        validation_results["validation_results"]["orphan_platform_mappings"] = {
            "count": len(orphan_platform_codes),
            "codes": list(orphan_platform_codes)
        }
        
        # 2. バンドル構成の存在しない共通コードチェック
        bundle_components = supabase.table('product_bundle_components').select('bundle_common_code, component_common_code').execute()
        
        if bundle_components.data:
            bundle_codes = set()
            component_codes = set()
            for item in bundle_components.data:
                bundle_codes.add(item['bundle_common_code'])
                component_codes.add(item['component_common_code'])
            
            orphan_bundle_codes = bundle_codes - master_codes
            orphan_component_codes = component_codes - master_codes
            
            validation_results["validation_results"]["orphan_bundle_codes"] = {
                "count": len(orphan_bundle_codes),
                "codes": list(orphan_bundle_codes)
            }
            validation_results["validation_results"]["orphan_component_codes"] = {
                "count": len(orphan_component_codes),
                "codes": list(orphan_component_codes)
            }
        
        return validation_results
        
    except Exception as e:
        return JSONResponse(
            status_code=200,
            content={
                "status": "error",
                "message": str(e),
                "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
            }
        )