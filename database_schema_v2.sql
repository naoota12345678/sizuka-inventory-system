-- 統合売上・在庫管理システム v2.0
-- 全プラットフォーム対応データベース設計

-- 1. プラットフォーム管理（拡張）
ALTER TABLE platform ADD COLUMN IF NOT EXISTS integration_type VARCHAR(20) DEFAULT 'api'; -- 'api', 'rpa', 'manual'
ALTER TABLE platform ADD COLUMN IF NOT EXISTS automation_config JSONB;
ALTER TABLE platform ADD COLUMN IF NOT EXISTS sync_frequency VARCHAR(20) DEFAULT 'daily';

-- 新プラットフォーム追加
INSERT INTO platform (name, platform_code, integration_type, is_active) VALUES 
('Amazon', 'amazon', 'api', true),
('カラーミーショップ', 'colorme', 'api', true), 
('エアレジ', 'airegi', 'rpa', true),
('法人卸', 'wholesale', 'manual', true)
ON CONFLICT (platform_code) DO NOTHING;

-- 2. 売上データ統合テーブル
CREATE TABLE IF NOT EXISTS sales_transactions (
    id SERIAL PRIMARY KEY,
    transaction_id VARCHAR(100) NOT NULL, -- プラットフォーム固有のID
    platform_id INTEGER NOT NULL,
    common_code VARCHAR(10) NOT NULL,
    
    -- 売上詳細
    sale_date TIMESTAMP WITH TIME ZONE NOT NULL,
    quantity INTEGER NOT NULL,
    unit_price DECIMAL(10,2) NOT NULL,
    total_amount DECIMAL(10,2) NOT NULL,
    tax_amount DECIMAL(10,2) DEFAULT 0,
    shipping_fee DECIMAL(10,2) DEFAULT 0,
    commission_fee DECIMAL(10,2) DEFAULT 0,
    net_amount DECIMAL(10,2) NOT NULL, -- 手数料等差し引き後
    
    -- 顧客情報
    customer_type VARCHAR(20) DEFAULT 'retail', -- 'retail', 'wholesale', 'b2b'
    customer_id VARCHAR(100),
    customer_name VARCHAR(255),
    
    -- メタデータ
    order_number VARCHAR(100),
    transaction_type VARCHAR(20) DEFAULT 'sale', -- 'sale', 'return', 'cancel'
    payment_status VARCHAR(20) DEFAULT 'completed',
    fulfillment_status VARCHAR(20) DEFAULT 'shipped',
    
    -- システム情報
    raw_data JSONB, -- プラットフォーム固有の生データ
    sync_source VARCHAR(50) NOT NULL, -- 'api', 'rpa', 'manual_import'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (platform_id) REFERENCES platform(id),
    FOREIGN KEY (common_code) REFERENCES product_master(common_code),
    UNIQUE(platform_id, transaction_id)
);

-- 3. 在庫変動履歴（拡張）
ALTER TABLE inventory_history ADD COLUMN IF NOT EXISTS cost_price DECIMAL(10,2);
ALTER TABLE inventory_history ADD COLUMN IF NOT EXISTS transaction_id INTEGER;
ALTER TABLE inventory_history ADD COLUMN IF NOT EXISTS batch_id VARCHAR(50);

-- 4. 原価・利益管理
CREATE TABLE IF NOT EXISTS product_costs (
    id SERIAL PRIMARY KEY,
    common_code VARCHAR(10) NOT NULL,
    cost_type VARCHAR(20) NOT NULL, -- 'material', 'labor', 'overhead', 'total'
    cost_amount DECIMAL(10,2) NOT NULL,
    cost_date DATE NOT NULL,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (common_code) REFERENCES product_master(common_code)
);

-- 5. 分析用ビュー：日別売上サマリー
CREATE OR REPLACE VIEW daily_sales_summary AS
SELECT 
    DATE(sale_date) as sale_date,
    platform_id,
    p.name as platform_name,
    COUNT(*) as transaction_count,
    SUM(quantity) as total_quantity,
    SUM(total_amount) as gross_sales,
    SUM(net_amount) as net_sales,
    SUM(commission_fee) as total_commission,
    AVG(unit_price) as avg_unit_price
FROM sales_transactions st
JOIN platform p ON st.platform_id = p.id
WHERE transaction_type = 'sale'
GROUP BY DATE(sale_date), platform_id, p.name
ORDER BY sale_date DESC;

-- 6. 分析用ビュー：商品別売上サマリー
CREATE OR REPLACE VIEW product_sales_summary AS
SELECT 
    st.common_code,
    pm.product_name,
    pm.product_type,
    COUNT(*) as sale_count,
    SUM(st.quantity) as total_sold,
    SUM(st.total_amount) as gross_revenue,
    SUM(st.net_amount) as net_revenue,
    AVG(st.unit_price) as avg_price,
    MAX(st.sale_date) as last_sale_date,
    
    -- 利益計算（最新の原価を使用）
    COALESCE(
        (SELECT cost_amount FROM product_costs pc 
         WHERE pc.common_code = st.common_code 
         AND pc.cost_type = 'total' 
         ORDER BY cost_date DESC LIMIT 1), 0
    ) as latest_cost,
    
    SUM(st.net_amount) - (
        SUM(st.quantity) * COALESCE(
            (SELECT cost_amount FROM product_costs pc 
             WHERE pc.common_code = st.common_code 
             AND pc.cost_type = 'total' 
             ORDER BY cost_date DESC LIMIT 1), 0
        )
    ) as estimated_profit
    
FROM sales_transactions st
JOIN product_master pm ON st.common_code = pm.common_code
WHERE st.transaction_type = 'sale'
GROUP BY st.common_code, pm.product_name, pm.product_type
ORDER BY net_revenue DESC;

-- 7. 在庫評価ビュー
CREATE OR REPLACE VIEW inventory_valuation AS
SELECT 
    i.common_code,
    pm.product_name,
    i.current_stock,
    COALESCE(pc.cost_amount, 0) as unit_cost,
    (i.current_stock * COALESCE(pc.cost_amount, 0)) as inventory_value,
    i.minimum_stock,
    CASE 
        WHEN i.current_stock <= 0 THEN 'out_of_stock'
        WHEN i.current_stock <= i.minimum_stock THEN 'low_stock'
        ELSE 'in_stock'
    END as stock_status
FROM inventory i
JOIN product_master pm ON i.common_code = pm.common_code
LEFT JOIN LATERAL (
    SELECT cost_amount 
    FROM product_costs pc 
    WHERE pc.common_code = i.common_code 
    AND pc.cost_type = 'total' 
    ORDER BY cost_date DESC 
    LIMIT 1
) pc ON true
WHERE pm.is_active = true;

-- 8. RPA実行ログ
CREATE TABLE IF NOT EXISTS rpa_execution_log (
    id SERIAL PRIMARY KEY,
    platform_id INTEGER NOT NULL,
    execution_type VARCHAR(50) NOT NULL, -- 'data_scraping', 'product_upload', 'inventory_sync'
    status VARCHAR(20) NOT NULL, -- 'running', 'completed', 'failed', 'partial'
    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    end_time TIMESTAMP WITH TIME ZONE,
    records_processed INTEGER DEFAULT 0,
    errors_count INTEGER DEFAULT 0,
    error_details JSONB,
    execution_config JSONB,
    results JSONB,
    FOREIGN KEY (platform_id) REFERENCES platform(id)
);

-- 9. 手動インポートログ
CREATE TABLE IF NOT EXISTS manual_import_log (
    id SERIAL PRIMARY KEY,
    import_type VARCHAR(50) NOT NULL, -- 'wholesale_orders', 'cost_data', 'inventory_adjustment'
    file_name VARCHAR(255),
    file_size INTEGER,
    records_imported INTEGER DEFAULT 0,
    records_failed INTEGER DEFAULT 0,
    import_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    imported_by VARCHAR(100),
    import_summary JSONB,
    error_log JSONB
);

-- 10. アラート設定
CREATE TABLE IF NOT EXISTS alert_rules (
    id SERIAL PRIMARY KEY,
    rule_name VARCHAR(100) NOT NULL,
    rule_type VARCHAR(50) NOT NULL, -- 'low_stock', 'high_sales', 'sync_failure', 'cost_alert'
    conditions JSONB NOT NULL, -- 閾値や条件
    notification_methods JSONB, -- email, slack, etc.
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- インデックス作成
CREATE INDEX idx_sales_transactions_date ON sales_transactions(sale_date);
CREATE INDEX idx_sales_transactions_platform ON sales_transactions(platform_id);
CREATE INDEX idx_sales_transactions_product ON sales_transactions(common_code);
CREATE INDEX idx_sales_transactions_customer ON sales_transactions(customer_type, customer_id);
CREATE INDEX idx_product_costs_code_date ON product_costs(common_code, cost_date DESC);
CREATE INDEX idx_rpa_execution_platform_date ON rpa_execution_log(platform_id, start_time DESC);