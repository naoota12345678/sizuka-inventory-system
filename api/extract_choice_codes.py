from fastapi import FastAPI
from fastapi.responses import JSONResponse
from datetime import datetime
import pytz
import os
from supabase import create_client, Client
import re
from typing import Dict, List, Optional

app = FastAPI()

# Supabase接続
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if SUPABASE_URL and SUPABASE_KEY:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
else:
    supabase = None

@app.get("/api/extract_choice_codes")
async def extract_choice_codes():
    """既存のorder_itemsから選択肢コードを抽出・分析"""
    try:
        if not supabase:
            return {"error": "Database connection not configured"}
        
        # 既存のorder_itemsデータを取得
        order_items = supabase.table('order_items').select('*').execute()
        
        if not order_items.data:
            return {"error": "order_itemsデータが見つかりません"}
        
        analysis_results = {
            "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat(),
            "total_items": len(order_items.data),
            "choice_code_analysis": {},
            "extracted_patterns": [],
            "update_candidates": [],
            "recommendations": []
        }
        
        choice_code_patterns = {}
        extracted_codes = []
        update_candidates = []
        
        for item in order_items.data:
            item_id = item.get('id')
            product_name = item.get('product_name', '')
            product_code = item.get('product_code', '')
            
            # 商品名から選択肢コードを抽出
            choice_codes = extract_choice_codes_from_text(product_name)
            
            # 商品コードからも抽出を試行
            if not choice_codes:
                choice_codes = extract_choice_codes_from_text(product_code)
            
            if choice_codes:
                extracted_codes.extend(choice_codes)
                
                # パターン分析用
                for code in choice_codes:
                    if code not in choice_code_patterns:
                        choice_code_patterns[code] = []
                    choice_code_patterns[code].append({
                        "item_id": item_id,
                        "product_name": product_name[:100],
                        "product_code": product_code
                    })
                
                # 更新候補に追加
                update_candidates.append({
                    "item_id": item_id,
                    "product_code": product_code,
                    "product_name": product_name[:100],
                    "extracted_choice_codes": choice_codes,
                    "primary_choice_code": choice_codes[0] if choice_codes else None
                })
        
        analysis_results["choice_code_analysis"] = choice_code_patterns
        analysis_results["extracted_patterns"] = list(set(extracted_codes))
        analysis_results["update_candidates"] = update_candidates
        
        # 推奨事項
        recommendations = []
        
        if update_candidates:
            recommendations.append(
                f"{len(update_candidates)}件の商品から選択肢コードを抽出できました。"
                "choice_codeカラムの更新を推奨します。"
            )
        
        if len(set(extracted_codes)) > 0:
            recommendations.append(
                f"{len(set(extracted_codes))}種類の選択肢コードパターンを発見しました。"
                "商品マスターとの照合を推奨します。"
            )
        
        # 一般的なパターン分析
        common_patterns = analyze_common_patterns(extracted_codes)
        if common_patterns:
            recommendations.append(
                f"一般的なパターン: {', '.join(common_patterns[:5])}"
            )
        
        analysis_results["recommendations"] = recommendations
        
        return analysis_results
        
    except Exception as e:
        return JSONResponse(
            status_code=200,
            content={
                "status": "error",
                "message": str(e),
                "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
            }
        )

@app.post("/api/update_choice_codes")
async def update_choice_codes():
    """抽出した選択肢コードでorder_itemsテーブルを更新"""
    try:
        if not supabase:
            return {"error": "Database connection not configured"}
        
        # choice_codeカラムの存在確認
        try:
            test_query = supabase.table('order_items').select('choice_code').limit(1).execute()
        except:
            return {
                "status": "error",
                "message": "choice_codeカラムが存在しません。先にテーブル拡張SQLを実行してください。",
                "sql": """
ALTER TABLE order_items ADD COLUMN choice_code VARCHAR(10);
ALTER TABLE order_items ADD COLUMN parent_item_id INTEGER;
ALTER TABLE order_items ADD COLUMN item_type INTEGER DEFAULT 0;
"""
            }
        
        # 選択肢コード抽出結果を取得
        extraction_result = await extract_choice_codes()
        update_candidates = extraction_result.get("update_candidates", [])
        
        if not update_candidates:
            return {
                "status": "warning",
                "message": "更新対象の選択肢コードが見つかりませんでした"
            }
        
        updated_count = 0
        error_count = 0
        
        for candidate in update_candidates:
            item_id = candidate["item_id"]
            primary_choice_code = candidate["primary_choice_code"]
            
            if primary_choice_code:
                try:
                    # choice_codeカラムを更新
                    supabase.table('order_items').update({
                        'choice_code': primary_choice_code
                    }).eq('id', item_id).execute()
                    
                    updated_count += 1
                    
                except Exception as e:
                    error_count += 1
                    print(f"更新エラー (ID: {item_id}): {str(e)}")
        
        return {
            "status": "success",
            "message": f"選択肢コード更新完了: {updated_count}件更新、{error_count}件エラー",
            "updated_count": updated_count,
            "error_count": error_count,
            "total_candidates": len(update_candidates),
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

def extract_choice_codes_from_text(text: str) -> List[str]:
    """テキストから選択肢コードを抽出"""
    if not text:
        return []
    
    choice_codes = []
    
    # パターン1: 【L01】【M02】【S03】形式
    pattern1 = r'【([LMS]\d*)】'
    matches = re.findall(pattern1, text, re.IGNORECASE)
    choice_codes.extend(matches)
    
    # パターン2: [L01][M02][S03]形式
    pattern2 = r'\[([LMS]\d*)\]'
    matches = re.findall(pattern2, text, re.IGNORECASE)
    choice_codes.extend(matches)
    
    # パターン3: (L01)(M02)(S03)形式
    pattern3 = r'\(([LMS]\d*)\)'
    matches = re.findall(pattern3, text, re.IGNORECASE)
    choice_codes.extend(matches)
    
    # パターン4: L01 M02 S03（スペース区切り）
    pattern4 = r'\b([LMS]\d+)\b'
    matches = re.findall(pattern4, text, re.IGNORECASE)
    choice_codes.extend(matches)
    
    # パターン5: サイズ表記
    size_patterns = [
        r'サイズ[:：]?\s*([LMS])',
        r'SIZE[:：]?\s*([LMS])',
        r'([LMS])サイズ'
    ]
    
    for pattern in size_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        choice_codes.extend(matches)
    
    # パターン6: 数値表記（15g、30g等）
    weight_pattern = r'(\d+)g|\d+グラム|\d+ｇ'
    weight_matches = re.findall(weight_pattern, text, re.IGNORECASE)
    
    # 重量を選択肢コードに変換
    for weight in weight_matches:
        if weight == '15':
            choice_codes.append('S01')  # 小サイズ
        elif weight == '30':
            choice_codes.append('L01')  # 大サイズ
        elif weight == '20':
            choice_codes.append('M01')  # 中サイズ
    
    # パターン7: 小中大表記
    size_mapping = {
        '小': 'S01',
        '中': 'M01', 
        '大': 'L01',
        '特大': 'XL01'
    }
    
    for size, code in size_mapping.items():
        if size in text:
            choice_codes.append(code)
    
    # 重複除去して大文字に統一
    unique_codes = list(set(code.upper() for code in choice_codes if code))
    
    return unique_codes

def analyze_common_patterns(codes: List[str]) -> List[str]:
    """一般的なパターンを分析"""
    if not codes:
        return []
    
    # 頻度分析
    from collections import Counter
    counter = Counter(codes)
    
    # 上位パターンを返す
    common_patterns = [code for code, count in counter.most_common(10)]
    
    return common_patterns

@app.get("/api/choice_code_mapping_suggestions")
async def choice_code_mapping_suggestions():
    """選択肢コードと商品マスターのマッピング提案"""
    try:
        if not supabase:
            return {"error": "Database connection not configured"}
        
        # 選択肢コード付きの商品を取得
        items_with_codes = supabase.table('order_items').select('product_code, product_name, choice_code').not_.is_('choice_code', 'null').execute()
        
        # 商品マスターを取得
        product_masters = supabase.table('product_mapping_master').select('*').execute()
        
        mapping_suggestions = []
        
        if items_with_codes.data and product_masters.data:
            for item in items_with_codes.data:
                product_code = item['product_code']
                choice_code = item['choice_code']
                product_name = item['product_name']
                
                # 対応する商品マスターを検索
                for master in product_masters.data:
                    master_name = master['product_name']
                    
                    # 商品名の類似性チェック
                    if calculate_similarity(product_name, master_name) > 0.6:
                        suggested_common_code = f"{master['common_code']}_{choice_code}"
                        
                        mapping_suggestions.append({
                            "rakuten_product_code": product_code,
                            "choice_code": choice_code,
                            "rakuten_product_name": product_name[:100],
                            "master_common_code": master['common_code'],
                            "master_product_name": master_name,
                            "suggested_final_code": suggested_common_code,
                            "similarity_score": calculate_similarity(product_name, master_name)
                        })
        
        return {
            "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat(),
            "mapping_suggestions": mapping_suggestions[:20],  # 上位20件
            "total_suggestions": len(mapping_suggestions)
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

def calculate_similarity(text1: str, text2: str) -> float:
    """テキスト類似度計算（簡易版）"""
    if not text1 or not text2:
        return 0.0
    
    # 共通キーワード数による類似度
    words1 = set(text1.lower().split())
    words2 = set(text2.lower().split())
    
    intersection = words1.intersection(words2)
    union = words1.union(words2)
    
    return len(intersection) / len(union) if union else 0.0