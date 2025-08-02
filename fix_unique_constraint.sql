-- ordersテーブルにUNIQUE制約を追加
-- 楽天注文同期のON CONFLICTエラーを修正

-- order_numberに対するUNIQUE制約を追加
ALTER TABLE orders ADD CONSTRAINT unique_order_number UNIQUE (order_number);

-- 既存の重複データがある場合は事前に削除が必要
-- 重複確認クエリ
SELECT order_number, COUNT(*) as count 
FROM orders 
GROUP BY order_number 
HAVING COUNT(*) > 1;