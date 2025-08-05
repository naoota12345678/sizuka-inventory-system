-- platform_daily_sales テーブル作成SQL
-- Supabase Dashboard → SQL Editor で実行してください

-- 既存テーブルがある場合は削除（注意：データが消えます）
-- DROP TABLE IF EXISTS platform_daily_sales;

-- platform_daily_sales テーブル作成
CREATE TABLE IF NOT EXISTS platform_daily_sales (
    sales_date DATE NOT NULL,
    platform VARCHAR(20) NOT NULL,
    total_amount DECIMAL(12,2) NOT NULL DEFAULT 0,
    order_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- プライマリキー
    PRIMARY KEY (sales_date, platform),
    
    -- 制約
    CONSTRAINT valid_platform CHECK (platform IN ('rakuten', 'amazon', 'colorme', 'airegi', 'yahoo')),
    CONSTRAINT positive_amount CHECK (total_amount >= 0),
    CONSTRAINT positive_count CHECK (order_count >= 0)
);

-- インデックス作成（パフォーマンス向上のため）
CREATE INDEX IF NOT EXISTS idx_platform_sales_date ON platform_daily_sales(sales_date);
CREATE INDEX IF NOT EXISTS idx_platform_sales_platform ON platform_daily_sales(platform);
CREATE INDEX IF NOT EXISTS idx_platform_sales_amount ON platform_daily_sales(total_amount DESC);

-- コメント追加
COMMENT ON TABLE platform_daily_sales IS 'プラットフォーム別日次売上集計テーブル';
COMMENT ON COLUMN platform_daily_sales.sales_date IS '売上日';
COMMENT ON COLUMN platform_daily_sales.platform IS '販売プラットフォーム';
COMMENT ON COLUMN platform_daily_sales.total_amount IS 'その日の売上合計金額';
COMMENT ON COLUMN platform_daily_sales.order_count IS 'その日の注文件数';

-- テストデータ挿入（動作確認用）
INSERT INTO platform_daily_sales (sales_date, platform, total_amount, order_count) 
VALUES ('2025-08-04', 'rakuten', 500000, 25);

-- 作成確認
SELECT * FROM platform_daily_sales;