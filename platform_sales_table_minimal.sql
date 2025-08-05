-- 最小限版: platform_daily_sales テーブル作成
-- エラーが出る場合はこちらを使用してください

CREATE TABLE platform_daily_sales (
    sales_date DATE NOT NULL,
    platform VARCHAR(20) NOT NULL,
    total_amount DECIMAL(12,2) DEFAULT 0,
    order_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (sales_date, platform)
);