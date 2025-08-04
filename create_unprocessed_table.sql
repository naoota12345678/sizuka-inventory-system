-- 未処理売上アイテムテーブル
-- マッピングが見つからない楽天注文を記録して手動対応可能にする

CREATE TABLE IF NOT EXISTS unprocessed_sales_items (
    id SERIAL PRIMARY KEY,
    order_item_id INTEGER NOT NULL,
    order_id INTEGER NOT NULL,
    product_code VARCHAR(50),
    product_name TEXT,
    quantity INTEGER NOT NULL,
    choice_code_text TEXT,
    unmapped_codes TEXT[], -- マッピングされなかった選択肢コードの配列
    status VARCHAR(20) DEFAULT 'unprocessed', -- unprocessed, resolved, manual_review
    resolution_notes TEXT, -- 手動対応時のメモ
    resolved_at TIMESTAMP WITH TIME ZONE,
    resolved_by VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- インデックス作成
CREATE INDEX IF NOT EXISTS idx_unprocessed_sales_status ON unprocessed_sales_items(status);
CREATE INDEX IF NOT EXISTS idx_unprocessed_sales_order_item ON unprocessed_sales_items(order_item_id);
CREATE INDEX IF NOT EXISTS idx_unprocessed_sales_created_at ON unprocessed_sales_items(created_at);

-- コメント追加
COMMENT ON TABLE unprocessed_sales_items IS 'マッピングが見つからない楽天注文アイテムを記録';
COMMENT ON COLUMN unprocessed_sales_items.unmapped_codes IS 'マッピングされなかった選択肢コードの配列';
COMMENT ON COLUMN unprocessed_sales_items.status IS 'unprocessed: 未処理, resolved: 解決済み, manual_review: 手動確認必要';
COMMENT ON COLUMN unprocessed_sales_items.resolution_notes IS '手動対応時の解決方法やメモ';