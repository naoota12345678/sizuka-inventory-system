from fastapi import FastAPI
from datetime import datetime
import pytz
import os
from supabase import create_client, Client

app = FastAPI()

# Supabase接続
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if SUPABASE_URL and SUPABASE_KEY:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
else:
    supabase = None

@app.post("/api/create_missing_tables")
async def create_missing_tables():
    """不足しているテーブルを作成"""
    try:
        if not supabase:
            return {"error": "Database connection not configured"}
            
        results = []
        
        # 1. sales_daily テーブル作成
        sales_daily_sql = """
        CREATE TABLE IF NOT EXISTS sales_daily (
            id SERIAL PRIMARY KEY,
            summary_date DATE NOT NULL,
            product_code VARCHAR(10) NOT NULL,
            product_name VARCHAR(255),
            platform_id INTEGER NOT NULL,
            units_sold INTEGER DEFAULT 0,
            gross_sales DECIMAL(10,2) DEFAULT 0,
            discounts DECIMAL(10,2) DEFAULT 0,
            net_sales DECIMAL(10,2) DEFAULT 0,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (platform_id) REFERENCES platform(id),
            UNIQUE(summary_date, product_code, platform_id)
        );
        """
        
        try:
            supabase.rpc('exec_sql', {'sql': sales_daily_sql}).execute()
            results.append({"table": "sales_daily", "status": "created"})
        except Exception as e:
            results.append({"table": "sales_daily", "status": "error", "message": str(e)})
        
        # 2. sales_transactions テーブル作成
        sales_transactions_sql = """
        CREATE TABLE IF NOT EXISTS sales_transactions (
            id SERIAL PRIMARY KEY,
            transaction_id VARCHAR(100) NOT NULL,
            platform_id INTEGER NOT NULL,
            common_code VARCHAR(10) NOT NULL,
            sale_date TIMESTAMP WITH TIME ZONE NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price DECIMAL(10,2) NOT NULL,
            total_amount DECIMAL(10,2) NOT NULL,
            tax_amount DECIMAL(10,2) DEFAULT 0,
            shipping_fee DECIMAL(10,2) DEFAULT 0,
            commission_fee DECIMAL(10,2) DEFAULT 0,
            net_amount DECIMAL(10,2) NOT NULL,
            customer_type VARCHAR(20) DEFAULT 'retail',
            customer_id VARCHAR(100),
            customer_name VARCHAR(255),
            order_number VARCHAR(100),
            transaction_type VARCHAR(20) DEFAULT 'sale',
            payment_status VARCHAR(20) DEFAULT 'completed',
            fulfillment_status VARCHAR(20) DEFAULT 'shipped',
            raw_data JSONB,
            sync_source VARCHAR(50) NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (platform_id) REFERENCES platform(id),
            UNIQUE(platform_id, transaction_id)
        );
        """
        
        try:
            supabase.rpc('exec_sql', {'sql': sales_transactions_sql}).execute()
            results.append({"table": "sales_transactions", "status": "created"})
        except Exception as e:
            results.append({"table": "sales_transactions", "status": "error", "message": str(e)})
        
        return {
            "status": "completed",
            "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat(),
            "results": results
        }
        
    except Exception as e:
        return {
            "error": f"Table creation failed: {str(e)}",
            "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
        }