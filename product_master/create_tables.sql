-- 商品マスター関連テーブル作成SQL
-- Supabaseダッシュボードで実行してください

-- 1. 商品マスターテーブル
CREATE TABLE IF NOT EXISTS product_master (
    id SERIAL PRIMARY KEY,
    common_code VARCHAR(10) UNIQUE NOT NULL,
    jan_code VARCHAR(13),
    product_name VARCHAR(255) NOT NULL,
    product_type VARCHAR(20) NOT NULL,
    rakuten_sku VARCHAR(50),
    colorme_id VARCHAR(50),
    smaregi_id VARCHAR(50),
    yahoo_id VARCHAR(50),
    amazon_asin VARCHAR(50),
    mercari_id VARCHAR(50),
    rakuten_parent_sku VARCHAR(50),
    rakuten_choice_code VARCHAR(10),
    remarks TEXT,
    is_limited BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. 選択肢コード対応表
CREATE TABLE IF NOT EXISTS choice_code_mapping (
    id SERIAL PRIMARY KEY,
    choice_code VARCHAR(10) UNIQUE NOT NULL,
    common_code VARCHAR(10) NOT NULL,
    jan_code VARCHAR(13),
    rakuten_sku VARCHAR(50),
    product_name VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (common_code) REFERENCES product_master(common_code) ON DELETE CASCADE
);

-- 3. セット商品構成テーブル
CREATE TABLE IF NOT EXISTS bundle_components (
    id SERIAL PRIMARY KEY,
    bundle_code VARCHAR(10) NOT NULL,
    component_code VARCHAR(10) NOT NULL,
    is_selectable BOOLEAN DEFAULT FALSE,
    selection_group VARCHAR(50),
    required_count INTEGER DEFAULT 1,
    display_order INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (bundle_code) REFERENCES product_master(common_code) ON DELETE CASCADE,
    FOREIGN KEY (component_code) REFERENCES product_master(common_code) ON DELETE CASCADE,
    UNIQUE(bundle_code, component_code)
);

-- 4. まとめ商品構成テーブル
CREATE TABLE IF NOT EXISTS package_components (
    id SERIAL PRIMARY KEY,
    detail_id INTEGER,
    package_code VARCHAR(10) NOT NULL,
    package_name VARCHAR(255),
    component_code VARCHAR(10) NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    remarks TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (package_code) REFERENCES product_master(common_code) ON DELETE CASCADE,
    FOREIGN KEY (component_code) REFERENCES product_master(common_code) ON DELETE CASCADE
);

-- 5. インデックスの作成
CREATE INDEX IF NOT EXISTS idx_product_master_common_code ON product_master(common_code);
CREATE INDEX IF NOT EXISTS idx_product_master_product_type ON product_master(product_type);
CREATE INDEX IF NOT EXISTS idx_product_master_rakuten_sku ON product_master(rakuten_sku);
CREATE INDEX IF NOT EXISTS idx_choice_code_mapping_choice_code ON choice_code_mapping(choice_code);
CREATE INDEX IF NOT EXISTS idx_bundle_components_bundle_code ON bundle_components(bundle_code);
CREATE INDEX IF NOT EXISTS idx_package_components_package_code ON package_components(package_code);

-- 6. 在庫テーブルの拡張
ALTER TABLE inventory 
ADD COLUMN IF NOT EXISTS common_code VARCHAR(10);

-- 7. 在庫ビューの作成
CREATE OR REPLACE VIEW available_stock_view AS
WITH component_stock AS (
    -- 単品の在庫
    SELECT 
        pm.common_code,
        pm.product_name,
        pm.product_type,
        COALESCE(i.current_stock, 0) as available_stock
    FROM product_master pm
    LEFT JOIN inventory i ON pm.common_code = i.common_code
    WHERE pm.product_type = '単品'
    
    UNION ALL
    
    -- まとめ商品の在庫（構成品の在庫から計算）
    SELECT 
        pm.common_code,
        pm.product_name,
        pm.product_type,
        CASE 
            WHEN MIN(FLOOR(COALESCE(i.current_stock, 0) / pc.quantity)) IS NULL THEN 0
            ELSE MIN(FLOOR(COALESCE(i.current_stock, 0) / pc.quantity))
        END as available_stock
    FROM product_master pm
    JOIN package_components pc ON pm.common_code = pc.package_code
    LEFT JOIN inventory i ON pc.component_code = i.common_code
    WHERE pm.product_type IN ('まとめ(固定)', 'まとめ(複合)')
    GROUP BY pm.common_code, pm.product_name, pm.product_type
    
    UNION ALL
    
    -- セット商品の在庫（固定構成品の最小在庫）
    SELECT 
        pm.common_code,
        pm.product_name,
        pm.product_type,
        CASE 
            WHEN MIN(COALESCE(i.current_stock, 0)) IS NULL THEN 0
            ELSE MIN(COALESCE(i.current_stock, 0))
        END as available_stock
    FROM product_master pm
    JOIN bundle_components bc ON pm.common_code = bc.bundle_code
    LEFT JOIN inventory i ON bc.component_code = i.common_code
    WHERE pm.product_type IN ('セット(固定)', 'セット(選択)')
      AND bc.is_selectable = FALSE
    GROUP BY pm.common_code, pm.product_name, pm.product_type
)
SELECT * FROM component_stock;

-- 8. 更新日時の自動更新トリガー
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_product_master_updated_at BEFORE UPDATE
    ON product_master FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_choice_code_mapping_updated_at BEFORE UPDATE
    ON choice_code_mapping FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_bundle_components_updated_at BEFORE UPDATE
    ON bundle_components FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_package_components_updated_at BEFORE UPDATE
    ON package_components FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
