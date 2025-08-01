-- 正しい商品管理テーブル構造
-- スプレッドシートの設計に基づく

-- 1. 商品番号マッピング基本表
DROP TABLE IF EXISTS product_mapping_master CASCADE;
CREATE TABLE product_mapping_master (
    id SERIAL PRIMARY KEY,
    common_code VARCHAR(10) NOT NULL UNIQUE, -- CM042, BC001, PC001等
    product_name VARCHAR(255) NOT NULL,
    product_type VARCHAR(20) NOT NULL, -- 'single', 'set_choice', 'set_fixed', 'bundle_fixed', 'bundle_mixed'
    price DECIMAL(10,2),
    description TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. プラットフォーム別商品マッピング（選択肢コード対応表）
DROP TABLE IF EXISTS platform_product_mapping CASCADE;
CREATE TABLE platform_product_mapping (
    id SERIAL PRIMARY KEY,
    platform_name VARCHAR(50) NOT NULL, -- 'rakuten', 'amazon', 'colorme'等
    platform_product_code VARCHAR(100) NOT NULL, -- 457326558401等
    common_code VARCHAR(10) NOT NULL, -- CM042等
    platform_product_name VARCHAR(255),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (common_code) REFERENCES product_mapping_master(common_code),
    UNIQUE(platform_name, platform_product_code)
);

-- 3. セット・まとめ商品内訳テーブル
DROP TABLE IF EXISTS product_bundle_components CASCADE;
CREATE TABLE product_bundle_components (
    id SERIAL PRIMARY KEY,
    bundle_common_code VARCHAR(10) NOT NULL, -- BC001, PC001等（親）
    component_common_code VARCHAR(10) NOT NULL, -- CM042等（子）
    quantity INTEGER NOT NULL DEFAULT 1, -- 構成品の数量
    is_selectable BOOLEAN DEFAULT false, -- チョイス商品で選択可能か
    selection_group VARCHAR(50), -- 選択グループ（レトルト、ちび袋等）
    required_count INTEGER DEFAULT 0, -- 必須選択数
    display_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (bundle_common_code) REFERENCES product_mapping_master(common_code),
    FOREIGN KEY (component_common_code) REFERENCES product_mapping_master(common_code)
);

-- 4. 在庫テーブル（単品商品のみ）
DROP TABLE IF EXISTS inventory_master CASCADE;
CREATE TABLE inventory_master (
    id SERIAL PRIMARY KEY,
    common_code VARCHAR(10) NOT NULL UNIQUE, -- CM042等（単品のみ）
    current_stock INTEGER DEFAULT 0,
    initial_stock INTEGER DEFAULT 0,
    minimum_stock INTEGER DEFAULT 5,
    reorder_point INTEGER DEFAULT 10,
    reference_date DATE, -- 基準日（2025-02-10等）
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (common_code) REFERENCES product_mapping_master(common_code)
);

-- 5. 売上データ（共通コードベース）
DROP TABLE IF EXISTS sales_master CASCADE;
CREATE TABLE sales_master (
    id SERIAL PRIMARY KEY,
    sale_date DATE NOT NULL,
    common_code VARCHAR(10) NOT NULL, -- 売れた商品の共通コード
    platform_name VARCHAR(50) NOT NULL,
    platform_order_id VARCHAR(100),
    quantity INTEGER NOT NULL,
    unit_price DECIMAL(10,2),
    total_amount DECIMAL(10,2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (common_code) REFERENCES product_mapping_master(common_code)
);

-- インデックス作成
CREATE INDEX idx_platform_mapping_platform ON platform_product_mapping(platform_name);
CREATE INDEX idx_platform_mapping_common ON platform_product_mapping(common_code);
CREATE INDEX idx_bundle_components_bundle ON product_bundle_components(bundle_common_code);
CREATE INDEX idx_bundle_components_component ON product_bundle_components(component_common_code);
CREATE INDEX idx_inventory_common ON inventory_master(common_code);
CREATE INDEX idx_sales_date_common ON sales_master(sale_date, common_code);

-- コメント
COMMENT ON TABLE product_mapping_master IS '商品番号マッピング基本表';
COMMENT ON TABLE platform_product_mapping IS '選択肢コード対応表（プラットフォーム別）';
COMMENT ON TABLE product_bundle_components IS 'セット・まとめ商品内訳テーブル';
COMMENT ON TABLE inventory_master IS '在庫マスター（単品商品のみ）';
COMMENT ON TABLE sales_master IS '売上マスター（共通コードベース）';

-- サンプルデータ
INSERT INTO product_mapping_master (common_code, product_name, product_type, price) VALUES
('CM042', 'ふわふわスモークサーモン', 'single', 800),
('CM043', 'スモークサーモンチップ', 'single', 800),
('BC001', 'おまかせセット', 'set_choice', 2400),
('PC001', 'サーモン3個セット', 'bundle_fixed', 2200);

INSERT INTO platform_product_mapping (platform_name, platform_product_code, common_code, platform_product_name) VALUES
('rakuten', '457326558401', 'CM042', 'ふわふわスモークサーモン'),
('rakuten', '457326558403', 'CM043', 'スモークサーモンチップ');

INSERT INTO inventory_master (common_code, current_stock, initial_stock, minimum_stock, reference_date) VALUES
('CM042', 119, 119, 10, '2025-02-10'),
('CM043', 122, 122, 10, '2025-02-10');

INSERT INTO product_bundle_components (bundle_common_code, component_common_code, quantity, is_selectable) VALUES
('BC001', 'CM042', 1, true),
('BC001', 'CM043', 1, true),
('PC001', 'CM042', 3, false);