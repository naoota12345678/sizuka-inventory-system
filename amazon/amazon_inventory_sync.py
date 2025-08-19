#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Amazon在庫同期システム
共通在庫テーブルとの連携
"""

import os
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from supabase import create_client
from collections import defaultdict

# ロギング設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Supabase接続情報
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://equrcpeifogdrxoldkpe.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ")

class AmazonInventorySync:
    """Amazon在庫同期クラス"""
    
    def __init__(self):
        """初期化"""
        self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        self.mapping_cache = {}
        self._load_mappings()
        
    def _load_mappings(self):
        """商品マッピング情報をロード"""
        try:
            # Amazon商品マスタからマッピング情報を取得
            response = self.supabase.table("amazon_product_master").select("*").execute()
            
            for item in response.data:
                self.mapping_cache[item["sku"]] = {
                    "common_code": item["common_code"],
                    "product_name": item.get("product_name", ""),
                    "asin": item.get("asin", "")
                }
                
            logger.info(f"Loaded {len(self.mapping_cache)} product mappings")
            
        except Exception as e:
            logger.error(f"Error loading mappings: {str(e)}")
            
    def get_common_code(self, sku: str, asin: str = None) -> Optional[str]:
        """
        SKUから共通コードを取得
        
        Args:
            sku: Amazon SKU
            asin: ASIN（オプション）
            
        Returns:
            共通コード
        """
        # キャッシュから取得
        if sku in self.mapping_cache:
            return self.mapping_cache[sku]["common_code"]
            
        # データベースから検索
        try:
            response = self.supabase.table("amazon_product_master").select("common_code").eq("sku", sku).execute()
            
            if response.data:
                return response.data[0]["common_code"]
                
            # ASINで検索（フォールバック）
            if asin:
                response = self.supabase.table("amazon_product_master").select("common_code").eq("asin", asin).execute()
                if response.data:
                    return response.data[0]["common_code"]
                    
        except Exception as e:
            logger.error(f"Error getting common code for SKU {sku}: {str(e)}")
            
        return None
        
    def sync_order_inventory_changes(self, order_items: List[Dict]) -> Dict[str, Any]:
        """
        注文に基づいて在庫を更新
        
        Args:
            order_items: 注文商品リスト
            
        Returns:
            更新結果
        """
        results = {
            "processed": 0,
            "updated": 0,
            "skipped": 0,
            "errors": []
        }
        
        # 商品ごとに集計
        inventory_changes = defaultdict(int)
        
        for item in order_items:
            sku = item.get("sku")
            quantity = item.get("quantity_shipped", 0)
            
            if not sku or quantity <= 0:
                results["skipped"] += 1
                continue
                
            common_code = self.get_common_code(sku, item.get("asin"))
            
            if common_code:
                inventory_changes[common_code] -= quantity  # 販売なので在庫減少
                results["processed"] += 1
            else:
                logger.warning(f"No mapping found for SKU: {sku}")
                results["skipped"] += 1
                
        # 在庫テーブルを更新
        for common_code, quantity_change in inventory_changes.items():
            try:
                # 現在の在庫を取得
                current = self.supabase.table("inventory").select("*").eq("common_code", common_code).execute()
                
                if current.data:
                    # 既存在庫を更新
                    current_stock = current.data[0].get("current_stock", 0)
                    new_stock = max(0, current_stock + quantity_change)  # 負の在庫は防ぐ
                    
                    self.supabase.table("inventory").update({
                        "current_stock": new_stock,
                        "last_updated": datetime.now(timezone.utc).isoformat()
                    }).eq("common_code", common_code).execute()
                    
                    logger.info(f"Updated inventory for {common_code}: {current_stock} -> {new_stock}")
                else:
                    # 新規在庫レコード作成
                    product_name = self.mapping_cache.get(common_code, {}).get("product_name", f"Amazon商品_{common_code}")
                    
                    self.supabase.table("inventory").insert({
                        "common_code": common_code,
                        "current_stock": max(0, quantity_change),
                        "minimum_stock": 10,  # デフォルト最小在庫
                        "product_name": product_name,
                        "last_updated": datetime.now(timezone.utc).isoformat()
                    }).execute()
                    
                    logger.info(f"Created new inventory for {common_code}")
                    
                results["updated"] += 1
                
            except Exception as e:
                logger.error(f"Error updating inventory for {common_code}: {str(e)}")
                results["errors"].append({
                    "common_code": common_code,
                    "error": str(e)
                })
                
        return results
        
    def sync_fba_inventory(self) -> Dict[str, Any]:
        """
        FBA在庫を共通在庫テーブルに同期
        
        Returns:
            同期結果
        """
        results = {
            "processed": 0,
            "updated": 0,
            "errors": []
        }
        
        try:
            # FBA在庫データを取得
            fba_response = self.supabase.table("amazon_fba_inventory").select("*").execute()
            
            # SKUごとに集計（複数倉庫の在庫を合算）
            sku_totals = defaultdict(lambda: {
                "fulfillable": 0,
                "inbound": 0,
                "product_name": "",
                "asin": ""
            })
            
            for item in fba_response.data:
                sku = item["sku"]
                sku_totals[sku]["fulfillable"] += item.get("fulfillable_quantity", 0)
                sku_totals[sku]["inbound"] += (
                    item.get("inbound_working_quantity", 0) +
                    item.get("inbound_shipped_quantity", 0) +
                    item.get("inbound_receiving_quantity", 0)
                )
                sku_totals[sku]["product_name"] = item.get("product_name", "")
                sku_totals[sku]["asin"] = item.get("asin", "")
                
            # Amazon在庫テーブルを更新
            for sku, totals in sku_totals.items():
                try:
                    common_code = self.get_common_code(sku, totals["asin"])
                    
                    if not common_code:
                        logger.warning(f"No common code mapping for SKU: {sku}")
                        continue
                        
                    # Amazon在庫テーブルを更新
                    amazon_inventory_data = {
                        "sku": sku,
                        "common_code": common_code,
                        "asin": totals["asin"],
                        "product_name": totals["product_name"],
                        "quantity_available": totals["fulfillable"],
                        "quantity_inbound_working": totals["inbound"],
                        "fulfillment_channel": "AFN",
                        "last_updated": datetime.now(timezone.utc).isoformat()
                    }
                    
                    # 既存レコードをチェック
                    existing = self.supabase.table("amazon_inventory").select("id").eq("sku", sku).execute()
                    
                    if existing.data:
                        self.supabase.table("amazon_inventory").update(amazon_inventory_data).eq("sku", sku).execute()
                    else:
                        self.supabase.table("amazon_inventory").insert(amazon_inventory_data).execute()
                        
                    # 共通在庫テーブルも更新
                    total_stock = totals["fulfillable"] + totals["inbound"]
                    self._update_common_inventory(common_code, total_stock, totals["product_name"])
                    
                    results["updated"] += 1
                    results["processed"] += 1
                    
                except Exception as e:
                    logger.error(f"Error syncing SKU {sku}: {str(e)}")
                    results["errors"].append({
                        "sku": sku,
                        "error": str(e)
                    })
                    
        except Exception as e:
            logger.error(f"Error syncing FBA inventory: {str(e)}")
            results["errors"].append({
                "general": str(e)
            })
            
        return results
        
    def _update_common_inventory(self, common_code: str, amazon_stock: int, product_name: str = ""):
        """
        共通在庫テーブルを更新
        
        Args:
            common_code: 共通コード
            amazon_stock: Amazon在庫数
            product_name: 商品名
        """
        try:
            # 現在の在庫を取得
            current = self.supabase.table("inventory").select("*").eq("common_code", common_code).execute()
            
            if current.data:
                # Amazon在庫分を考慮して更新
                # 注：実際の実装では楽天在庫等も考慮する必要がある
                self.supabase.table("inventory").update({
                    "amazon_stock": amazon_stock,  # Amazon在庫フィールドが必要
                    "last_updated": datetime.now(timezone.utc).isoformat()
                }).eq("common_code", common_code).execute()
            else:
                # 新規作成
                self.supabase.table("inventory").insert({
                    "common_code": common_code,
                    "current_stock": amazon_stock,
                    "amazon_stock": amazon_stock,
                    "minimum_stock": 10,
                    "product_name": product_name or f"Amazon商品_{common_code}",
                    "last_updated": datetime.now(timezone.utc).isoformat()
                }).execute()
                
        except Exception as e:
            logger.error(f"Error updating common inventory for {common_code}: {str(e)}")
            
    def process_daily_sync(self) -> Dict[str, Any]:
        """
        日次同期処理
        
        Returns:
            処理結果
        """
        logger.info("Starting daily Amazon inventory sync")
        
        results = {
            "fba_sync": {},
            "order_sync": {},
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # FBA在庫同期
        results["fba_sync"] = self.sync_fba_inventory()
        
        # 最近の注文から在庫変動を処理
        try:
            # 本日の注文商品を取得
            today = datetime.now(timezone.utc).date()
            order_items_response = self.supabase.table("amazon_order_items").select("*").gte("created_at", str(today)).execute()
            
            if order_items_response.data:
                results["order_sync"] = self.sync_order_inventory_changes(order_items_response.data)
            else:
                results["order_sync"] = {"message": "No orders to process today"}
                
        except Exception as e:
            logger.error(f"Error processing orders: {str(e)}")
            results["order_sync"] = {"error": str(e)}
            
        logger.info(f"Daily sync completed: {results}")
        return results


def main():
    """メイン処理"""
    sync = AmazonInventorySync()
    
    # 日次同期を実行
    results = sync.process_daily_sync()
    
    print("Amazon Inventory Sync Results:")
    print(f"FBA Sync: {results['fba_sync']}")
    print(f"Order Sync: {results['order_sync']}")


if __name__ == "__main__":
    main()