from fastapi import FastAPI
from fastapi.responses import JSONResponse
import os
from supabase import create_client, Client

app = FastAPI()

@app.get("/api/force_table_schema_check")
def force_table_schema_check():
    """強制的にテーブル構造を確認し、楽天拡張の適用状況を詳細調査"""
    try:
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        
        if not supabase_url or not supabase_key:
            return {"status": "error", "message": "Supabase環境変数が設定されていません"}
        
        supabase: Client = create_client(supabase_url, supabase_key)
        
        # 1. order_itemsテーブルの全カラム確認
        sample_response = supabase.table('order_items').select('*').limit(1).execute()
        
        if not sample_response.data:
            return {"status": "error", "message": "order_itemsテーブルにデータがありません"}
        
        all_columns = list(sample_response.data[0].keys())
        
        # 2. 楽天関連カラムの詳細チェック
        rakuten_columns_check = {
            'choice_code': 'choice_code' in all_columns,
            'parent_item_id': 'parent_item_id' in all_columns,
            'item_type': 'item_type' in all_columns,
            'rakuten_variant_id': 'rakuten_variant_id' in all_columns,
            'rakuten_item_number': 'rakuten_item_number' in all_columns,
            'shop_item_code': 'shop_item_code' in all_columns,
            'jan_code': 'jan_code' in all_columns,
            'category_path': 'category_path' in all_columns,
            'brand_name': 'brand_name' in all_columns,
            'weight_info': 'weight_info' in all_columns,
            'size_info': 'size_info' in all_columns,
            'extended_rakuten_data': 'extended_rakuten_data' in all_columns,
            'rakuten_sku': 'rakuten_sku' in all_columns,
            'sku_type': 'sku_type' in all_columns
        }
        
        existing_rakuten_columns = [k for k, v in rakuten_columns_check.items() if v]
        missing_rakuten_columns = [k for k, v in rakuten_columns_check.items() if not v]
        
        # 3. product_mapping_masterテーブルの存在確認
        try:
            pm_response = supabase.table('product_mapping_master').select('*').limit(1).execute()
            product_mapping_exists = True
            pm_columns = list(pm_response.data[0].keys()) if pm_response.data else []
        except:
            product_mapping_exists = False
            pm_columns = []
        
        # 4. 楽天データの実際の確認（より多くのサンプルをチェック）
        large_sample = supabase.table('order_items').select('*').limit(50).execute()
        rakuten_data_found = False
        rakuten_examples = {}
        
        for item in large_sample.data:
            for col in existing_rakuten_columns:
                value = item.get(col)
                if value is not None and str(value).strip() != '':
                    rakuten_data_found = True
                    if col not in rakuten_examples:
                        rakuten_examples[col] = []
                    if len(rakuten_examples[col]) < 3:  # 各カラムから最大3個の例
                        rakuten_examples[col].append(str(value))
        
        # 5. 統計情報
        count_response = supabase.table('order_items').select('*', count='exact').limit(0).execute()
        total_records = count_response.count if hasattr(count_response, 'count') else 0
        
        # 6. 結論の判定
        enhancement_percentage = len(existing_rakuten_columns) / len(rakuten_columns_check) * 100
        
        status_conclusion = "UNKNOWN"
        if enhancement_percentage == 100:
            status_conclusion = "FULLY_APPLIED"
        elif enhancement_percentage >= 50:
            status_conclusion = "PARTIALLY_APPLIED"
        elif enhancement_percentage > 0:
            status_conclusion = "MINIMAL_APPLICATION"
        else:
            status_conclusion = "NOT_APPLIED"
        
        return {
            "status": "success",
            "database_analysis": {
                "total_order_items_records": total_records,
                "total_columns_in_order_items": len(all_columns),
                "all_columns": all_columns
            },
            "rakuten_enhancement_analysis": {
                "expected_rakuten_columns": 14,
                "existing_rakuten_columns": len(existing_rakuten_columns),
                "missing_rakuten_columns": len(missing_rakuten_columns),
                "enhancement_percentage": round(enhancement_percentage, 1),
                "detailed_column_status": rakuten_columns_check,
                "existing_columns": existing_rakuten_columns,
                "missing_columns": missing_rakuten_columns
            },
            "product_mapping_master": {
                "exists": product_mapping_exists,
                "columns": pm_columns,
                "column_count": len(pm_columns)
            },
            "rakuten_data_presence": {
                "has_actual_data": rakuten_data_found,
                "columns_with_data": list(rakuten_examples.keys()),
                "examples": rakuten_examples
            },
            "final_assessment": {
                "schema_status": status_conclusion,
                "data_populated": rakuten_data_found,
                "ready_for_sku_processing": status_conclusion in ["FULLY_APPLIED", "PARTIALLY_APPLIED"] and rakuten_data_found,
                "next_action_needed": "APPLY_SQL" if status_conclusion == "NOT_APPLIED" else "CHECK_DATA_FLOW" if not rakuten_data_found else "PROCEED_TO_API_TESTING"
            }
        }
        
    except Exception as e:
        return {"status": "error", "message": f"エラー: {str(e)}", "error_type": type(e).__name__}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)