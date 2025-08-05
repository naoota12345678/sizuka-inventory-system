#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
シンプル在庫ダッシュボード - 共通コード一覧とマッピング失敗リスト
"""

import os
import logging
from supabase import create_client
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse

# 環境変数を設定
os.environ['SUPABASE_URL'] = 'https://equrcpeifogdrxoldkpe.supabase.co'
os.environ['SUPABASE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ'

from fix_rakuten_sku_mapping import FixedMappingSystem

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SUPABASE_URL = "https://equrcpeifogdrxoldkpe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ"

app = FastAPI()
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
mapping_system = FixedMappingSystem()

@app.get("/inventory-simple")
async def get_simple_inventory():
    """共通コード別在庫一覧（シンプル版）"""
    try:
        # 在庫データを取得（共通コード、在庫数のみ）
        inventory_result = supabase.table("inventory").select(
            "common_code, current_stock, minimum_stock, updated_at"
        ).order("common_code").execute()
        
        if not inventory_result.data:
            return {"message": "在庫データがありません", "status": "no_data"}
        
        return {
            "status": "success",
            "inventory_list": inventory_result.data,
            "total_count": len(inventory_result.data)
        }
        
    except Exception as e:
        logger.error(f"inventory error: {str(e)}")
        return {"status": "error", "message": str(e)}

@app.get("/mapping-failures")
async def get_mapping_failures(limit: int = 50):
    """マッピング失敗商品一覧"""
    try:
        # order_itemsを取得（TESTデータ除外）
        result = supabase.table("order_items").select("*").not_.like("product_code", "TEST%").limit(limit).execute()
        
        failed_items = []
        success_count = 0
        
        for item in result.data:
            try:
                mapping = mapping_system.find_product_mapping(item)
                if mapping:
                    success_count += 1
                else:
                    failed_items.append({
                        "id": item["id"],
                        "product_code": item.get("product_code"),
                        "rakuten_item_number": item.get("rakuten_item_number"),
                        "choice_code": item.get("choice_code"),
                        "order_number": item.get("order_number"),
                        "created_at": item.get("created_at")
                    })
            except Exception as e:
                logger.error(f"エラー ID {item.get('id')}: {str(e)}")
        
        total = len(result.data)
        success_rate = (success_count / total * 100) if total > 0 else 0
        
        return {
            "status": "success",
            "summary": {
                "total_checked": total,
                "success_count": success_count,
                "failed_count": len(failed_items),
                "success_rate": round(success_rate, 1)
            },
            "failed_items": failed_items
        }
        
    except Exception as e:
        logger.error(f"mapping failures error: {str(e)}")
        return {"status": "error", "message": str(e)}

@app.get("/dashboard-simple")
async def simple_dashboard_html(request: Request):
    """シンプル在庫ダッシュボードHTML"""
    try:
        # 在庫データとマッピング失敗データを取得
        inventory_data = await get_simple_inventory()
        mapping_data = await get_mapping_failures()
        
        html_content = """
        <!DOCTYPE html>
        <html lang="ja">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>在庫一覧 - SIZUKA在庫管理システム</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    margin: 20px;
                    background-color: #f5f5f5;
                }
                .container {
                    max-width: 1200px;
                    margin: 0 auto;
                    background: white;
                    padding: 30px;
                    border-radius: 10px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }
                h1, h2 {
                    color: #333;
                    border-bottom: 2px solid #4CAF50;
                    padding-bottom: 10px;
                }
                .summary {
                    background: #e8f5e8;
                    padding: 15px;
                    border-radius: 5px;
                    margin: 20px 0;
                }
                table {
                    width: 100%;
                    border-collapse: collapse;
                    margin: 20px 0;
                }
                th, td {
                    padding: 12px;
                    text-align: left;
                    border-bottom: 1px solid #ddd;
                }
                th {
                    background-color: #4CAF50;
                    color: white;
                }
                tr:hover {
                    background-color: #f5f5f5;
                }
                .negative {
                    color: #d32f2f;
                    font-weight: bold;
                }
                .positive {
                    color: #2e7d32;
                }
                .zero {
                    color: #ff9800;
                    font-weight: bold;
                }
                .section {
                    margin: 40px 0;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>📦 在庫一覧</h1>
        """
        
        if inventory_data.get("status") == "success":
            inventory_list = inventory_data["inventory_list"]
            html_content += f"""
                <div class="summary">
                    <strong>総商品数: {len(inventory_list)}件</strong>
                </div>
                
                <div class="section">
                    <h2>共通コード別在庫一覧</h2>
                    <table>
                        <thead>
                            <tr>
                                <th>共通コード</th>
                                <th>現在在庫</th>
                                <th>最小在庫</th>
                                <th>更新日時</th>
                            </tr>
                        </thead>
                        <tbody>
            """
            
            for item in inventory_list:
                current_stock = item.get('current_stock', 0)
                minimum_stock = item.get('minimum_stock', 0)
                
                # 在庫数の色分け
                if current_stock < 0:
                    stock_class = "negative"
                elif current_stock == 0:
                    stock_class = "zero"
                else:
                    stock_class = "positive"
                
                html_content += f"""
                            <tr>
                                <td><strong>{item.get('common_code', 'N/A')}</strong></td>
                                <td class="{stock_class}">{current_stock}</td>
                                <td>{minimum_stock}</td>
                                <td>{item.get('updated_at', 'N/A')[:19] if item.get('updated_at') else 'N/A'}</td>
                            </tr>
                """
            
            html_content += """
                        </tbody>
                    </table>
                </div>
            """
        
        # マッピング失敗リスト
        if mapping_data.get("status") == "success":
            summary = mapping_data["summary"]
            failed_items = mapping_data["failed_items"]
            
            html_content += f"""
                <div class="section">
                    <h2>⚠️ マッピング失敗商品</h2>
                    <div class="summary">
                        <strong>マッピング成功率: {summary['success_rate']}%</strong><br>
                        成功: {summary['success_count']}件 / 失敗: {summary['failed_count']}件 (チェック対象: {summary['total_checked']}件)
                    </div>
                    
                    <table>
                        <thead>
                            <tr>
                                <th>注文番号</th>
                                <th>商品コード</th>
                                <th>楽天SKU</th>
                                <th>選択肢コード</th>
                                <th>作成日</th>
                            </tr>
                        </thead>
                        <tbody>
            """
            
            for item in failed_items[:20]:  # 最大20件表示
                html_content += f"""
                            <tr>
                                <td>{item.get('order_number', 'N/A')}</td>
                                <td>{item.get('product_code', 'N/A')}</td>
                                <td>{item.get('rakuten_item_number', 'N/A')}</td>
                                <td style="max-width: 200px; overflow: hidden; text-overflow: ellipsis;">{item.get('choice_code', 'N/A')}</td>
                                <td>{item.get('created_at', 'N/A')[:10] if item.get('created_at') else 'N/A'}</td>
                            </tr>
                """
            
            if len(failed_items) > 20:
                html_content += f"""
                            <tr>
                                <td colspan="5" style="text-align: center; color: #666;">
                                    ... 他 {len(failed_items) - 20}件
                                </td>
                            </tr>
                """
            
            html_content += """
                        </tbody>
                    </table>
                </div>
            """
        
        html_content += f"""
                <div style="text-align: center; color: #666; margin-top: 30px;">
                    <p>最終更新: {supabase.table('inventory').select('updated_at').order('updated_at', desc=True).limit(1).execute().data[0]['updated_at'][:19] if supabase.table('inventory').select('updated_at').order('updated_at', desc=True).limit(1).execute().data else 'N/A'}</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return HTMLResponse(content=html_content)
        
    except Exception as e:
        logger.error(f"dashboard HTML error: {str(e)}")
        return HTMLResponse(content=f"<h1>エラー</h1><p>{str(e)}</p>", status_code=500)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8081)