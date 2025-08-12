-- product_masterテーブルにGoogle Sheets対応カラムを追加
-- 既存のカラムは変更せず、新しいカラムのみ追加

ALTER TABLE product_master ADD COLUMN IF NOT EXISTS sequence_number INTEGER;
ALTER TABLE product_master ADD COLUMN IF NOT EXISTS jan_ean_code TEXT;
ALTER TABLE product_master ADD COLUMN IF NOT EXISTS colorMe_id TEXT;
ALTER TABLE product_master ADD COLUMN IF NOT EXISTS smaregi_id TEXT;
ALTER TABLE product_master ADD COLUMN IF NOT EXISTS yahoo_product_id TEXT;
ALTER TABLE product_master ADD COLUMN IF NOT EXISTS amazon_asin TEXT;
ALTER TABLE product_master ADD COLUMN IF NOT EXISTS mercari_product_id TEXT;
ALTER TABLE product_master ADD COLUMN IF NOT EXISTS remarks TEXT;