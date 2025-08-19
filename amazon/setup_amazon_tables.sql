-- Amazon注文管理用テーブル構造
-- 楽天システムと同じ構造で設計

-- Amazon注文テーブル
CREATE TABLE IF NOT EXISTS amazon_orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id TEXT UNIQUE NOT NULL,
    purchase_date TIMESTAMP WITH TIME ZONE,
    order_status TEXT,
    fulfillment_channel TEXT,
    ship_service_level TEXT,
    marketplace_id TEXT,
    buyer_email TEXT,
    buyer_name TEXT,
    ship_address JSONB,
    order_total DECIMAL(10, 2),
    currency_code TEXT,
    payment_method TEXT,
    is_business_order BOOLEAN DEFAULT FALSE,
    is_prime BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Amazon注文商品詳細テーブル
CREATE TABLE IF NOT EXISTS amazon_order_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID REFERENCES amazon_orders(id),
    amazon_order_id TEXT NOT NULL,
    order_item_id TEXT UNIQUE NOT NULL,
    asin TEXT,
    sku TEXT,
    product_name TEXT,
    quantity_ordered INTEGER,
    quantity_shipped INTEGER,
    item_price DECIMAL(10, 2),
    item_tax DECIMAL(10, 2),
    shipping_price DECIMAL(10, 2),
    shipping_tax DECIMAL(10, 2),
    shipping_discount DECIMAL(10, 2),
    promotion_discount DECIMAL(10, 2),
    condition_id TEXT,
    condition_note TEXT,
    is_gift BOOLEAN DEFAULT FALSE,
    gift_message_text TEXT,
    gift_wrap_price DECIMAL(10, 2),
    gift_wrap_tax DECIMAL(10, 2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Amazon商品マスタテーブル
CREATE TABLE IF NOT EXISTS amazon_product_master (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    asin TEXT UNIQUE NOT NULL,
    sku TEXT UNIQUE NOT NULL,
    common_code TEXT NOT NULL,
    product_name TEXT,
    brand TEXT,
    manufacturer TEXT,
    product_group TEXT,
    product_type TEXT,
    list_price DECIMAL(10, 2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Amazon在庫テーブル（共通在庫と連携）
CREATE TABLE IF NOT EXISTS amazon_inventory (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sku TEXT UNIQUE NOT NULL,
    common_code TEXT NOT NULL,
    fnsku TEXT,
    asin TEXT,
    product_name TEXT,
    condition TEXT DEFAULT 'NewItem',
    your_price DECIMAL(10, 2),
    fulfillment_channel TEXT,
    quantity_available INTEGER DEFAULT 0,
    quantity_inbound_working INTEGER DEFAULT 0,
    quantity_inbound_shipped INTEGER DEFAULT 0,
    quantity_inbound_receiving INTEGER DEFAULT 0,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Amazon FBA在庫テーブル
CREATE TABLE IF NOT EXISTS amazon_fba_inventory (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sku TEXT NOT NULL,
    fnsku TEXT,
    asin TEXT,
    product_name TEXT,
    condition TEXT,
    fulfillable_quantity INTEGER DEFAULT 0,
    total_quantity INTEGER DEFAULT 0,
    inbound_working_quantity INTEGER DEFAULT 0,
    inbound_shipped_quantity INTEGER DEFAULT 0,
    inbound_receiving_quantity INTEGER DEFAULT 0,
    reserved_quantity INTEGER DEFAULT 0,
    researching_quantity INTEGER DEFAULT 0,
    unfulfillable_quantity INTEGER DEFAULT 0,
    warehouse_code TEXT,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Amazon売上集計用ビュー
CREATE OR REPLACE VIEW amazon_sales_summary AS
SELECT 
    DATE_TRUNC('day', ao.purchase_date) as sale_date,
    COUNT(DISTINCT ao.order_id) as order_count,
    COUNT(aoi.id) as item_count,
    SUM(aoi.quantity_ordered) as total_quantity,
    SUM(aoi.item_price) as total_sales,
    AVG(aoi.item_price) as average_price
FROM amazon_orders ao
JOIN amazon_order_items aoi ON ao.id = aoi.order_id
WHERE ao.order_status != 'Cancelled'
GROUP BY DATE_TRUNC('day', ao.purchase_date);

-- インデックス作成
CREATE INDEX idx_amazon_orders_purchase_date ON amazon_orders(purchase_date);
CREATE INDEX idx_amazon_orders_order_id ON amazon_orders(order_id);
CREATE INDEX idx_amazon_order_items_asin ON amazon_order_items(asin);
CREATE INDEX idx_amazon_order_items_sku ON amazon_order_items(sku);
CREATE INDEX idx_amazon_product_master_common_code ON amazon_product_master(common_code);
CREATE INDEX idx_amazon_inventory_common_code ON amazon_inventory(common_code);