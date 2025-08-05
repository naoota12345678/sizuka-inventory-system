-- platform_daily_sales テーブル作成SQL（修正版）
-- Supabase Dashboard → SQL Editor で実行してください

-- Step 1: テーブル作成
CREATE TABLE platform_daily_sales (
    sales_date DATE NOT NULL,
    platform VARCHAR(20) NOT NULL,
    total_amount DECIMAL(12,2) NOT NULL DEFAULT 0,
    order_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (sales_date, platform)
);

-- Step 2: 制約追加
ALTER TABLE platform_daily_sales 
ADD CONSTRAINT valid_platform 
CHECK (platform IN ('rakuten', 'amazon', 'colorme', 'airegi', 'yahoo'));

ALTER TABLE platform_daily_sales 
ADD CONSTRAINT positive_amount 
CHECK (total_amount >= 0);

ALTER TABLE platform_daily_sales 
ADD CONSTRAINT positive_count 
CHECK (order_count >= 0);

-- Step 3: インデックス作成
CREATE INDEX idx_platform_sales_date ON platform_daily_sales(sales_date);
CREATE INDEX idx_platform_sales_platform ON platform_daily_sales(platform);
CREATE INDEX idx_platform_sales_amount ON platform_daily_sales(total_amount DESC);

-- Step 4: テストデータ挿入
INSERT INTO platform_daily_sales (sales_date, platform, total_amount, order_count) 
VALUES ('2025-08-04', 'rakuten', 500000, 25);

-- Step 5: 確認
SELECT * FROM platform_daily_sales;