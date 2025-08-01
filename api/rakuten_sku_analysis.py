from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from datetime import datetime
import pytz
import os
from supabase import create_client, Client
from typing import Optional, List, Dict
import json

app = FastAPI()

# Supabase接続
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if SUPABASE_URL and SUPABASE_KEY:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
else:
    supabase = None

@app.get("/api/analyze_rakuten_sku_structure")
async def analyze_rakuten_sku_structure():
    """楽天のSKU構造と選択肢コードを詳細分析"""
    try:
        if not supabase:
            return {"error": "Database connection not configured"}
        
        # 現在のorder_itemsデータを詳細分析
        raw_analysis = await analyze_current_order_items()
        
        # 楽天API応答の構造分析
        api_structure_analysis = get_rakuten_api_structure_info()
        
        # 選択肢コード抽出パターンの提案
        choice_code_patterns = analyze_choice_code_patterns(raw_analysis)
        
        return {
            "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat(),
            "current_data_analysis": raw_analysis,
            "rakuten_api_structure": api_structure_analysis,
            "choice_code_patterns": choice_code_patterns,
            "improvement_recommendations": get_improvement_recommendations()
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

async def analyze_current_order_items():
    """現在のorder_itemsデータを詳細分析"""
    try:
        # 全order_itemsデータを取得
        order_items = supabase.table('order_items').select('*').limit(50).execute()
        
        if not order_items.data:
            return {"error": "order_itemsデータが見つかりません"}
        
        analysis = {
            "total_items": len(order_items.data),
            "product_code_patterns": {},
            "product_name_patterns": {},
            "extended_info_analysis": {},
            "sample_items": []
        }
        
        for item in order_items.data:
            product_code = item.get('product_code', '')
            product_name = item.get('product_name', '')
            extended_info = item.get('extended_info', {})
            
            # 商品コードパターン分析
            if product_code:
                code_length = len(product_code)
                if code_length not in analysis["product_code_patterns"]:
                    analysis["product_code_patterns"][code_length] = []
                analysis["product_code_patterns"][code_length].append(product_code)
            
            # 商品名パターン分析
            if product_name:
                if '【' in product_name or '(' in product_name or '[' in product_name:
                    if "choice_indicators" not in analysis["product_name_patterns"]:
                        analysis["product_name_patterns"]["choice_indicators"] = []
                    analysis["product_name_patterns"]["choice_indicators"].append(product_name)
            
            # extended_info分析
            if extended_info:
                for key, value in extended_info.items():
                    if key not in analysis["extended_info_analysis"]:
                        analysis["extended_info_analysis"][key] = {"count": 0, "samples": []}
                    analysis["extended_info_analysis"][key]["count"] += 1
                    if len(analysis["extended_info_analysis"][key]["samples"]) < 3 and value:
                        analysis["extended_info_analysis"][key]["samples"].append(str(value)[:100])
            
            # サンプルアイテム
            if len(analysis["sample_items"]) < 10:
                analysis["sample_items"].append({
                    "product_code": product_code,
                    "product_name": product_name[:100],
                    "extended_info": extended_info
                })
        
        # 商品コードパターンをソート
        for code_length in analysis["product_code_patterns"]:
            analysis["product_code_patterns"][code_length] = list(set(analysis["product_code_patterns"][code_length]))[:10]
        
        return analysis
        
    except Exception as e:
        return {"error": f"データ分析エラー: {str(e)}"}

def get_rakuten_api_structure_info():
    """楽天APIの構造情報（ドキュメントベース）"""
    return {
        "parent_child_structure": {
            "description": "楽天の親子商品構造",
            "parent_item": {
                "itemType": 1,
                "description": "親商品（まとめ商品、選択肢商品）",
                "contains": "selectedItems配列"
            },
            "child_item": {
                "itemType": 0,
                "description": "子商品（実際の選択された商品）",
                "contains": "選択肢コード情報"
            }
        },
        "choice_code_locations": {
            "selectedItems": {
                "description": "親商品内の選択された商品一覧",
                "potential_fields": [
                    "choiceId",
                    "choiceCode", 
                    "variantId",
                    "optionId",
                    "itemName",
                    "itemId"
                ]
            },
            "item_properties": {
                "description": "商品プロパティ内の選択肢情報",
                "potential_fields": [
                    "properties",
                    "variants",
                    "options",
                    "choices"
                ]
            }
        },
        "sku_identification": {
            "description": "SKU識別の方法",
            "methods": [
                "itemId + variantId",
                "shopItemCode",
                "janCode",
                "choiceId組み合わせ"
            ]
        }
    }

def analyze_choice_code_patterns(raw_analysis):
    """選択肢コードパターンの分析"""
    patterns = {
        "detected_patterns": [],
        "potential_choice_codes": [],
        "extraction_strategies": []
    }
    
    # サンプルデータから選択肢コードらしきパターンを検索
    sample_items = raw_analysis.get("sample_items", [])
    
    for item in sample_items:
        product_name = item.get("product_name", "")
        extended_info = item.get("extended_info", {})
        
        # 商品名から選択肢コードパターンを抽出
        choice_patterns = extract_choice_patterns_from_name(product_name)
        if choice_patterns:
            patterns["detected_patterns"].extend(choice_patterns)
        
        # extended_infoから選択肢情報を抽出
        choice_info = extract_choice_info_from_extended(extended_info)
        if choice_info:
            patterns["potential_choice_codes"].extend(choice_info)
    
    # 抽出戦略の提案
    patterns["extraction_strategies"] = [
        {
            "strategy": "selectedItems解析",
            "description": "楽天API応答のselectedItems配列から選択肢コードを抽出",
            "implementation": "parent_item.selectedItems[].choiceId/choiceCode"
        },
        {
            "strategy": "商品名パターンマッチング",
            "description": "商品名から【L】【M】【S】などのパターンを抽出",
            "implementation": "正規表現: r'【([LMS]\\d*)】|\\[([LMS]\\d*)\\]|\\(([LMS]\\d*)\\)'"
        },
        {
            "strategy": "variantId活用",
            "description": "楽天のvariantIdから選択肢情報を抽出",
            "implementation": "extended_info.rakuten_variant_id"
        },
        {
            "strategy": "shopItemCode解析",
            "description": "店舗商品コードから選択肢コードを抽出",
            "implementation": "extended_info.shop_item_code"
        }
    ]
    
    return patterns

def extract_choice_patterns_from_name(product_name: str) -> List[str]:
    """商品名から選択肢パターンを抽出"""
    import re
    
    if not product_name:
        return []
    
    patterns = []
    
    # 一般的な選択肢パターン
    choice_patterns = [
        r'【([LMS]\d*)】',  # 【L01】【M02】【S03】
        r'\[([LMS]\d*)\]',  # [L01][M02][S03]
        r'\(([LMS]\d*)\)',  # (L01)(M02)(S03)
        r'([LMS]\d+)',      # L01 M02 S03
        r'サイズ[:：]([LMS])',  # サイズ:L
        r'(\d+g|\d+グラム|\d+ｇ)',  # 重量表記
        r'(小|中|大|特大)',  # サイズ表記
    ]
    
    for pattern in choice_patterns:
        matches = re.findall(pattern, product_name, re.IGNORECASE)
        patterns.extend(matches)
    
    return patterns

def extract_choice_info_from_extended(extended_info: Dict) -> List[str]:
    """extended_infoから選択肢情報を抽出"""
    choice_info = []
    
    if not extended_info:
        return choice_info
    
    # 重要なフィールドをチェック
    important_fields = [
        'rakuten_variant_id',
        'shop_item_code', 
        'rakuten_item_number',
        'weight',
        'size_info'
    ]
    
    for field in important_fields:
        value = extended_info.get(field, '')
        if value:
            choice_info.append(f"{field}: {value}")
    
    return choice_info

def get_improvement_recommendations():
    """改善提案"""
    return {
        "immediate_actions": [
            {
                "action": "楽天API応答の完全ログ取得",
                "description": "selectedItems、variants、properties等の全情報をログ出力",
                "priority": "高"
            },
            {
                "action": "親子商品の適切な処理",
                "description": "itemType=1の親商品とselectedItemsの関係を正しく処理",
                "priority": "高"
            },
            {
                "action": "選択肢コード抽出ロジック実装",
                "description": "L01、M02等の選択肢コードを確実に抽出",
                "priority": "高"
            }
        ],
        "data_structure_improvements": [
            {
                "improvement": "order_itemsテーブル拡張",
                "description": "choice_code, parent_item_id, item_type等のカラム追加",
                "sql": """
                ALTER TABLE order_items ADD COLUMN choice_code VARCHAR(10);
                ALTER TABLE order_items ADD COLUMN parent_item_id INTEGER;
                ALTER TABLE order_items ADD COLUMN item_type INTEGER; -- 0:child, 1:parent
                ALTER TABLE order_items ADD COLUMN variant_id VARCHAR(50);
                """
            }
        ],
        "mapping_strategy_improvements": [
            {
                "strategy": "階層マッピング",
                "description": "親商品 → 選択肢コード → 共通コードの3段階マッピング",
                "example": "親商品:10000059 → 選択肢:L01 → 共通コード:CM042_L"
            },
            {
                "strategy": "選択肢別在庫管理",
                "description": "同一商品でもサイズ別に別在庫として管理",
                "example": "ふわふわサーモン15g(CM042_S) vs ふわふわサーモン30g(CM042_L)"
            }
        ]
    }

@app.get("/api/debug_rakuten_api_response")
async def debug_rakuten_api_response():
    """楽天API応答の詳細デバッグ情報"""
    try:
        if not supabase:
            return {"error": "Database connection not configured"}
        
        # 実際の楽天API応答をシミュレーション（デバッグ用）
        sample_api_response = {
            "OrderModelList": [
                {
                    "orderNumber": "338531-20250701-0014102294",
                    "PackageModelList": [
                        {
                            "ItemModelList": [
                                {
                                    "itemType": 1,  # 親商品
                                    "itemId": "10000059",
                                    "itemName": "ふわふわスモークサーモン【選択肢あり】",
                                    "units": 2,
                                    "price": 1600,
                                    "selectedItems": [  # ここが重要！
                                        {
                                            "choiceId": "L01",
                                            "itemId": "10000059-L01", 
                                            "itemName": "ふわふわスモークサーモン【L:30g】",
                                            "units": 1
                                        },
                                        {
                                            "choiceId": "M01",
                                            "itemId": "10000059-M01",
                                            "itemName": "ふわふわスモークサーモン【M:20g】", 
                                            "units": 1
                                        }
                                    ]
                                }
                            ]
                        }
                    ]
                }
            ]
        }
        
        return {
            "debug_info": "楽天API応答の想定構造",
            "sample_response": sample_api_response,
            "key_points": [
                "itemType=1が親商品を示す",
                "selectedItems配列に実際の選択された商品が入る",
                "choiceIdまたはchoiceCodeに選択肢コード（L01、M01等）が入る",
                "各選択肢商品には独自のitemIdが割り当てられる"
            ],
            "next_steps": [
                "実際の楽天API応答をログ出力して構造確認",
                "selectedItems処理ロジックの実装",
                "選択肢コード抽出機能の実装"
            ]
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