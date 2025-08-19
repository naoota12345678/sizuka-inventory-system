-- Amazon注文管理用テーブル構造（簡略版）
-- 楽天と同じ構造だが、選択肢関連フィールドを除外

-- =====================================
-- 1. Amazon注文テーブル（楽天ordersと同等）
-- =====================================
CREATE TABLE IF NOT EXISTS amazon_orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_number TEXT UNIQUE NOT NULL,  -- Amazon注文番号
    order_date TIMESTAMP WITH TIME ZONE,
    platform TEXT DEFAULT 'amazon',
    status TEXT,  -- Pending, Shipped, Delivered等
    buyer_email TEXT,
    buyer_name TEXT,
    shipping_address JSONB,
    order_total DECIMAL(10, 2),
    currency_code TEXT DEFAULT 'JPY',
    fulfillment_channel TEXT,  -- AFN(FBA) or MFN(出品者配送)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =====================================
-- 2. Amazon注文明細テーブル（楽天order_itemsと同等）
-- =====================================
CREATE TABLE IF NOT EXISTS amazon_order_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID REFERENCES amazon_orders(id),
    product_code TEXT NOT NULL,  -- Amazon SKU
    product_name TEXT,
    quantity INTEGER DEFAULT 1,
    price DECIMAL(10, 2),
    asin TEXT,  -- Amazon Standard Identification Number
    -- 選択肢関連フィールドは除外（choice_code等）
    item_tax DECIMAL(10, 2),
    shipping_price DECIMAL(10, 2),
    shipping_tax DECIMAL(10, 2),
    promotion_discount DECIMAL(10, 2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =====================================
-- 3. Amazon商品マスタ（楽天product_masterと同等）
-- =====================================
CREATE TABLE IF NOT EXISTS amazon_product_master (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    amazon_sku TEXT UNIQUE NOT NULL,  -- Amazon SKU（楽天のrakuten_skuに相当）
    common_code TEXT NOT NULL,  -- 共通商品コード
    product_name TEXT,
    asin TEXT,
    brand TEXT,
    category TEXT,
    list_price DECIMAL(10, 2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =====================================
-- 4. 統合ビュー（楽天とAmazon両方の売上を確認）
-- =====================================
CREATE OR REPLACE VIEW unified_sales_view AS
-- 楽天の売上
SELECT 
    'rakuten' as platform,
    o.order_number,
    o.order_date,
    oi.product_code,
    oi.product_name,
    oi.quantity,
    oi.price,
    oi.quantity * oi.price as total_amount,
    pm.common_code
FROM orders o
JOIN order_items oi ON o.id = oi.order_id
LEFT JOIN product_master pm ON oi.product_code = pm.rakuten_sku
WHERE o.platform = 'rakuten'

UNION ALL

-- Amazonの売上
SELECT 
    'amazon' as platform,
    ao.order_number,
    ao.order_date,
    aoi.product_code,
    aoi.product_name,
    aoi.quantity,
    aoi.price,
    aoi.quantity * aoi.price as total_amount,
    apm.common_code
FROM amazon_orders ao
JOIN amazon_order_items aoi ON ao.id = aoi.order_id
LEFT JOIN amazon_product_master apm ON aoi.product_code = apm.amazon_sku;

-- =====================================
-- 5. プラットフォーム別売上集計ビュー
-- =====================================
CREATE OR REPLACE VIEW platform_sales_summary AS
SELECT 
    platform,
    DATE_TRUNC('day', order_date) as sale_date,
    COUNT(DISTINCT order_number) as order_count,
    SUM(quantity) as total_quantity,
    SUM(total_amount) as total_sales
FROM unified_sales_view
GROUP BY platform, DATE_TRUNC('day', order_date)
ORDER BY sale_date DESC, platform;

-- =====================================
-- 6. インデックス作成
-- =====================================
CREATE INDEX idx_amazon_orders_order_date ON amazon_orders(order_date);
CREATE INDEX idx_amazon_orders_order_number ON amazon_orders(order_number);
CREATE INDEX idx_amazon_order_items_product_code ON amazon_order_items(product_code);
CREATE INDEX idx_amazon_order_items_asin ON amazon_order_items(asin);
CREATE INDEX idx_amazon_product_master_common_code ON amazon_product_master(common_code);
CREATE INDEX idx_amazon_product_master_asin ON amazon_product_master(asin);

-- =====================================
-- 7. サンプルデータ挿入（テスト用）
-- =====================================
-- Amazon商品マスタのサンプル
INSERT INTO amazon_product_master (amazon_sku, common_code, product_name, asin) VALUES
('AMZ-001', 'CM001', 'サンプル商品1', 'B001SAMPLE1'),
('AMZ-002', 'CM002', 'サンプル商品2', 'B002SAMPLE2'),
('AMZ-003', 'CM003', 'サンプル商品3', 'B003SAMPLE3')
ON CONFLICT (amazon_sku) DO NOTHING;