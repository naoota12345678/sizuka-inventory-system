-- ===================================================================
-- Database Schema Updates for Return/Refund Processing
-- 楽天返品・返金処理のためのデータベーススキーマ更新
-- ===================================================================

-- 1. inventory_transactions テーブル作成（存在しない場合）
-- 在庫トランザクション履歴を管理
CREATE TABLE IF NOT EXISTS inventory_transactions (
    id SERIAL PRIMARY KEY,
    common_code VARCHAR(10) NOT NULL,
    transaction_type VARCHAR(20) NOT NULL, 
    quantity_change INTEGER NOT NULL,
    reference_order_item_id INTEGER,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- 外部キー制約
    CONSTRAINT fk_inventory_transactions_common_code 
        FOREIGN KEY (common_code) REFERENCES product_master(common_code),
    CONSTRAINT fk_inventory_transactions_order_item 
        FOREIGN KEY (reference_order_item_id) REFERENCES order_items(id)
);

-- インデックス作成（パフォーマンス向上）
CREATE INDEX IF NOT EXISTS idx_inventory_transactions_common_code 
    ON inventory_transactions(common_code);
CREATE INDEX IF NOT EXISTS idx_inventory_transactions_type 
    ON inventory_transactions(transaction_type);
CREATE INDEX IF NOT EXISTS idx_inventory_transactions_created_at 
    ON inventory_transactions(created_at);

-- 2. orders テーブルに実際のステータスを追加
-- 現在はすべて "completed" になっているため、実際のステータスを管理
ALTER TABLE orders ADD COLUMN IF NOT EXISTS actual_status VARCHAR(20);
ALTER TABLE orders ADD COLUMN IF NOT EXISTS return_date TIMESTAMP WITH TIME ZONE;
ALTER TABLE orders ADD COLUMN IF NOT EXISTS return_reason TEXT;

-- 3. order_items テーブルに返品関連フィールドを追加
ALTER TABLE order_items ADD COLUMN IF NOT EXISTS transaction_type VARCHAR(20) DEFAULT 'sale';
ALTER TABLE order_items ADD COLUMN IF NOT EXISTS original_order_item_id INTEGER;
ALTER TABLE order_items ADD COLUMN IF NOT EXISTS is_returned BOOLEAN DEFAULT FALSE;

-- 外部キー制約（返品元の注文アイテム参照）
ALTER TABLE order_items ADD CONSTRAINT IF NOT EXISTS fk_order_items_original 
    FOREIGN KEY (original_order_item_id) REFERENCES order_items(id);

-- 4. inventory テーブルに返品統計を追加（オプション）
ALTER TABLE inventory ADD COLUMN IF NOT EXISTS total_returned INTEGER DEFAULT 0;
ALTER TABLE inventory ADD COLUMN IF NOT EXISTS last_return_date TIMESTAMP WITH TIME ZONE;

-- 5. 返品処理ログテーブル作成
CREATE TABLE IF NOT EXISTS return_processing_log (
    id SERIAL PRIMARY KEY,
    batch_id UUID DEFAULT gen_random_uuid(),
    order_number VARCHAR(50) NOT NULL,
    processed_items INTEGER DEFAULT 0,
    successful_items INTEGER DEFAULT 0,
    failed_items INTEGER DEFAULT 0,
    processing_status VARCHAR(20) DEFAULT 'pending', -- pending, completed, failed
    error_details TEXT,
    processing_started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    processing_completed_at TIMESTAMP WITH TIME ZONE,
    
    -- インデックス
    CONSTRAINT unique_return_batch_order UNIQUE(batch_id, order_number)
);

-- インデックス作成
CREATE INDEX IF NOT EXISTS idx_return_log_batch_id ON return_processing_log(batch_id);
CREATE INDEX IF NOT EXISTS idx_return_log_order_number ON return_processing_log(order_number);
CREATE INDEX IF NOT EXISTS idx_return_log_status ON return_processing_log(processing_status);

-- 6. トランザクション種別の定義（コメント）
/*
transaction_type の値:
- 'sale': 通常の売上（既存）
- 'return': 返品による在庫追加
- 'return_component': まとめ商品返品時の構成品在庫追加
- 'adjustment': 手動調整
- 'initial_stock': 初期在庫設定
*/

-- 7. 制約とチェック
-- transaction_type の値を制限
ALTER TABLE inventory_transactions 
ADD CONSTRAINT IF NOT EXISTS check_transaction_type 
CHECK (transaction_type IN ('sale', 'return', 'return_component', 'adjustment', 'initial_stock'));

ALTER TABLE order_items 
ADD CONSTRAINT IF NOT EXISTS check_order_item_transaction_type 
CHECK (transaction_type IN ('sale', 'return', 'refund'));

-- actual_status の値を制限
ALTER TABLE orders 
ADD CONSTRAINT IF NOT EXISTS check_actual_status 
CHECK (actual_status IN ('completed', 'cancelled', 'returned', 'partial_return'));

-- 8. 既存データの更新（安全な移行）
-- 既存の order_items を 'sale' として設定
UPDATE order_items SET transaction_type = 'sale' WHERE transaction_type IS NULL;

-- 既存の orders を 'completed' として設定
UPDATE orders SET actual_status = 'completed' WHERE actual_status IS NULL;

-- 9. 返品処理統計ビュー作成
CREATE OR REPLACE VIEW return_statistics AS
SELECT 
    DATE_TRUNC('month', created_at) as month,
    transaction_type,
    COUNT(*) as transaction_count,
    SUM(quantity_change) as total_quantity,
    SUM(CASE WHEN quantity_change > 0 THEN quantity_change ELSE 0 END) as total_additions,
    SUM(CASE WHEN quantity_change < 0 THEN ABS(quantity_change) ELSE 0 END) as total_reductions
FROM inventory_transactions 
WHERE transaction_type IN ('return', 'return_component')
GROUP BY DATE_TRUNC('month', created_at), transaction_type
ORDER BY month DESC, transaction_type;

-- 10. 在庫残高確認ビュー作成（返品処理を含む）
CREATE OR REPLACE VIEW inventory_with_returns AS
SELECT 
    i.common_code,
    i.product_name,
    i.current_stock,
    i.minimum_stock,
    COALESCE(returns.total_returned, 0) as total_returned,
    COALESCE(returns.last_return_date, NULL) as last_return_date,
    i.updated_at
FROM inventory i
LEFT JOIN (
    SELECT 
        common_code,
        SUM(quantity_change) as total_returned,
        MAX(created_at) as last_return_date
    FROM inventory_transactions 
    WHERE transaction_type IN ('return', 'return_component')
    GROUP BY common_code
) returns ON i.common_code = returns.common_code;

-- 11. パフォーマンス最適化
-- よく使用される検索条件にインデックスを追加
CREATE INDEX IF NOT EXISTS idx_orders_actual_status ON orders(actual_status);
CREATE INDEX IF NOT EXISTS idx_order_items_transaction_type ON order_items(transaction_type);
CREATE INDEX IF NOT EXISTS idx_order_items_is_returned ON order_items(is_returned);

-- 12. コメント追加（ドキュメント化）
COMMENT ON TABLE inventory_transactions IS '在庫トランザクション履歴（売上、返品、調整等）';
COMMENT ON COLUMN inventory_transactions.transaction_type IS 'トランザクション種別: sale, return, return_component, adjustment, initial_stock';
COMMENT ON COLUMN inventory_transactions.quantity_change IS '在庫変動数（正=追加、負=減少）';

COMMENT ON TABLE return_processing_log IS '返品処理のバッチログ';
COMMENT ON COLUMN return_processing_log.batch_id IS '処理バッチのUUID';

COMMENT ON COLUMN orders.actual_status IS '実際の注文ステータス（completed, cancelled, returned, partial_return）';
COMMENT ON COLUMN order_items.transaction_type IS '取引種別（sale, return, refund）';

-- 完了メッセージ
-- SELECT 'Database schema updates completed successfully!' as message;