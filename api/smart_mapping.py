from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from datetime import datetime
import pytz
import os
from supabase import create_client, Client
from typing import Optional, List, Dict
import re

app = FastAPI()

# Supabase接続
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if SUPABASE_URL and SUPABASE_KEY:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
else:
    supabase = None

@app.get("/api/analyze_unmapped_products")
async def analyze_unmapped_products():
    """未マッピング商品を分析して自動マッピング候補を提案"""
    try:
        if not supabase:
            return {"error": "Database connection not configured"}
        
        # 未マッピング商品の詳細を取得
        unmapped_analysis = await get_unmapped_product_details()
        
        # 自動マッピング候補を生成
        mapping_suggestions = await generate_smart_mapping_suggestions(unmapped_analysis)
        
        return {
            "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat(),
            "unmapped_analysis": unmapped_analysis,
            "mapping_suggestions": mapping_suggestions,
            "auto_mapping_rules": get_smart_mapping_rules()
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

async def get_unmapped_product_details():
    """未マッピング商品の詳細情報を取得"""
    try:
        # 未マッピング商品の売上データ
        unmapped_sales = supabase.table('sales_master').select('common_code, quantity, total_amount').like('common_code', 'UNMAPPED_%').execute()
        
        # 商品コード別に集計
        product_analysis = {}
        
        if unmapped_sales.data:
            for sale in unmapped_sales.data:
                common_code = sale['common_code']
                product_code = common_code.replace('UNMAPPED_', '')
                
                if product_code not in product_analysis:
                    product_analysis[product_code] = {
                        'product_code': product_code,
                        'total_sales': 0,
                        'total_quantity': 0,
                        'order_count': 0
                    }
                
                product_analysis[product_code]['total_sales'] += float(sale.get('total_amount', 0))
                product_analysis[product_code]['total_quantity'] += int(sale.get('quantity', 0))
                product_analysis[product_code]['order_count'] += 1
        
        # 楽天の商品詳細情報を取得
        for product_code, analysis in product_analysis.items():
            product_details = await get_rakuten_product_details(product_code)
            analysis.update(product_details)
        
        # 売上順でソート
        sorted_analysis = sorted(product_analysis.values(), key=lambda x: x['total_sales'], reverse=True)
        
        return sorted_analysis[:20]  # 上位20商品
        
    except Exception as e:
        print(f"未マッピング商品分析エラー: {str(e)}")
        return []

async def get_rakuten_product_details(product_code: str):
    """楽天の商品詳細情報を取得"""
    try:
        # order_itemsから商品情報を取得
        product_info = supabase.table('order_items').select('product_name, price').eq('product_code', product_code).limit(1).execute()
        
        if product_info.data:
            product = product_info.data[0]
            return {
                'product_name': product.get('product_name', ''),
                'unit_price': float(product.get('price', 0))
            }
        else:
            return {
                'product_name': f'商品コード: {product_code}',
                'unit_price': 0
            }
            
    except Exception as e:
        return {
            'product_name': f'商品コード: {product_code}',
            'unit_price': 0
        }

async def generate_smart_mapping_suggestions(unmapped_analysis):
    """スマート自動マッピング候補を生成"""
    try:
        # 既存の商品マスターを取得
        product_masters = supabase.table('product_mapping_master').select('common_code, product_name').execute()
        master_products = product_masters.data if product_masters.data else []
        
        suggestions = []
        
        for product in unmapped_analysis:
            product_name = product.get('product_name', '')
            product_code = product.get('product_code', '')
            
            # 複数のマッピング手法を試行
            suggested_mappings = []
            
            # 1. 商品名キーワードマッチング
            keyword_match = find_keyword_match(product_name, master_products)
            if keyword_match:
                suggested_mappings.append({
                    'method': 'keyword_match',
                    'common_code': keyword_match['common_code'],
                    'master_name': keyword_match['product_name'],
                    'confidence': calculate_name_similarity(product_name, keyword_match['product_name'])
                })
            
            # 2. 商品コードパターンマッチング
            code_pattern_match = find_code_pattern_match(product_code)
            if code_pattern_match:
                suggested_mappings.append({
                    'method': 'code_pattern',
                    'common_code': code_pattern_match['common_code'],
                    'master_name': code_pattern_match['product_name'],
                    'confidence': code_pattern_match['confidence']
                })
            
            # 3. 価格帯マッチング
            price_match = find_price_match(product.get('unit_price', 0), master_products)
            if price_match:
                suggested_mappings.append({
                    'method': 'price_match',
                    'common_code': price_match['common_code'],
                    'master_name': price_match['product_name'],
                    'confidence': 0.3  # 価格マッチは信頼度低め
                })
            
            # 信頼度でソート
            suggested_mappings.sort(key=lambda x: x['confidence'], reverse=True)
            
            if suggested_mappings:
                suggestions.append({
                    'unmapped_product': product,
                    'best_suggestion': suggested_mappings[0],
                    'all_suggestions': suggested_mappings[:3]  # 上位3候補
                })
        
        return suggestions
        
    except Exception as e:
        print(f"マッピング候補生成エラー: {str(e)}")
        return []

def find_keyword_match(product_name: str, master_products: List[Dict]) -> Optional[Dict]:
    """商品名キーワードマッチング"""
    if not product_name:
        return None
    
    product_name_clean = clean_product_name(product_name)
    
    for master in master_products:
        master_name = master.get('product_name', '')
        master_name_clean = clean_product_name(master_name)
        
        # キーワード抽出
        product_keywords = extract_keywords(product_name_clean)
        master_keywords = extract_keywords(master_name_clean)
        
        # マッチング度計算
        match_score = calculate_keyword_match_score(product_keywords, master_keywords)
        
        if match_score > 0.6:  # 60%以上マッチ
            return master
    
    return None

def find_code_pattern_match(product_code: str) -> Optional[Dict]:
    """商品コードパターンマッチング"""
    # 既知のパターンルール
    code_patterns = {
        r'^10000059$': {'common_code': 'CM001', 'product_name': 'パターン商品1', 'confidence': 0.9},
        r'^10000301$': {'common_code': 'CM002', 'product_name': 'パターン商品2', 'confidence': 0.9},
        r'^10000\d{3}$': {'common_code': 'CM_SERIES', 'product_name': '10000シリーズ', 'confidence': 0.7},
        r'^TEST\d+$': {'common_code': 'TEST_PRODUCT', 'product_name': 'テスト商品', 'confidence': 0.8}
    }
    
    for pattern, mapping in code_patterns.items():
        if re.match(pattern, product_code):
            return mapping
    
    return None

def find_price_match(unit_price: float, master_products: List[Dict]) -> Optional[Dict]:
    """価格帯マッチング"""
    if unit_price <= 0:
        return None
    
    # 価格差±10%以内の商品を検索
    tolerance = 0.1
    
    for master in master_products:
        # 商品マスターから価格情報を取得（実装依存）
        # この例では簡易的に800円の商品を想定
        master_price = 800.0  # 実際は master.get('price', 0)
        
        if master_price > 0:
            price_diff = abs(unit_price - master_price) / master_price
            if price_diff <= tolerance:
                return master
    
    return None

def clean_product_name(name: str) -> str:
    """商品名のクリーニング"""
    if not name:
        return ""
    
    # 不要文字の除去
    cleaned = re.sub(r'[【】\[\]（）()・\s]+', '', name)
    cleaned = cleaned.lower()
    
    return cleaned

def extract_keywords(name: str) -> List[str]:
    """商品名からキーワードを抽出"""
    if not name:
        return []
    
    # 重要キーワードの定義
    important_keywords = [
        'サーモン', 'スモーク', 'ふわふわ', 'チップ',
        'コーン', 'フレーク', 'にんじん', 'ちび',
        'レトルト', 'おやつ', 'トリーツ'
    ]
    
    found_keywords = []
    for keyword in important_keywords:
        if keyword.lower() in name.lower():
            found_keywords.append(keyword)
    
    return found_keywords

def calculate_keyword_match_score(keywords1: List[str], keywords2: List[str]) -> float:
    """キーワードマッチスコア計算"""
    if not keywords1 or not keywords2:
        return 0.0
    
    matches = len(set(keywords1) & set(keywords2))
    total_unique = len(set(keywords1) | set(keywords2))
    
    return matches / total_unique if total_unique > 0 else 0.0

def calculate_name_similarity(name1: str, name2: str) -> float:
    """商品名類似度計算（簡易版）"""
    if not name1 or not name2:
        return 0.0
    
    clean1 = clean_product_name(name1)
    clean2 = clean_product_name(name2)
    
    # 共通文字数による類似度
    common_chars = len(set(clean1) & set(clean2))
    total_chars = len(set(clean1) | set(clean2))
    
    return common_chars / total_chars if total_chars > 0 else 0.0

def get_smart_mapping_rules():
    """スマートマッピングルールの説明"""
    return {
        "keyword_matching": {
            "description": "商品名のキーワードマッチング",
            "keywords": ["サーモン", "スモーク", "ふわふわ", "チップ", "コーン", "フレーク", "にんじん"],
            "threshold": 0.6
        },
        "code_pattern_matching": {
            "description": "商品コードパターンマッチング",
            "patterns": ["10000xxx系", "TESTxxx系"],
            "confidence": "high"
        },
        "price_matching": {
            "description": "価格帯マッチング",
            "tolerance": "±10%",
            "confidence": "low"
        }
    }

@app.post("/api/apply_smart_mapping")
async def apply_smart_mapping(
    auto_apply: Optional[bool] = Query(False, description="高信頼度マッピングを自動適用")
):
    """スマートマッピングを適用"""
    try:
        if not supabase:
            return {"error": "Database connection not configured"}
        
        # マッピング候補を取得
        analysis_result = await analyze_unmapped_products()
        suggestions = analysis_result.get("mapping_suggestions", [])
        
        applied_mappings = []
        high_confidence_threshold = 0.8
        
        for suggestion in suggestions:
            best_suggestion = suggestion.get("best_suggestion", {})
            confidence = best_suggestion.get("confidence", 0)
            
            if auto_apply and confidence >= high_confidence_threshold:
                # 高信頼度の場合は自動適用
                product_code = suggestion["unmapped_product"]["product_code"]
                common_code = best_suggestion["common_code"]
                product_name = suggestion["unmapped_product"]["product_name"]
                
                # platform_product_mappingに追加
                mapping_result = await add_product_mapping_internal(
                    'rakuten', product_code, common_code, product_name
                )
                
                if mapping_result.get("status") == "success":
                    applied_mappings.append({
                        "product_code": product_code,
                        "common_code": common_code,
                        "confidence": confidence,
                        "method": best_suggestion["method"]
                    })
        
        return {
            "status": "success",
            "total_suggestions": len(suggestions),
            "applied_mappings": applied_mappings,
            "manual_review_needed": len(suggestions) - len(applied_mappings),
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

async def add_product_mapping_internal(platform_name: str, product_code: str, common_code: str, product_name: str):
    """内部用：商品マッピング追加"""
    try:
        # 重複チェック
        existing = supabase.table('platform_product_mapping').select('id').eq('platform_name', platform_name).eq('platform_product_code', product_code).execute()
        
        if existing.data:
            # 既存の場合は更新
            result = supabase.table('platform_product_mapping').update({
                'common_code': common_code,
                'platform_product_name': product_name,
                'updated_at': datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
            }).eq('platform_name', platform_name).eq('platform_product_code', product_code).execute()
            
            return {"status": "success", "action": "updated"}
        else:
            # 新規追加
            result = supabase.table('platform_product_mapping').insert({
                'platform_name': platform_name,
                'platform_product_code': product_code,
                'common_code': common_code,
                'platform_product_name': product_name,
                'is_active': True
            }).execute()
            
            return {"status": "success", "action": "added"}
            
    except Exception as e:
        return {"status": "error", "message": str(e)}