# Amazon在庫・売上管理システム

楽天システムと同じ構造でAmazonの注文・在庫・売上を管理するシステムです。

## システム概要

### データベース構造
- **amazon_orders**: Amazon注文データ
- **amazon_order_items**: Amazon注文商品詳細
- **amazon_product_master**: Amazon商品マスタ（SKU→共通コードマッピング）
- **amazon_inventory**: Amazon在庫管理
- **amazon_fba_inventory**: FBA在庫詳細

### 主要機能

#### 1. Amazon SP-API連携
- 注文データの自動取得
- FBA在庫情報の同期
- 商品マスタの管理

#### 2. 在庫同期システム
- 楽天システムと同じ共通在庫テーブルとの連携
- 売上に基づく自動在庫減算
- プラットフォーム横断の在庫管理

#### 3. 売上ダッシュボード
- 期間指定可能な売上集計
- 商品別売上分析
- 楽天との売上比較

## セットアップ

### 1. 依存関係のインストール
```bash
pip install -r requirements.txt
```

### 2. 環境変数設定
```bash
# Supabase
SUPABASE_URL=https://equrcpeifogdrxoldkpe.supabase.co
SUPABASE_KEY=your_supabase_key

# Amazon SP-API
AMAZON_REFRESH_TOKEN=your_refresh_token
AMAZON_CLIENT_ID=your_client_id
AMAZON_CLIENT_SECRET=your_client_secret
AMAZON_AWS_ACCESS_KEY=your_aws_access_key
AMAZON_AWS_SECRET_KEY=your_aws_secret_key
AMAZON_ROLE_ARN=your_role_arn
AMAZON_MARKETPLACE_ID=A1VC38T7YXB528  # 日本
```

### 3. データベースセットアップ
```bash
# Supabaseでテーブル作成
cat setup_amazon_tables.sql | supabase db reset
```

## 使用方法

### Amazon API連携
```python
from amazon_api import AmazonAPI

api = AmazonAPI()

# 最近7日間の注文を同期
results = api.sync_recent_orders(days_back=7)

# 在庫情報を同期
inventory_data = api.fetch_inventory()
inventory_results = api.sync_inventory_to_supabase(inventory_data)
```

### 在庫同期
```python
from amazon_inventory_sync import AmazonInventorySync

sync = AmazonInventorySync()

# 日次同期を実行
results = sync.process_daily_sync()
```

### 売上ダッシュボードAPI
```bash
# APIサーバー起動
python amazon_sales_api.py

# ダッシュボードデータ取得
curl "http://localhost:8001/api/amazon/sales/dashboard?start_date=2025-08-01&end_date=2025-08-19"

# 商品別売上
curl "http://localhost:8001/api/amazon/sales/products"

# 在庫状況
curl "http://localhost:8001/api/amazon/inventory/status"

# プラットフォーム比較
curl "http://localhost:8001/api/amazon/sales/comparison"
```

## API エンドポイント

### 売上関連
- `GET /api/amazon/sales/dashboard` - 売上ダッシュボード
- `GET /api/amazon/sales/products` - 商品別売上
- `GET /api/amazon/sales/comparison` - プラットフォーム比較

### 在庫関連
- `GET /api/amazon/inventory/status` - 在庫状況サマリー

## 楽天システムとの統合

### 共通在庫管理
- 同じ`inventory`テーブルを使用
- `common_code`による商品統一管理
- プラットフォーム別在庫フィールド追加

### 売上ダッシュボード統合
- 楽天とAmazonの合算売上表示
- プラットフォーム別内訳表示
- 期間指定可能な比較分析

## 注意事項

### Amazon SP-API認証
- 実際の運用にはAmazon Developer Centralでのアプリ登録が必要
- 適切なIAMロールとポリシーの設定が必要
- リクエスト制限（レート制限）に注意

### データ同期
- 初回同期時は大量データの処理に時間がかかる可能性
- 定期的な同期スケジュールの設定を推奨
- エラーハンドリングとリトライ機能の実装が重要

### 在庫管理
- Amazon FBAとセラー在庫の区別
- 返品・交換による在庫変動の考慮
- マルチマーケットプレイス対応（必要に応じて）

## トラブルシューティング

### よくある問題
1. **SP-API認証エラー**: 認証情報とIAMロールの確認
2. **データ同期失敗**: ネットワーク接続とAPI制限の確認
3. **在庫不整合**: マッピングテーブルの整合性確認

### ログ確認
```bash
# アプリケーションログ
tail -f app.log

# 同期処理ログ
python amazon_api.py  # 詳細ログ出力
```