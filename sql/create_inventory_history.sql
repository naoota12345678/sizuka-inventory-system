-- 在庫履歴テーブルの作成
-- Supabaseダッシュボードで実行してください

CREATE TABLE IF NOT EXISTS inventory_history (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    product_code VARCHAR(20) NOT NULL,
    product_name VARCHAR(255),
    opening_stock INTEGER DEFAULT 0,
    production_qty INTEGER DEFAULT 0,
    sales_qty INTEGER DEFAULT 0,
    adjustment_qty INTEGER DEFAULT 0,
    closing_stock INTEGER DEFAULT 0,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(date, product_code)
);

-- インデックスの作成
CREATE INDEX IF NOT EXISTS idx_inventory_history_date ON inventory_history(date);
CREATE INDEX IF NOT EXISTS idx_inventory_history_product_code ON inventory_history(product_code);
CREATE INDEX IF NOT EXISTS idx_inventory_history_date_product ON inventory_history(date, product_code);

-- コメント追加
COMMENT ON TABLE inventory_history IS '在庫履歴テーブル - 日別商品別の在庫変動を記録';
COMMENT ON COLUMN inventory_history.date IS '対象日';
COMMENT ON COLUMN inventory_history.product_code IS '商品コード';
COMMENT ON COLUMN inventory_history.product_name IS '商品名';
COMMENT ON COLUMN inventory_history.opening_stock IS '期首在庫';
COMMENT ON COLUMN inventory_history.production_qty IS '製造数量';
COMMENT ON COLUMN inventory_history.sales_qty IS '売上数量';
COMMENT ON COLUMN inventory_history.adjustment_qty IS '調整数量（棚卸し等）';
COMMENT ON COLUMN inventory_history.closing_stock IS '期末在庫';
COMMENT ON COLUMN inventory_history.notes IS '備考';

-- 同期ログテーブルの作成（オプション）
CREATE TABLE IF NOT EXISTS sync_logs (
    id SERIAL PRIMARY KEY,
    sync_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL,
    results JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE sync_logs IS '同期処理ログテーブル';
COMMENT ON COLUMN sync_logs.sync_type IS '同期タイプ（scheduled_daily, manual, bulk等）';
COMMENT ON COLUMN sync_logs.status IS '実行結果（started, completed, error）';
COMMENT ON COLUMN sync_logs.results IS '詳細結果（JSON形式）';