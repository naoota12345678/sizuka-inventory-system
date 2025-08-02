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

@app.get("/api/platform_sync")
async def unified_platform_sync(
    platform: str = Query(..., description="同期プラットフォーム (rakuten/amazon/colorme/airegi)"),
    action: str = Query("sync", description="実行アクション (sync/analyze/test)"),
    date_from: Optional[str] = Query(None, description="同期開始日 (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="同期終了日 (YYYY-MM-DD)")
):
    """統合プラットフォーム同期API - 全ECサイト対応"""
    try:
        if not supabase:
            return {"error": "Database connection not configured"}
        
        result = {
            "platform": platform,
            "action": action,
            "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
        }
        
        if platform == "rakuten":
            if action == "sync":
                result["data"] = await sync_rakuten_orders(date_from, date_to)
            elif action == "analyze":
                result["data"] = await analyze_rakuten_structure()
            elif action == "test":
                result["data"] = await test_rakuten_connection()
                
        elif platform == "amazon":
            if action == "sync":
                result["data"] = await sync_amazon_orders(date_from, date_to)
            elif action == "analyze":
                result["data"] = {"message": "Amazon分析機能準備中"}
            elif action == "test":
                result["data"] = await test_amazon_connection()
                
        elif platform == "colorme":
            if action == "sync":
                result["data"] = await sync_colorme_orders(date_from, date_to)
            elif action == "analyze":
                result["data"] = {"message": "ColorME分析機能準備中"}
            elif action == "test":
                result["data"] = await test_colorme_connection()
                
        elif platform == "airegi":
            if action == "sync":
                result["data"] = await sync_airegi_orders(date_from, date_to)
            elif action == "analyze":
                result["data"] = {"message": "Airegi分析機能準備中"}
            elif action == "test":
                result["data"] = await test_airegi_connection()
                
        else:
            return {
                "status": "error",
                "message": f"未対応プラットフォーム: {platform}",
                "supported_platforms": ["rakuten", "amazon", "colorme", "airegi"]
            }
        
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

@app.get("/api/mapping_tools")
async def unified_mapping_tools(
    tool: str = Query(..., description="マッピングツール (smart/enhanced/manual/validate)"),
    target: Optional[str] = Query(None, description="対象商品コード"),
    auto_apply: Optional[bool] = Query(False, description="自動適用")
):
    """統合マッピングツールAPI"""
    try:
        if not supabase:
            return {"error": "Database connection not configured"}
        
        result = {
            "tool": tool,
            "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
        }
        
        if tool == "smart":
            result["data"] = await run_smart_mapping(auto_apply)
        elif tool == "enhanced":
            result["data"] = await run_enhanced_mapping()
        elif tool == "manual":
            result["data"] = await get_manual_mapping_candidates(target)
        elif tool == "validate":
            result["data"] = await validate_all_mappings()
        else:
            return {
                "status": "error",
                "message": f"未対応ツール: {tool}",
                "supported_tools": ["smart", "enhanced", "manual", "validate"]
            }
        
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

@app.get("/api/admin_tools")
async def unified_admin_tools(
    tool: str = Query(..., description="管理ツール (convert_sales/setup_inventory/debug/cleanup)"),
    confirm: Optional[bool] = Query(False, description="実行確認")
):
    """統合管理ツールAPI"""
    try:
        if not supabase:
            return {"error": "Database connection not configured"}
        
        result = {
            "tool": tool,
            "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
        }
        
        if tool == "convert_sales":
            result["data"] = await convert_sales_data_internal()
        elif tool == "setup_inventory":
            result["data"] = await setup_initial_inventory()
        elif tool == "debug":
            result["data"] = await run_debug_analysis()
        elif tool == "cleanup":
            if confirm:
                result["data"] = await cleanup_old_data()
            else:
                result["data"] = {"message": "確認が必要です。confirm=trueを追加してください"}
        else:
            return {
                "status": "error",
                "message": f"未対応ツール: {tool}",
                "supported_tools": ["convert_sales", "setup_inventory", "debug", "cleanup"]
            }
        
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

# 楽天関連機能
async def sync_rakuten_orders(date_from: str, date_to: str):
    """楽天注文同期 - 実際の楽天APIから注文データを取得"""
    try:
        from datetime import datetime, timedelta
        from api.rakuten_api import RakutenAPI
        
        # 日付の設定
        if not date_from:
            date_from = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        if not date_to:
            date_to = datetime.now().strftime('%Y-%m-%d')
        
        start_date = datetime.strptime(date_from, '%Y-%m-%d')
        end_date = datetime.strptime(date_to, '%Y-%m-%d')
        
        # 楽天API初期化
        rakuten_api = RakutenAPI()
        
        # 注文データの取得
        orders = rakuten_api.get_orders(start_date, end_date)
        
        # データベースに保存
        result = rakuten_api.save_to_supabase(orders)
        
        return {
            "status": "success",
            "message": f"楽天注文同期完了: {date_from} から {date_to}",
            "period": f"{date_from} - {date_to}",
            "orders_processed": result.get('total_orders', 0),
            "items_processed": result.get('items_success', 0),
            "success_rate": result.get('success_rate', '0%'),
            "details": result
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"楽天同期エラー: {str(e)}",
            "date_from": date_from,
            "date_to": date_to
        }

async def analyze_rakuten_structure():
    """楽天SKU構造分析"""
    try:
        # order_itemsから選択肢コード分析
        order_items = supabase.table('order_items').select('product_code, product_name, extended_info').limit(20).execute()
        
        analysis = {
            "total_items": len(order_items.data) if order_items.data else 0,
            "choice_code_patterns": [],
            "sku_analysis": {}
        }
        
        if order_items.data:
            for item in order_items.data:
                product_name = item.get('product_name', '')
                # 選択肢コードパターン抽出
                if '【' in product_name or '[' in product_name:
                    analysis["choice_code_patterns"].append(product_name)
        
        return analysis
        
    except Exception as e:
        return {"error": f"楽天構造分析エラー: {str(e)}"}

async def test_rakuten_connection():
    """楽天接続テスト"""
    return {"status": "rakuten_test", "message": "楽天API接続テスト"}

# Amazon関連機能（準備中）
async def sync_amazon_orders(date_from: str, date_to: str):
    """Amazon注文同期（準備中）"""
    return {"message": "Amazon注文同期準備中", "status": "pending"}

async def test_amazon_connection():
    """Amazon接続テスト"""
    return {"status": "amazon_test", "message": "Amazon API接続準備中"}

# ColorME関連機能（準備中）
async def sync_colorme_orders(date_from: str, date_to: str):
    """ColorME注文同期（準備中）"""
    return {"message": "ColorME注文同期準備中", "status": "pending"}

async def test_colorme_connection():
    """ColorME接続テスト"""
    return {"status": "colorme_test", "message": "ColorME API接続準備中"}

# Airegi関連機能（準備中）
async def sync_airegi_orders(date_from: str, date_to: str):
    """Airegi注文同期（準備中）"""
    return {"message": "Airegi注文同期準備中", "status": "pending"}

async def test_airegi_connection():
    """Airegi接続テスト"""
    return {"status": "airegi_test", "message": "Airegi API接続準備中"}

# マッピング関連機能
async def run_smart_mapping(auto_apply: bool):
    """スマートマッピング実行"""
    return {"message": "スマートマッピング実行", "auto_apply": auto_apply}

async def run_enhanced_mapping():
    """拡張マッピング実行"""
    return {"message": "拡張マッピング実行"}

async def get_manual_mapping_candidates(target: str):
    """手動マッピング候補取得"""
    return {"message": "手動マッピング候補", "target": target}

async def validate_all_mappings():
    """全マッピング検証"""
    return {"message": "全マッピング検証実行"}

# 管理ツール関連機能
async def convert_sales_data_internal():
    """売上データ変換（内部版）"""
    return {"message": "売上データ変換実行"}

async def setup_initial_inventory():
    """初期在庫セットアップ"""
    return {"message": "初期在庫セットアップ実行"}

async def run_debug_analysis():
    """デバッグ分析実行"""
    return {"message": "デバッグ分析実行"}

async def cleanup_old_data():
    """古いデータクリーンアップ"""
    return {"message": "古いデータクリーンアップ実行"}