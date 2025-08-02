from fastapi import FastAPI
from fastapi.responses import JSONResponse
import os
from supabase import create_client, Client

app = FastAPI()

@app.get("/api/debug_table_schema")
def debug_table_schema():
    """order_itemsテーブルのスキーマと楽天関連カラムを詳細確認"""
    try:
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        
        if not supabase_url or not supabase_key:
            return {"status": "error", "message": "Supabase環境変数が設定されていません"}
        
        supabase: Client = create_client(supabase_url, supabase_key)
        
        # 1. order_itemsテーブルのサンプルデータを取得してカラム構造を確認
        sample_response = supabase.table('order_items').select('*').limit(1).execute()
        
        if not sample_response.data:
            return {"status": "error", "message": "order_itemsテーブルにデータがありません"}
        
        # カラム一覧を取得
        all_columns = list(sample_response.data[0].keys())
        
        # 楽天関連カラムを確認
        expected_rakuten_columns = [
            'choice_code', 'parent_item_id', 'item_type', 'rakuten_variant_id',
            'rakuten_item_number', 'shop_item_code', 'jan_code', 'category_path',
            'brand_name', 'weight_info', 'size_info', 'extended_rakuten_data',
            'rakuten_sku', 'sku_type'
        ]
        
        existing_rakuten_columns = [col for col in expected_rakuten_columns if col in all_columns]
        missing_rakuten_columns = [col for col in expected_rakuten_columns if col not in all_columns]
        
        # 2. 楽天データが実際に保存されているかチェック
        rakuten_data_sample = []
        more_samples = supabase.table('order_items').select('*').limit(10).execute()
        
        for item in more_samples.data:
            rakuten_data = {}
            for col in existing_rakuten_columns:
                value = item.get(col)
                if value is not None and value != '':
                    rakuten_data[col] = value
            if rakuten_data:
                rakuten_data_sample.append(rakuten_data)
                if len(rakuten_data_sample) >= 3:  # 最大3件まで
                    break
        
        # 3. テーブル全体の統計情報
        count_response = supabase.table('order_items').select('*', count='exact').limit(0).execute()
        total_count = count_response.count if hasattr(count_response, 'count') else 0
        
        return {
            "status": "success",
            "table_info": {
                "total_columns": len(all_columns),
                "total_records": total_count,
                "all_columns": all_columns
            },
            "rakuten_enhancement": {
                "expected_columns_count": len(expected_rakuten_columns),
                "existing_columns_count": len(existing_rakuten_columns),
                "missing_columns_count": len(missing_rakuten_columns),
                "existing_columns": existing_rakuten_columns,
                "missing_columns": missing_rakuten_columns,
                "enhancement_applied": len(missing_rakuten_columns) == 0
            },
            "rakuten_data_analysis": {
                "has_rakuten_data": len(rakuten_data_sample) > 0,
                "sample_count": len(rakuten_data_sample),
                "samples": rakuten_data_sample
            },
            "conclusion": {
                "schema_status": "APPLIED" if len(missing_rakuten_columns) == 0 else "NOT_APPLIED",
                "data_status": "EXISTS" if len(rakuten_data_sample) > 0 else "NO_DATA"
            }
        }
        
    except Exception as e:
        return {"status": "error", "message": f"エラー: {str(e)}"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)