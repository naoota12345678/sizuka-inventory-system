-- updated_at カラムを追加
ALTER TABLE platform_daily_sales 
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();