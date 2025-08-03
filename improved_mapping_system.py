#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
改良されたマッピングシステム
1. 楽天API → 楽天商品在庫変動データ作成
2. 選択肢コード抽出 → 単品在庫変動
3. まとめ商品処理 → 構成品在庫変動
4. 総合在庫から減算

シンプルで分かりやすい流れに改良
"""

from supabase import create_client
from datetime import datetime, timezone
import re
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SUPABASE_URL = "https://equrcpeifogdrxoldkpe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ"

class InventoryMappingSystem:
    def __init__(self):
        self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    def step1_extract_rakuten_sales(self, target_date=None):
        """ステップ1: 楽天注文データから在庫変動データを作成"""
        logger.info("=== ステップ1: 楽天注文データ抽出 ===")
        
        if target_date is None:
            target_date = datetime.now().date()
        
        # その日の楽天注文データを取得
        orders = self.supabase.table("order_items").select("*").gte("created_at", f"{target_date}T00:00:00").lt("created_at", f"{target_date}T23:59:59").execute()
        
        rakuten_sales = []
        
        for order in orders.data:
            choice_code = order.get('choice_code', '')
            
            if choice_code:
                # 選択肢コードがある場合：各選択肢を個別商品として扱う
                extracted_codes = self._extract_choice_codes(choice_code)
                
                for code in extracted_codes:
                    rakuten_sales.append({
                        "type": "choice_item",
                        "rakuten_code": code,
                        "quantity": order['quantity'],
                        "order_item_id": order['id'],
                        "product_name": f"選択肢商品 {code}",
                        "source": "楽天選択肢"
                    })
            else:
                # 通常商品の場合：楽天SKU（rakuten_item_number）で処理
                rakuten_sku = order.get('rakuten_item_number', '') or order.get('product_code', '')
                rakuten_sales.append({
                    "type": "normal_item", 
                    "rakuten_code": rakuten_sku,
                    "quantity": order['quantity'],
                    "order_item_id": order['id'],
                    "product_name": order['product_name'],
                    "source": "楽天通常商品",
                    "fallback_product_code": order['product_code']  # フォールバック用
                })
        
        logger.info(f"楽天商品在庫変動データ: {len(rakuten_sales)}件")
        return rakuten_sales
    
    def step2_map_to_common_codes(self, rakuten_sales):
        """ステップ2: 楽天商品を共通コードにマッピング"""
        logger.info("=== ステップ2: 共通コードマッピング ===")
        
        mapped_items = []
        unmapped_items = []
        
        for item in rakuten_sales:
            if item["type"] == "choice_item":
                # 選択肢コードのマッピング
                mapping = self._find_choice_code_mapping(item["rakuten_code"])
                if mapping:
                    mapped_items.append({
                        "common_code": mapping["common_code"],
                        "quantity": item["quantity"],
                        "item_type": "単品",
                        "source_item": item,
                        "product_name": mapping["product_name"]
                    })
                else:
                    unmapped_items.append(item)
            else:
                # 通常商品のマッピング（楽天SKUベース）
                fallback_code = item.get("fallback_product_code")
                mapping = self._find_normal_product_mapping(item["rakuten_code"], fallback_code)
                if mapping:
                    mapped_items.append({
                        "common_code": mapping["common_code"],
                        "quantity": item["quantity"], 
                        "item_type": mapping.get("product_type", "単品"),
                        "source_item": item,
                        "product_name": mapping["product_name"]
                    })
                else:
                    unmapped_items.append(item)
        
        logger.info(f"マッピング成功: {len(mapped_items)}件")
        logger.info(f"マッピング失敗: {len(unmapped_items)}件")
        
        return mapped_items, unmapped_items
    
    def step3_process_bundle_products(self, mapped_items):
        """ステップ3: まとめ商品の構成品処理"""
        logger.info("=== ステップ3: まとめ商品処理 ===")
        
        final_inventory_changes = []
        
        for item in mapped_items:
            if item["item_type"] in ["まとめ(固定)", "まとめ(複合)", "セット(固定)", "セット(選択)"]:
                # まとめ商品の場合：構成品を取得
                components = self._get_bundle_components(item["common_code"])
                
                if components:
                    logger.info(f"まとめ商品 {item['common_code']} の構成品: {len(components)}件")
                    
                    for component in components:
                        final_inventory_changes.append({
                            "common_code": component["component_code"],
                            "quantity_to_reduce": item["quantity"] * component.get("quantity", 1),
                            "reason": f"まとめ商品 {item['common_code']} 売上",
                            "source_type": "まとめ商品構成品",
                            "parent_product": item["common_code"]
                        })
                else:
                    # 構成品が見つからない場合はそのまま処理
                    final_inventory_changes.append({
                        "common_code": item["common_code"],
                        "quantity_to_reduce": item["quantity"],
                        "reason": "まとめ商品（構成品未定義）",
                        "source_type": "まとめ商品",
                        "parent_product": None
                    })
            else:
                # 単品の場合：そのまま在庫変動
                final_inventory_changes.append({
                    "common_code": item["common_code"],
                    "quantity_to_reduce": item["quantity"],
                    "reason": "楽天単品売上",
                    "source_type": "単品",
                    "parent_product": None
                })
        
        # 同じ共通コードの在庫変動を集計
        consolidated_changes = {}
        for change in final_inventory_changes:
            code = change["common_code"]
            if code in consolidated_changes:
                consolidated_changes[code]["quantity_to_reduce"] += change["quantity_to_reduce"]
                consolidated_changes[code]["reasons"].append(change["reason"])
            else:
                consolidated_changes[code] = {
                    "common_code": code,
                    "quantity_to_reduce": change["quantity_to_reduce"],
                    "reasons": [change["reason"]],
                    "source_types": [change["source_type"]]
                }
        
        logger.info(f"最終在庫変動: {len(consolidated_changes)}商品")
        return list(consolidated_changes.values())
    
    def step4_apply_inventory_changes(self, inventory_changes, dry_run=True):
        """ステップ4: 総合在庫から減算"""
        logger.info("=== ステップ4: 在庫変動適用 ===")
        
        if dry_run:
            logger.info("DRY RUN MODE - 実際の在庫は変更しません")
        
        results = []
        
        for change in inventory_changes:
            common_code = change["common_code"]
            quantity_to_reduce = change["quantity_to_reduce"]
            
            if not dry_run:
                # 実際の在庫更新（今回はdry_run=Trueなので実行されない）
                current_stock = self._get_current_stock(common_code)
                new_stock = max(0, current_stock - quantity_to_reduce)
                self._update_stock(common_code, new_stock)
                
                results.append({
                    "common_code": common_code,
                    "previous_stock": current_stock,
                    "quantity_reduced": quantity_to_reduce,
                    "new_stock": new_stock,
                    "status": "success"
                })
            else:
                # DRY RUN: 変更をシミュレート
                current_stock = self._get_current_stock(common_code)
                new_stock = max(0, current_stock - quantity_to_reduce)
                
                results.append({
                    "common_code": common_code,
                    "previous_stock": current_stock,
                    "quantity_reduced": quantity_to_reduce,
                    "new_stock": new_stock,
                    "status": "simulated",
                    "reasons": change["reasons"]
                })
                
                logger.info(f"  {common_code}: {current_stock} → {new_stock} (-{quantity_to_reduce})")
        
        return results
    
    def _extract_choice_codes(self, choice_code_text):
        """選択肢コード抽出"""
        if not choice_code_text:
            return []
        pattern = r'[A-Z]\d{2}'
        matches = re.findall(pattern, choice_code_text)
        return list(dict.fromkeys(matches))  # 重複除去
    
    def _find_choice_code_mapping(self, choice_code):
        """選択肢コードのマッピング検索"""
        try:
            result = self.supabase.table("choice_code_mapping").select("*").contains("choice_info", {"choice_code": choice_code}).execute()
            return result.data[0] if result.data else None
        except:
            return None
    
    def _find_normal_product_mapping(self, rakuten_sku, fallback_product_code=None):
        """通常商品のマッピング検索（楽天SKUベース、フォールバック対応）"""
        # 1. まず楽天SKU（rakuten_item_number）で検索
        try:
            if rakuten_sku:
                result = self.supabase.table("product_master").select("*").eq("rakuten_sku", rakuten_sku).execute()
                if result.data:
                    logger.debug(f"Found mapping for rakuten_sku {rakuten_sku}: {result.data[0]['common_code']}")
                    return result.data[0]
            
            # 2. フォールバック：product_codeで検索
            if fallback_product_code and fallback_product_code != rakuten_sku:
                result = self.supabase.table("product_master").select("*").eq("rakuten_sku", fallback_product_code).execute()
                if result.data:
                    logger.debug(f"Found mapping for fallback_code {fallback_product_code}: {result.data[0]['common_code']}")
                    return result.data[0]
            
            logger.debug(f"No mapping found for rakuten_sku: {rakuten_sku} or fallback: {fallback_product_code}")
            return None
        except Exception as e:
            logger.error(f"Error finding mapping for {rakuten_sku}: {str(e)}")
            return None
    
    def _get_bundle_components(self, bundle_code):
        """まとめ商品の構成品取得"""
        try:
            # package_componentsテーブルから構成品を取得
            result = self.supabase.table("package_components").select("*").eq("package_code", bundle_code).execute()
            return result.data if result.data else []
        except:
            return []
    
    def _get_current_stock(self, common_code):
        """現在の在庫数取得"""
        try:
            result = self.supabase.table("inventory").select("current_stock").eq("common_code", common_code).execute()
            return result.data[0]["current_stock"] if result.data else 0
        except:
            return 0
    
    def _update_stock(self, common_code, new_stock):
        """在庫数更新"""
        try:
            self.supabase.table("inventory").update({"current_stock": new_stock}).eq("common_code", common_code).execute()
            return True
        except:
            return False
    
    def run_full_process(self, target_date=None, dry_run=True):
        """完全プロセス実行"""
        logger.info("=== 楽天在庫変動処理 完全フロー ===")
        
        # ステップ1: 楽天売上データ抽出
        rakuten_sales = self.step1_extract_rakuten_sales(target_date)
        
        # ステップ2: 共通コードマッピング
        mapped_items, unmapped_items = self.step2_map_to_common_codes(rakuten_sales)
        
        # ステップ3: まとめ商品処理
        inventory_changes = self.step3_process_bundle_products(mapped_items)
        
        # ステップ4: 在庫変動適用
        results = self.step4_apply_inventory_changes(inventory_changes, dry_run)
        
        # サマリー
        logger.info("=== 処理サマリー ===")
        logger.info(f"楽天商品: {len(rakuten_sales)}件")
        logger.info(f"マッピング成功: {len(mapped_items)}件")
        logger.info(f"マッピング失敗: {len(unmapped_items)}件")
        logger.info(f"最終在庫変動: {len(inventory_changes)}商品")
        
        return {
            "rakuten_sales": rakuten_sales,
            "mapped_items": mapped_items,
            "unmapped_items": unmapped_items,
            "inventory_changes": inventory_changes,
            "results": results
        }

def test_improved_mapping():
    """改良マッピングシステムのテスト"""
    system = InventoryMappingSystem()
    
    # 今日のデータでテスト実行
    result = system.run_full_process(dry_run=True)
    
    print("\n=== テスト結果 ===")
    print(f"楽天商品データ: {len(result['rakuten_sales'])}件")
    print(f"マッピング成功: {len(result['mapped_items'])}件")
    print(f"マッピング失敗: {len(result['unmapped_items'])}件")
    print(f"在庫変動対象: {len(result['inventory_changes'])}商品")
    
    if result['inventory_changes']:
        print("\n在庫変動詳細:")
        for change in result['inventory_changes'][:5]:  # 最初の5件のみ表示
            print(f"  {change['common_code']}: -{change['quantity_to_reduce']}個")
    
    if result['unmapped_items']:
        print("\n未マッピング商品:")
        for item in result['unmapped_items'][:3]:  # 最初の3件のみ表示
            print(f"  {item['rakuten_code']}: {item['product_name'][:30]}...")

if __name__ == "__main__":
    test_improved_mapping()