#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
スマレジID（製造商品）マッピング同期
商品番号マッピング基本表からスマレジID→共通コードを取得してproduct_masterに同期
"""

import requests
import csv
from io import StringIO
from supabase import create_client
from datetime import datetime, timezone
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SUPABASE_URL = "https://equrcpeifogdrxoldkpe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ"

SPREADSHEET_ID = "1mLg1N0a1wubEIdKSouiW_jDaWUnuFLBxj8greczuS3E"
MAPPING_GID = "1290908701"  # 商品番号マッピング基本表

def get_mapping_from_sheets():
    """Google Sheetsから商品番号マッピング基本表を取得"""
    try:
        csv_url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid={MAPPING_GID}"
        
        logger.info("商品番号マッピング基本表をダウンロード中...")
        response = requests.get(csv_url, timeout=30)
        response.raise_for_status()
        
        # CSVパース
        csv_data = StringIO(response.text)
        reader = csv.DictReader(csv_data)
        data = list(reader)
        
        logger.info(f"マッピングデータ取得成功: {len(data)}行")
        
        if data:
            logger.info("利用可能な列:")
            for col in data[0].keys():
                logger.info(f"  - {repr(col)}")
        
        return data
        
    except Exception as e:
        logger.error(f"データ取得エラー: {str(e)}")
        return None

def find_smaregi_mappings(data):
    """スマレジID（10XXX）のマッピングを抽出"""
    if not data:
        return []
    
    smaregi_mappings = []
    
    # 列名を自動検出
    columns = list(data[0].keys())
    smaregi_column = None
    common_code_column = None
    product_name_column = None
    
    # スマレジID列を探す
    for col in columns:
        if any(keyword in col.lower() for keyword in ['スマレジ', 'smaregi', 'smartregi']):
            smaregi_column = col
            logger.info(f"スマレジID列を検出: {col}")
            break
        elif any(keyword in col for keyword in ['10', 'ID']):
            # 数値やIDを含む列をチェック
            sample_values = [row.get(col, '') for row in data[:5] if row.get(col)]
            if any(str(val).startswith('10') and len(str(val)) >= 5 for val in sample_values):
                smaregi_column = col
                logger.info(f"スマレジID列を推定: {col}")
                break
    
    # 共通コード列を探す
    for col in columns:
        # 日本語の文字化けした列名も考慮
        col_lower = col.lower()
        if any(keyword in col_lower for keyword in ['common', 'cm', 'sizuka']) or '共通' in col or 'コード' in col:
            common_code_column = col
            logger.info(f"共通コード列を検出: {col}")
            break
    
    # 見つからない場合、データ内容で推定
    if not common_code_column:
        logger.info("列名で見つからないため、データ内容で推定します")
        for col in columns:
            sample_values = [str(row.get(col, '')) for row in data[:10] if row.get(col)]
            if sample_values:
                # CM### 形式やアルファベット+数字の組み合わせをチェック
                code_count = sum(1 for val in sample_values if val.startswith(('CM', 'S', 'C', 'B', 'P', 'N')) and len(val) >= 2)
                if code_count >= 3:
                    common_code_column = col
                    logger.info(f"共通コード列を推定: {col}")
                    break
    
    # 商品名列を探す
    for col in columns:
        if any(keyword in col for keyword in ['商品名', 'name', '名前', '商品']):
            product_name_column = col
            logger.info(f"商品名列を検出: {col}")
            break
    
    if not smaregi_column or not common_code_column:
        logger.error("必要な列が見つかりません")
        logger.info("利用可能な列:")
        for col in columns:
            logger.info(f"  - {col}")
        return []
    
    logger.info(f"データ処理開始: {len(data)}行")
    
    for row_index, row in enumerate(data, start=1):
        smaregi_id = str(row.get(smaregi_column, '')).strip()
        common_code = str(row.get(common_code_column, '')).strip()
        product_name = str(row.get(product_name_column, '')).strip() if product_name_column else ''
        
        # スマレジID（10XXX形式）をチェック
        if smaregi_id and smaregi_id.startswith('10') and len(smaregi_id) >= 5 and common_code:
            smaregi_mappings.append({
                'smaregi_id': smaregi_id,
                'common_code': common_code,
                'product_name': product_name or f"スマレジ商品_{smaregi_id}",
                'row_index': row_index
            })
            
            if len(smaregi_mappings) <= 10:  # 最初の10件をログ出力
                logger.info(f"  {smaregi_id} → {common_code} ({product_name[:30]}...)")
    
    logger.info(f"スマレジマッピング抽出完了: {len(smaregi_mappings)}件")
    return smaregi_mappings

def sync_smaregi_to_product_master(mappings):
    """スマレジマッピングをproduct_masterに同期"""
    if not mappings:
        return {"status": "no_data", "message": "マッピングデータがありません"}
    
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    results = {
        "total_mappings": len(mappings),
        "successful_updates": 0,
        "failed_updates": 0,
        "created_new": 0,
        "updated_existing": 0,
        "details": []
    }
    
    logger.info(f"product_master同期開始: {len(mappings)}件")
    
    for mapping in mappings:
        smaregi_id = mapping['smaregi_id']
        common_code = mapping['common_code']
        product_name = mapping['product_name']
        
        try:
            # 既存レコードをチェック
            existing = supabase.table("product_master").select("id").eq("rakuten_sku", smaregi_id).execute()
            
            mapping_data = {
                "common_code": common_code,
                "rakuten_sku": smaregi_id,  # スマレジIDをrakuten_skuとして保存
                "product_name": product_name,
                "product_type": "smaregi",  # スマレジ商品として分類
                "is_active": True,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            
            if existing.data:
                # 更新
                result = supabase.table("product_master").update(mapping_data).eq("rakuten_sku", smaregi_id).execute()
                
                if result.data:
                    results["successful_updates"] += 1
                    results["updated_existing"] += 1
                    logger.info(f"  更新: {smaregi_id} → {common_code}")
                    
                    results["details"].append({
                        "smaregi_id": smaregi_id,
                        "common_code": common_code,
                        "action": "updated"
                    })
                else:
                    results["failed_updates"] += 1
                    logger.error(f"  更新失敗: {smaregi_id}")
            else:
                # 新規作成
                mapping_data["created_at"] = datetime.now(timezone.utc).isoformat()
                result = supabase.table("product_master").insert(mapping_data).execute()
                
                if result.data:
                    results["successful_updates"] += 1
                    results["created_new"] += 1
                    logger.info(f"  新規: {smaregi_id} → {common_code}")
                    
                    results["details"].append({
                        "smaregi_id": smaregi_id,
                        "common_code": common_code,
                        "action": "created"
                    })
                else:
                    results["failed_updates"] += 1
                    logger.error(f"  新規作成失敗: {smaregi_id}")
        
        except Exception as e:
            results["failed_updates"] += 1
            logger.error(f"  エラー ({smaregi_id}): {str(e)}")
    
    # 成功率計算
    success_rate = (results["successful_updates"] / results["total_mappings"] * 100) if results["total_mappings"] > 0 else 0
    results["success_rate"] = f"{success_rate:.1f}%"
    
    return {
        "status": "success",
        "message": f"スマレジマッピング同期完了: {results['successful_updates']}/{results['total_mappings']} 成功",
        "results": results
    }

def main():
    """メイン実行関数"""
    try:
        print("=== スマレジID マッピング同期システム ===")
        print("商品番号マッピング基本表からスマレジID→共通コードを取得してproduct_masterに同期します")
        
        # 1. Google Sheetsからマッピングデータ取得
        sheets_data = get_mapping_from_sheets()
        if not sheets_data:
            print("マッピングデータの取得に失敗しました")
            return
        
        # 2. スマレジマッピングを抽出
        smaregi_mappings = find_smaregi_mappings(sheets_data)
        if not smaregi_mappings:
            print("スマレジマッピングが見つかりませんでした")
            return
        
        # 3. product_masterに同期
        result = sync_smaregi_to_product_master(smaregi_mappings)
        
        print(f"\n=== 同期結果 ===")
        print(f"ステータス: {result['status']}")
        print(f"メッセージ: {result['message']}")
        
        if result['status'] == 'success' and 'results' in result:
            results = result['results']
            print(f"\n詳細結果:")
            print(f"  総マッピング数: {results['total_mappings']}")
            print(f"  成功: {results['successful_updates']}")
            print(f"  失敗: {results['failed_updates']}")
            print(f"  新規作成: {results['created_new']}")
            print(f"  既存更新: {results['updated_existing']}")
            print(f"  成功率: {results['success_rate']}")
        
        print("\n同期完了！")
        
    except Exception as e:
        print(f"エラーが発生しました: {str(e)}")

if __name__ == "__main__":
    main()