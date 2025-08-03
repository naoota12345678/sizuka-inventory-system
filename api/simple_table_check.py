from fastapi import FastAPI
from fastapi.responses import JSONResponse
import os
from supabase import create_client, Client

app = FastAPI()

@app.get("/api/simple_table_check")
def simple_table_check():
    """シンプルなテーブル構造確認"""
    try:
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        
        supabase: Client = create_client(supabase_url, supabase_key)
        
        # order_itemsテーブルの詳細確認
        order_items_response = supabase.table('order_items').select('*').limit(1).execute()
        order_items_columns = list(order_items_response.data[0].keys()) if order_items_response.data else []
        
        # 楽天関連カラムの確認
        rakuten_columns = ['choice_code', 'rakuten_sku', 'rakuten_item_number', 'extended_rakuten_data']
        existing_rakuten = [col for col in rakuten_columns if col in order_items_columns]
        missing_rakuten = [col for col in rakuten_columns if col not in order_items_columns]
        
        # product_mapping_masterテーブルの確認
        try:
            pm_response = supabase.table('product_mapping_master').select('*').limit(1).execute()
            pm_exists = True
            pm_columns = list(pm_response.data[0].keys()) if pm_response.data else []
        except:
            pm_exists = False
            pm_columns = []
        
        return {
            "order_items": {
                "total_columns": len(order_items_columns),
                "all_columns": order_items_columns,
                "rakuten_columns_existing": existing_rakuten,
                "rakuten_columns_missing": missing_rakuten,
                "rakuten_enhancement_status": "COMPLETE" if len(missing_rakuten) == 0 else "INCOMPLETE"
            },
            "product_mapping_master": {
                "exists": pm_exists,
                "columns": pm_columns,
                "column_count": len(pm_columns)
            },
            "next_action": "READY_FOR_API_TESTING" if (len(missing_rakuten) == 0 and pm_exists) else "NEED_SQL_APPLICATION"
        }
        
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)