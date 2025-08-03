from fastapi import FastAPI
from fastapi.responses import JSONResponse
import os
from supabase import create_client, Client

app = FastAPI()

@app.get("/api/apply_missing_sql")
def apply_missing_sql():
    """不足しているSQLを適用してテーブル構造を完成させる"""
    try:
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        
        if not supabase_url or not supabase_key:
            return {"status": "error", "message": "Supabase環境変数が設定されていません"}
        
        supabase: Client = create_client(supabase_url, supabase_key)
        
        results = []
        
        # 1. product_mapping_masterテーブルの作成
        create_mapping_table_sql = """
        CREATE TABLE IF NOT EXISTS product_mapping_master (
            id SERIAL PRIMARY KEY,
            rakuten_product_code VARCHAR(100) NOT NULL,
            rakuten_sku VARCHAR(20),
            rakuten_choice_code VARCHAR(20),
            rakuten_product_name VARCHAR(500),
            common_product_code VARCHAR(100) NOT NULL,
            common_product_name VARCHAR(500),
            mapping_confidence INTEGER DEFAULT 100 CHECK (mapping_confidence >= 0 AND mapping_confidence <= 100),
            mapping_type VARCHAR(20) DEFAULT 'manual' CHECK (mapping_type IN ('auto', 'manual', 'verified')),
            mapping_status VARCHAR(20) DEFAULT 'active' CHECK (mapping_status IN ('active', 'inactive', 'pending')),
            weight VARCHAR(50),
            size VARCHAR(50),
            color VARCHAR(50),
            material VARCHAR(100),
            notes TEXT,
            created_by VARCHAR(100),
            verified_by VARCHAR(100),
            verified_at TIMESTAMP WITH TIME ZONE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            UNIQUE(rakuten_product_code, rakuten_sku, rakuten_choice_code)
        );
        """
        
        try:
            supabase.rpc('exec_sql', {'sql': create_mapping_table_sql}).execute()
            results.append({"action": "create_product_mapping_master", "status": "success"})
        except Exception as e:
            # 代替方法: 直接テーブル作成を試行
            try:
                # Supabaseの制限により、RPC関数が使えない場合は段階的に作成
                supabase.table('product_mapping_master').select('id').limit(1).execute()
                results.append({"action": "create_product_mapping_master", "status": "already_exists"})
            except:
                results.append({"action": "create_product_mapping_master", "status": "failed", "error": str(e)})
        
        # 2. rakuten_sku_masterテーブルの作成
        create_sku_table_sql = """
        CREATE TABLE IF NOT EXISTS rakuten_sku_master (
            id SERIAL PRIMARY KEY,
            rakuten_sku VARCHAR(20) UNIQUE NOT NULL,
            product_management_number VARCHAR(100) NOT NULL,
            product_name VARCHAR(500),
            choice_info JSONB,
            is_active BOOLEAN DEFAULT TRUE,
            last_synced_at TIMESTAMP WITH TIME ZONE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        """
        
        try:
            supabase.rpc('exec_sql', {'sql': create_sku_table_sql}).execute()
            results.append({"action": "create_rakuten_sku_master", "status": "success"})
        except Exception as e:
            results.append({"action": "create_rakuten_sku_master", "status": "failed", "error": str(e)})
        
        # 3. order_itemsテーブルへの楽天カラム追加確認
        order_items_sample = supabase.table('order_items').select('*').limit(1).execute()
        existing_columns = list(order_items_sample.data[0].keys()) if order_items_sample.data else []
        
        required_columns = ['choice_code', 'rakuten_sku', 'rakuten_item_number', 'extended_rakuten_data']
        missing_columns = [col for col in required_columns if col not in existing_columns]
        
        if missing_columns:
            results.append({"action": "order_items_columns", "status": "missing", "missing_columns": missing_columns})
        else:
            results.append({"action": "order_items_columns", "status": "complete"})
        
        # 4. サンプルデータの挿入（テーブルが作成された場合）
        if any(r["action"] == "create_product_mapping_master" and r["status"] == "success" for r in results):
            sample_data = [
                {
                    "rakuten_product_code": "10000059",
                    "rakuten_sku": "1797",
                    "rakuten_choice_code": "L01",
                    "rakuten_product_name": "ふわふわサーモン【L:30g】",
                    "common_product_code": "CM042_L",
                    "common_product_name": "共通サーモンL",
                    "mapping_confidence": 95,
                    "mapping_type": "auto",
                    "weight": "30g",
                    "size": "L"
                },
                {
                    "rakuten_product_code": "10000060",
                    "rakuten_sku": "167439411",
                    "rakuten_choice_code": None,
                    "rakuten_product_name": "まぐろジャーキー",
                    "common_product_code": "CM043",
                    "common_product_name": "共通まぐろジャーキー",
                    "mapping_confidence": 90,
                    "mapping_type": "auto",
                    "weight": "50g"
                }
            ]
            
            try:
                supabase.table('product_mapping_master').insert(sample_data).execute()
                results.append({"action": "insert_sample_data", "status": "success", "records": len(sample_data)})
            except Exception as e:
                results.append({"action": "insert_sample_data", "status": "failed", "error": str(e)})
        
        # 5. 最終確認
        final_check = {}
        for table in ['product_mapping_master', 'rakuten_sku_master', 'order_items']:
            try:
                response = supabase.table(table).select('*').limit(1).execute()
                final_check[table] = {
                    "exists": True, 
                    "has_data": len(response.data) > 0,
                    "columns": len(list(response.data[0].keys())) if response.data else 0
                }
            except Exception as e:
                final_check[table] = {"exists": False, "error": str(e)}
        
        return {
            "status": "success",
            "executed_actions": results,
            "table_status": final_check,
            "summary": {
                "product_mapping_master_ready": final_check.get('product_mapping_master', {}).get('exists', False),
                "rakuten_sku_master_ready": final_check.get('rakuten_sku_master', {}).get('exists', False),
                "order_items_enhanced": len(missing_columns) == 0,
                "ready_for_next_step": all([
                    final_check.get('product_mapping_master', {}).get('exists', False),
                    len(missing_columns) == 0
                ])
            }
        }
        
    except Exception as e:
        return {"status": "error", "message": f"エラー: {str(e)}", "error_type": type(e).__name__}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)