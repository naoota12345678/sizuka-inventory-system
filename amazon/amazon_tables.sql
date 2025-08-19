-- Amazon Inventory System テーブル構造
-- Supabase Dashboard → SQL Editor で実行

-- 1. Amazon注文テーブル
CREATE TABLE amz_orders (
    id SERIAL PRIMARY KEY,
    order_id VARCHAR(50) UNIQUE NOT NULL,
    order_date DATE NOT NULL,
    purchase_date TIMESTAMP WITH TIME ZONE,
    order_status VARCHAR(50),
    fulfillment_channel VARCHAR(20), -- FBA/FBM
    sales_channel VARCHAR(50),
    ship_city VARCHAR(100),
    ship_state VARCHAR(50),
    ship_postal_code VARCHAR(20),
    ship_country VARCHAR(50),
    total_amount DECIMAL(10,2),
    currency VARCHAR(10) DEFAULT 'JPY',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. Amazon注文商品詳細テーブル
CREATE TABLE amz_order_items (
    id SERIAL PRIMARY KEY,
    order_id VARCHAR(50) REFERENCES amz_orders(order_id),
    order_item_id VARCHAR(50) UNIQUE,
    asin VARCHAR(20) NOT NULL,
    sku VARCHAR(100) NOT NULL,
    product_name TEXT,
    quantity INTEGER NOT NULL DEFAULT 1,
    item_price DECIMAL(10,2),
    item_tax DECIMAL(10,2),
    shipping_price DECIMAL(10,2),
    shipping_tax DECIMAL(10,2),
    promotion_discount DECIMAL(10,2),
    condition_id VARCHAR(20),
    condition_note TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. Amazon商品マスタテーブル
CREATE TABLE amz_product_master (
    id SERIAL PRIMARY KEY,
    asin VARCHAR(20) UNIQUE NOT NULL,
    sku VARCHAR(100) NOT NULL,
    product_name TEXT NOT NULL,
    common_code VARCHAR(20), -- 共通コードへのマッピング
    brand VARCHAR(100),
    category VARCHAR(200),
    item_type VARCHAR(100),
    parent_asin VARCHAR(20),
    variation_data JSONB,
    fba_available BOOLEAN DEFAULT false,
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 4. Amazon在庫テーブル
CREATE TABLE amz_inventory (
    id SERIAL PRIMARY KEY,
    sku VARCHAR(100) UNIQUE NOT NULL,
    asin VARCHAR(20),
    common_code VARCHAR(20),
    product_name TEXT,
    fba_stock INTEGER DEFAULT 0,
    fbm_stock INTEGER DEFAULT 0,
    reserved_stock INTEGER DEFAULT 0,
    inbound_stock INTEGER DEFAULT 0,
    total_stock INTEGER GENERATED ALWAYS AS (COALESCE(fba_stock,0) + COALESCE(fbm_stock,0)) STORED,
    minimum_stock INTEGER DEFAULT 0,
    last_sync_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 5. ASINマッピングテーブル（ASIN→共通コード）
CREATE TABLE amz_asin_mapping (
    id SERIAL PRIMARY KEY,
    asin VARCHAR(20) NOT NULL,
    sku VARCHAR(100) NOT NULL,
    common_code VARCHAR(20) NOT NULL,
    product_name TEXT,
    mapping_type VARCHAR(50), -- 'direct', 'variant', 'bundle'
    mapping_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(asin, sku)
);

-- 6. Amazon日次集計テーブル
CREATE TABLE amz_daily_summary (
    summary_date DATE NOT NULL,
    total_orders INTEGER DEFAULT 0,
    total_items INTEGER DEFAULT 0,
    total_sales DECIMAL(12,2) DEFAULT 0,
    fba_orders INTEGER DEFAULT 0,
    fbm_orders INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (summary_date)
);

-- インデックス作成
CREATE INDEX idx_amz_orders_date ON amz_orders(order_date);
CREATE INDEX idx_amz_orders_status ON amz_orders(order_status);
CREATE INDEX idx_amz_order_items_asin ON amz_order_items(asin);
CREATE INDEX idx_amz_order_items_sku ON amz_order_items(sku);
CREATE INDEX idx_amz_product_master_sku ON amz_product_master(sku);
CREATE INDEX idx_amz_product_master_common ON amz_product_master(common_code);
CREATE INDEX idx_amz_inventory_common ON amz_inventory(common_code);
CREATE INDEX idx_amz_asin_mapping_common ON amz_asin_mapping(common_code);

-- RLS (Row Level Security) 設定
ALTER TABLE amz_orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE amz_order_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE amz_product_master ENABLE ROW LEVEL SECURITY;
ALTER TABLE amz_inventory ENABLE ROW LEVEL SECURITY;
ALTER TABLE amz_asin_mapping ENABLE ROW LEVEL SECURITY;
ALTER TABLE amz_daily_summary ENABLE ROW LEVEL SECURITY;

-- 全ユーザーに読み取り権限
CREATE POLICY "Allow public read access" ON amz_orders FOR SELECT USING (true);
CREATE POLICY "Allow public read access" ON amz_order_items FOR SELECT USING (true);
CREATE POLICY "Allow public read access" ON amz_product_master FOR SELECT USING (true);
CREATE POLICY "Allow public read access" ON amz_inventory FOR SELECT USING (true);
CREATE POLICY "Allow public read access" ON amz_asin_mapping FOR SELECT USING (true);
CREATE POLICY "Allow public read access" ON amz_daily_summary FOR SELECT USING (true);

-- テストデータ挿入（例）
INSERT INTO amz_product_master (asin, sku, product_name, common_code) VALUES
('B08ABC12345', 'AMZ-SKU-001', 'サンプル商品A', 'CM001'),
('B08DEF67890', 'AMZ-SKU-002', 'サンプル商品B', 'CM002');

INSERT INTO amz_inventory (sku, asin, common_code, product_name, fba_stock, fbm_stock) VALUES
('AMZ-SKU-001', 'B08ABC12345', 'CM001', 'サンプル商品A', 100, 50),
('AMZ-SKU-002', 'B08DEF67890', 'CM002', 'サンプル商品B', 200, 0);