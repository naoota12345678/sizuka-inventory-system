from fastapi import FastAPI
from fastapi.responses import JSONResponse
import os
from supabase import create_client, Client

app = FastAPI()

@app.get("/api/check_order_items_structure")
def check_order_items_structure():
    """order_itemsテーブルの構造を確認して楽天関連カラムが存在するかチェック"""
    try:
        # Supabase設定
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        
        if not supabase_url or not supabase_key:
            return {
                "status": "error",
                "message": "Supabase環境変数が設定されていません"
            }
        
        supabase: Client = create_client(supabase_url, supabase_key)
        
        # 1. order_itemsテーブルのカラム構造を確認
        # PostgreSQLのinformation_schemaを使ってカラム情報を取得
        column_query = """
        SELECT 
            column_name,
            data_type,
            is_nullable,
            column_default
        FROM information_schema.columns 
        WHERE table_name = 'order_items' 
        ORDER BY ordinal_position;
        """
        
        columns_response = supabase.rpc('execute_sql', {'sql': column_query}).execute()
        
        if hasattr(columns_response, 'data') and columns_response.data:
            columns = columns_response.data
        else:
            # 代替方法: 実際のデータを少し取得してカラムを確認
            sample_response = supabase.table('order_items').select('*').limit(1).execute()
            if sample_response.data:
                columns = [{"column_name": key, "data_type": "unknown", "is_nullable": "unknown", "column_default": "unknown"} 
                          for key in sample_response.data[0].keys()]
            else:
                return {
                    "status": "error", 
                    "message": "order_itemsテーブルのカラム情報を取得できませんでした"
                }
        
        # 2. 楽天関連カラムの存在確認
        expected_rakuten_columns = [
            'choice_code',
            'parent_item_id', 
            'item_type',
            'rakuten_variant_id',
            'rakuten_item_number',
            'shop_item_code',
            'jan_code',
            'category_path',
            'brand_name',
            'weight_info',
            'size_info',
            'extended_rakuten_data',
            'rakuten_sku',
            'sku_type'
        ]
        
        existing_columns = [col['column_name'] for col in columns]
        missing_columns = [col for col in expected_rakuten_columns if col not in existing_columns]
        existing_rakuten_columns = [col for col in expected_rakuten_columns if col in existing_columns]
        
        # 3. order_itemsのサンプルデータを取得（楽天関連データがあるか確認）
        sample_data_response = supabase.table('order_items').select('*').limit(5).execute()
        sample_data = sample_data_response.data if sample_data_response.data else []
        
        # 4. 楽天関連データが実際に保存されているか確認
        rakuten_data_exists = False
        if sample_data:
            for item in sample_data:
                if any(item.get(col) for col in existing_rakuten_columns):
                    rakuten_data_exists = True
                    break
        
        return {
            "status": "success",
            "table_structure": {
                "total_columns": len(columns),
                "all_columns": existing_columns,
                "column_details": columns
            },
            "rakuten_enhancement_status": {
                "existing_rakuten_columns": existing_rakuten_columns,
                "missing_rakuten_columns": missing_columns,
                "enhancement_applied": len(missing_columns) == 0,
                "rakuten_data_exists": rakuten_data_exists
            },
            "sample_data": sample_data[:2] if sample_data else []  # 最初の2件のみ表示
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"エラーが発生しました: {str(e)}"
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)