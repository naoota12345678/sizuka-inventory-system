-- Amazonテーブル構造（楽天と完全に同じ構造）

-- =====================================
-- 1. 既存のordersテーブルにAmazon注文も保存
-- =====================================
-- ordersテーブルは既存のものを使用（platform='amazon'で区別）

-- =====================================
-- 2. 既存のorder_itemsテーブルにAmazon注文明細も保存
-- =====================================
-- order_itemsテーブルは既存のものを使用
-- 必要に応じてAmazon固有フィールドを追加
ALTER TABLE order_items 
ADD COLUMN IF NOT EXISTS asin TEXT,
ADD COLUMN IF NOT EXISTS amazon_sku TEXT,
ADD COLUMN IF NOT EXISTS fulfillment_channel TEXT;

-- =====================================
-- 3. 既存のproduct_masterテーブルにAmazon SKUも追加
-- =====================================
-- product_masterテーブルは既存のものを使用
-- rakuten_skuフィールドにAmazon SKUを格納（または新カラム追加）
ALTER TABLE product_master
ADD COLUMN IF NOT EXISTS amazon_sku TEXT UNIQUE,
ADD COLUMN IF NOT EXISTS asin TEXT;

-- または、platform別にSKUを管理する場合
CREATE TABLE IF NOT EXISTS sku_mapping (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    platform TEXT NOT NULL, -- 'rakuten' or 'amazon'
    platform_sku TEXT NOT NULL, -- 楽天SKUまたはAmazon SKU
    common_code TEXT NOT NULL,
    product_name TEXT,
    UNIQUE(platform, platform_sku)
);

-- =====================================
-- 4. 統合ビュー（楽天・Amazon両方）
-- =====================================
CREATE OR REPLACE VIEW unified_orders_view AS
SELECT 
    o.id,
    o.order_number,
    o.order_date,
    o.platform,
    oi.product_code,
    oi.product_name,
    oi.quantity,
    oi.price,
    CASE 
        WHEN o.platform = 'rakuten' THEN pm.common_code
        WHEN o.platform = 'amazon' THEN pm2.common_code
        ELSE NULL
    END as common_code
FROM orders o
JOIN order_items oi ON o.id = oi.order_id
LEFT JOIN product_master pm ON oi.product_code = pm.rakuten_sku AND o.platform = 'rakuten'
LEFT JOIN product_master pm2 ON oi.product_code = pm2.amazon_sku AND o.platform = 'amazon';

-- =====================================
-- 5. サンプルデータ（テスト用）
-- =====================================
-- Amazon SKUをproduct_masterに追加
UPDATE product_master SET amazon_sku = 'AMZ-001' WHERE common_code = 'CM001';
UPDATE product_master SET amazon_sku = 'AMZ-002' WHERE common_code = 'CM002';
UPDATE product_master SET amazon_sku = 'AMZ-003' WHERE common_code = 'CM003';

-- または新規追加（楽天SKUがない場合）
INSERT INTO product_master (common_code, product_name, amazon_sku) VALUES
('CM101', 'Amazon専用商品1', 'AMZ-ONLY-001'),
('CM102', 'Amazon専用商品2', 'AMZ-ONLY-002')
ON CONFLICT DO NOTHING;