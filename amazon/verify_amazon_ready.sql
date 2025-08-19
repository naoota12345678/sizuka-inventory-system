-- Amazonデータ受け入れ準備の確認SQL（実行は任意）

-- 1. amazon_asinカラムの確認
SELECT 
    column_name, 
    data_type 
FROM information_schema.columns 
WHERE table_name = 'product_master' 
AND column_name = 'amazon_asin';

-- 2. Amazon ASINマッピング済み商品の確認
SELECT 
    common_code,
    product_name,
    amazon_asin
FROM product_master
WHERE amazon_asin IS NOT NULL
LIMIT 10;

-- 3. Amazon注文のテストデータ挿入（動作確認用）
-- INSERT INTO orders (order_number, order_date, platform, status) VALUES
-- ('123-4567890-1234567', NOW(), 'amazon', 'shipped');

-- 4. 統合売上ビュー（楽天・Amazon両方）
CREATE OR REPLACE VIEW all_platform_sales AS
SELECT 
    o.platform,
    o.order_number,
    o.order_date,
    oi.product_code,
    oi.product_name,
    oi.quantity,
    oi.price,
    oi.quantity * oi.price as total_amount,
    CASE 
        WHEN o.platform = 'rakuten' THEN pm.common_code
        WHEN o.platform = 'amazon' THEN pm2.common_code
        ELSE NULL
    END as common_code
FROM orders o
JOIN order_items oi ON o.id = oi.order_id
LEFT JOIN product_master pm ON oi.product_code = pm.rakuten_sku
LEFT JOIN product_master pm2 ON oi.product_code = pm2.amazon_asin;

-- このビューは作成しても良いですが、必須ではありません