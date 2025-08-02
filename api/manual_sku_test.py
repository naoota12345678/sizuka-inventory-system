from fastapi import FastAPI
from fastapi.responses import JSONResponse
import os
from supabase import create_client, Client
import json

app = FastAPI()

@app.get("/api/manual_sku_test")
def manual_sku_test():
    """手動でSKUデータをテストして、楽天SKU保存機能を確認"""
    try:
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        
        if not supabase_url or not supabase_key:
            return {"status": "error", "message": "Supabase環境変数が設定されていません"}
        
        supabase: Client = create_client(supabase_url, supabase_key)
        
        results = {}
        
        # 1. order_itemsテーブルの構造確認
        sample_response = supabase.table('order_items').select('*').limit(1).execute()
        if sample_response.data:
            all_columns = list(sample_response.data[0].keys())
            rakuten_columns = [col for col in ['choice_code', 'rakuten_sku', 'rakuten_item_number', 'extended_rakuten_data'] if col in all_columns]
            results["table_structure"] = {
                "total_columns": len(all_columns),
                "has_rakuten_columns": len(rakuten_columns) > 0,
                "rakuten_columns": rakuten_columns,
                "all_columns": all_columns
            }
        else:
            results["table_structure"] = {"error": "No data in order_items"}
        
        # 2. product_mapping_masterテーブルの確認
        try:
            pm_response = supabase.table('product_mapping_master').select('*').limit(1).execute()
            results["product_mapping_master"] = {
                "exists": True,
                "has_data": len(pm_response.data) > 0,
                "columns": list(pm_response.data[0].keys()) if pm_response.data else []
            }
        except Exception as e:
            results["product_mapping_master"] = {"exists": False, "error": str(e)}
        
        # 3. 手動でテストデータを挿入してみる
        test_data = {
            "order_id": 1,  # 仮のorder_id
            "product_code": "TEST_10000059",
            "product_name": "テスト商品 ふわふわサーモン【L:30g】",
            "quantity": 1,
            "price": 500.0,
            "choice_code": "L01",
            "rakuten_sku": "1797",
            "rakuten_item_number": "test_item_001",
            "extended_rakuten_data": {
                "test": True,
                "extracted_choice": "L01",
                "weight": "30g",
                "size": "L"
            }
        }
        
        try:
            test_insert = supabase.table('order_items').insert(test_data).execute()
            if test_insert.data:
                results["test_insert"] = {
                    "success": True,
                    "inserted_id": test_insert.data[0].get("id"),
                    "message": "楽天カラムへのデータ挿入成功"
                }
            else:
                results["test_insert"] = {"success": False, "message": "データ挿入失敗"}
        except Exception as e:
            results["test_insert"] = {"success": False, "error": str(e)}
        
        # 4. 実際のデータから楽天情報を確認
        try:
            existing_data = supabase.table('order_items').select('*').limit(10).execute()
            rakuten_data_found = []
            
            for item in existing_data.data:
                rakuten_info = {}
                for col in ['choice_code', 'rakuten_sku', 'rakuten_item_number']:
                    if col in item and item[col] is not None and str(item[col]).strip() != '':
                        rakuten_info[col] = item[col]
                
                if rakuten_info:
                    rakuten_data_found.append({
                        "product_code": item.get("product_code"),
                        "product_name": item.get("product_name"),
                        "rakuten_data": rakuten_info
                    })
            
            results["existing_rakuten_data"] = {
                "total_checked": len(existing_data.data),
                "with_rakuten_data": len(rakuten_data_found),
                "samples": rakuten_data_found[:3]  # 最初の3件
            }
            
        except Exception as e:
            results["existing_rakuten_data"] = {"error": str(e)}
        
        # 5. 手動でproduct_mapping_masterにテストデータを挿入
        if results.get("product_mapping_master", {}).get("exists"):
            test_mapping = {
                "rakuten_product_code": "10000059",
                "rakuten_sku": "1797",
                "rakuten_choice_code": "L01",
                "rakuten_product_name": "ふわふわサーモン【L:30g】",
                "common_product_code": "CM059_L",
                "common_product_name": "共通サーモンL",
                "mapping_confidence": 95,
                "mapping_type": "manual_test"
            }
            
            try:
                mapping_insert = supabase.table('product_mapping_master').insert(test_mapping).execute()
                results["mapping_test"] = {
                    "success": True,
                    "message": "product_mapping_masterへの挿入成功"
                }
            except Exception as e:
                results["mapping_test"] = {"success": False, "error": str(e)}
        
        # 結論
        enhancement_ready = results.get("table_structure", {}).get("has_rakuten_columns", False)
        mapping_ready = results.get("product_mapping_master", {}).get("exists", False)
        
        results["conclusion"] = {
            "rakuten_enhancement_applied": enhancement_ready,
            "product_mapping_ready": mapping_ready,
            "system_ready_for_sku_processing": enhancement_ready and mapping_ready,
            "next_steps": [
                "楽天API連携をテスト" if enhancement_ready and mapping_ready else "SQLスクリプト適用が必要",
                "実際の注文データで選択肢コード抽出をテスト",
                "楽天SKU取得APIの動作確認"
            ]
        }
        
        return {
            "status": "success",
            "test_results": results
        }
        
    except Exception as e:
        return {"status": "error", "message": f"テストエラー: {str(e)}"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)