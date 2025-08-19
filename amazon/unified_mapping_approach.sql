-- 統合マッピングアプローチ（推奨）
-- 楽天とAmazonのSKUを同じテーブルで管理

-- =====================================
-- 統合SKUマッピングテーブル
-- =====================================
CREATE TABLE IF NOT EXISTS platform_sku_mapping (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    platform TEXT NOT NULL CHECK (platform IN ('rakuten', 'amazon', 'colorme', 'other')),
    platform_sku TEXT NOT NULL,  -- 各プラットフォームのSKU
    common_code TEXT NOT NULL,    -- 共通商品コード
    product_name TEXT,
    additional_info JSONB,         -- ASIN、選択肢コード等の追加情報
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(platform, platform_sku)
);

-- インデックス
CREATE INDEX idx_platform_sku_mapping_common_code ON platform_sku_mapping(common_code);
CREATE INDEX idx_platform_sku_mapping_platform ON platform_sku_mapping(platform);

-- =====================================
-- データ移行（既存の楽天データを統合テーブルへ）
-- =====================================
-- product_masterから移行
INSERT INTO platform_sku_mapping (platform, platform_sku, common_code, product_name)
SELECT 
    'rakuten',
    rakuten_sku,
    common_code,
    product_name
FROM product_master
WHERE rakuten_sku IS NOT NULL
ON CONFLICT (platform, platform_sku) DO NOTHING;

-- choice_code_mappingから移行（選択肢コード）
INSERT INTO platform_sku_mapping (platform, platform_sku, common_code, product_name, additional_info)
SELECT 
    'rakuten',
    choice_info->>'choice_code',
    common_code,
    product_name,
    choice_info
FROM choice_code_mapping
WHERE choice_info->>'choice_code' IS NOT NULL
ON CONFLICT (platform, platform_sku) DO NOTHING;

-- =====================================
-- Amazon商品の追加例
-- =====================================
INSERT INTO platform_sku_mapping (platform, platform_sku, common_code, product_name, additional_info) VALUES
-- 楽天と同じ商品（同じ共通コード）
('amazon', 'AMZ-SKU-001', 'CM001', '商品A', '{"asin": "B001EXAMPLE"}'),
('amazon', 'AMZ-SKU-002', 'CM002', '商品B', '{"asin": "B002EXAMPLE"}'),
-- Amazon専用商品
('amazon', 'AMZ-EXCL-001', 'CM201', 'Amazon限定商品', '{"asin": "B901EXAMPLE", "fba": true}')
ON CONFLICT (platform, platform_sku) DO NOTHING;

-- =====================================
-- 統合ビュー：全プラットフォームの注文を共通コードで管理
-- =====================================
CREATE OR REPLACE VIEW unified_order_items_with_mapping AS
SELECT 
    o.platform,
    o.order_number,
    o.order_date,
    oi.product_code,
    oi.product_name,
    oi.quantity,
    oi.price,
    psm.common_code,
    psm.product_name as master_product_name,
    i.current_stock
FROM orders o
JOIN order_items oi ON o.id = oi.order_id
LEFT JOIN platform_sku_mapping psm ON 
    psm.platform = o.platform AND 
    psm.platform_sku = oi.product_code
LEFT JOIN inventory i ON i.common_code = psm.common_code
ORDER BY o.order_date DESC;

-- =====================================
-- マッピング確認用クエリ
-- =====================================
-- プラットフォーム別マッピング状況
SELECT 
    platform,
    COUNT(*) as sku_count,
    COUNT(DISTINCT common_code) as unique_products
FROM platform_sku_mapping
GROUP BY platform;

-- 共通商品の確認（複数プラットフォームで販売）
SELECT 
    common_code,
    product_name,
    STRING_AGG(platform || ':' || platform_sku, ', ') as platform_skus
FROM platform_sku_mapping
GROUP BY common_code, product_name
HAVING COUNT(DISTINCT platform) > 1;