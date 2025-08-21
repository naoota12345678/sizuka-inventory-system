#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
楽天注文データの日次確定処理
1. Google Sheetsと同期
2. その日の楽天注文データを処理
3. 在庫変動を確定
"""

from supabase import create_client
from datetime import datetime, timezone, timedelta
import re
import logging
from google_sheets_sync import daily_sync

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SUPABASE_URL = "https://equrcpeifogdrxoldkpe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ"

def extract_choice_codes(choice_code_text):
    """選択肢コードからR05, N03等を抽出"""
    if not choice_code_text:
        return []
    
    pattern = r'[A-Z]\d{2}'
    matches = re.findall(pattern, choice_code_text)
    
    # 重複除去しつつ順序保持
    seen = set()
    result = []
    for match in matches:
        if match not in seen:
            seen.add(match)
            result.append(match)
    
    return result

def get_mapping_for_choice_codes(choice_codes, supabase):
    """選択肢コードのマッピング情報を取得"""
    mappings = []
    
    for code in choice_codes:
        try:
            # choice_info.choice_code でJSONB検索
            result = supabase.table("choice_code_mapping").select("*").contains("choice_info", {"choice_code": code}).execute()
            
            if result.data:
                mapping = result.data[0]
                mappings.append({
                    "choice_code": code,
                    "common_code": mapping["common_code"],
                    "product_name": mapping["product_name"],
                    "mapping_found": True
                })
            else:
                mappings.append({
                    "choice_code": code,
                    "common_code": None,
                    "product_name": None,
                    "mapping_found": False
                })
        except Exception as e:
            logger.error(f"Mapping error for {code}: {str(e)}")
            mappings.append({
                "choice_code": code,
                "common_code": None,
                "product_name": None,
                "mapping_found": False,
                "error": str(e)
            })
    
    return mappings

def process_order_item(item, supabase):
    """個別の注文アイテムを処理"""
    choice_code = item.get('choice_code', '')
    if not choice_code:
        return {
            "status": "skipped",
            "reason": "No choice code",
            "inventory_changes": []
        }
    
    # 選択肢コード抽出
    extracted_codes = extract_choice_codes(choice_code)
    if not extracted_codes:
        return {
            "status": "skipped", 
            "reason": "No choice codes extracted",
            "inventory_changes": []
        }
    
    # マッピング取得
    mappings = get_mapping_for_choice_codes(extracted_codes, supabase)
    
    # 在庫変動計算
    inventory_changes = []
    unmapped_codes = []
    
    for mapping in mappings:
        if mapping["mapping_found"]:
            inventory_changes.append({
                "choice_code": mapping["choice_code"],
                "common_code": mapping["common_code"],
                "product_name": mapping["product_name"],
                "quantity_to_reduce": item['quantity'],
                "order_item_id": item['id'],
                "order_id": item['order_id']
            })
        else:
            unmapped_codes.append(mapping["choice_code"])
    
    status = "success" if inventory_changes else "no_mappings"
    if unmapped_codes:
        status = "partial_mapping" if inventory_changes else "no_mappings"
    
    return {
        "status": status,
        "extracted_codes": extracted_codes,
        "inventory_changes": inventory_changes,
        "unmapped_codes": unmapped_codes
    }

def create_unprocessed_sales_record(item, unmapped_codes, supabase):
    """未処理売上データを記録"""
    try:
        unprocessed_data = {
            "order_item_id": item['id'],
            "order_id": item['order_id'],
            "product_code": item['product_code'],
            "product_name": item['product_name'],
            "quantity": item['quantity'],
            "choice_code_text": item.get('choice_code', ''),
            "unmapped_codes": unmapped_codes,
            "status": "unprocessed",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        # unprocessed_sales_itemsテーブルに挿入（テーブルが存在しない場合は作成が必要）
        result = supabase.table("unprocessed_sales_items").insert(unprocessed_data).execute()
        
        if result.data:
            logger.info(f"   Recorded unprocessed item: Order {item['id']}")
            return True
        else:
            logger.error(f"   Failed to record unprocessed item: Order {item['id']}")
            return False
            
    except Exception as e:
        logger.error(f"Error recording unprocessed item {item['id']}: {str(e)}")
        return False

def process_daily_orders(target_date=None):
    """指定日の楽天注文データを処理（デフォルトは前日）"""
    if target_date is None:
        # 前日の売上データを処理（現実的なアプローチ）
        target_date = (datetime.now() - timedelta(days=1)).date()
    
    logger.info(f"=== Processing Rakuten Orders for {target_date} ===")
    
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # 指定日の楽天注文アイテムのみを取得（platform_id=1）
    start_datetime = datetime.combine(target_date, datetime.min.time()).replace(tzinfo=timezone.utc)
    end_datetime = start_datetime + timedelta(days=1)
    
    # 楽天プラットフォーム（platform_id=1）のorder_itemsのみ取得
    orders = supabase.table("order_items").select("*, orders!inner(platform_id)").eq("orders.platform_id", 1).gte("created_at", start_datetime.isoformat()).lt("created_at", end_datetime.isoformat()).execute()
    
    if not orders.data:
        logger.info(f"No order items found for {target_date}")
        return {
            "date": target_date,
            "total_items": 0,
            "processed_items": 0,
            "inventory_changes": [],
            "unprocessed_items": 0
        }
    
    logger.info(f"Found {len(orders.data)} order items for {target_date}")
    
    # 各注文アイテムを処理
    total_inventory_changes = []
    unprocessed_count = 0
    processed_count = 0
    
    for item in orders.data:
        logger.info(f"Processing order item {item['id']}: {item['product_code']}")
        
        result = process_order_item(item, supabase)
        
        if result["status"] == "success":
            total_inventory_changes.extend(result["inventory_changes"])
            processed_count += 1
            logger.info(f"   ✓ Processed: {len(result['inventory_changes'])} inventory changes")
            
        elif result["status"] == "partial_mapping":
            total_inventory_changes.extend(result["inventory_changes"])
            # 未マッピングコードを記録
            create_unprocessed_sales_record(item, result["unmapped_codes"], supabase)
            processed_count += 1
            unprocessed_count += 1
            logger.warning(f"   ⚠ Partial mapping: {len(result['inventory_changes'])} changes, {len(result['unmapped_codes'])} unmapped")
            
        elif result["status"] == "no_mappings":
            # 完全に未処理
            create_unprocessed_sales_record(item, result.get("extracted_codes", []), supabase)
            unprocessed_count += 1
            logger.warning(f"   ✗ No mappings found")
            
        else:
            logger.info(f"   - Skipped: {result['reason']}")
    
    # 在庫変動の集計
    inventory_summary = {}
    for change in total_inventory_changes:
        common_code = change["common_code"]
        if common_code in inventory_summary:
            inventory_summary[common_code] += change["quantity_to_reduce"]
        else:
            inventory_summary[common_code] = change["quantity_to_reduce"]
    
    logger.info(f"=== Daily Processing Summary for {target_date} ===")
    logger.info(f"Total items: {len(orders.data)}")
    logger.info(f"Processed items: {processed_count}")
    logger.info(f"Unprocessed items: {unprocessed_count}")
    logger.info(f"Inventory changes: {len(inventory_summary)} products")
    
    for common_code, total_qty in inventory_summary.items():
        logger.info(f"  - {common_code}: -{total_qty} units")
    
    return {
        "date": target_date,
        "total_items": len(orders.data),
        "processed_items": processed_count,
        "unprocessed_items": unprocessed_count,
        "inventory_changes": total_inventory_changes,
        "inventory_summary": inventory_summary
    }

def daily_processing():
    """1日1回の完全処理"""
    logger.info(f"=== Daily Rakuten Processing Started at {datetime.now()} ===")
    
    try:
        # 1. Google Sheetsと同期
        logger.info("Step 1: Syncing with Google Sheets")
        sync_success = daily_sync()
        
        if not sync_success:
            logger.error("Google Sheets sync failed - continuing with existing mappings")
        
        # 2. 楽天注文データの処理
        logger.info("Step 2: Processing Rakuten orders")
        processing_result = process_daily_orders()
        
        # 3. 結果レポート
        logger.info("=== Daily Processing Completed ===")
        logger.info(f"Google Sheets sync: {'✓' if sync_success else '✗'}")
        logger.info(f"Orders processed: {processing_result['processed_items']}/{processing_result['total_items']}")
        logger.info(f"Unprocessed items: {processing_result['unprocessed_items']}")
        logger.info(f"Inventory changes: {len(processing_result['inventory_summary'])} products")
        
        return {
            "sync_success": sync_success,
            "processing_result": processing_result,
            "overall_success": sync_success and processing_result['processed_items'] > 0
        }
        
    except Exception as e:
        logger.error(f"Daily processing failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "sync_success": False,
            "processing_result": None,
            "overall_success": False,
            "error": str(e)
        }

if __name__ == "__main__":
    result = daily_processing()
    
    if result["overall_success"]:
        print("Daily processing completed successfully")
    else:
        print("Daily processing completed with errors")
        if result.get("error"):
            print(f"Error: {result['error']}")