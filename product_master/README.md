# Product Master Module

商品マスターデータの管理とGoogle Sheets同期機能を提供するモジュールです。

## 機能

1. **データベース初期化** (`db_setup.py`)
   - 商品マスター関連テーブルの存在確認
   - SQLスクリプトの生成

2. **Google Sheets同期** (`sheets_sync.py`)
   - スプレッドシートからの自動データ取得
   - 商品マスター、選択肢コード、まとめ商品内訳の同期

3. **CSV インポート** (`csv_import.py`)
   - CSVファイルからの手動インポート
   - Google Sheets が使えない場合の代替手段

## セットアップ

### 1. Supabaseでテーブルを作成

`create_tables.sql` の内容をSupabaseダッシュボードのSQLエディタで実行してください。

### 2. 環境変数の設定

`.env` ファイルに以下を追加：

```env
# Google Sheets同期用
PRODUCT_MASTER_SPREADSHEET_ID=your_spreadsheet_id
GOOGLE_CREDENTIALS_FILE=path/to/credentials.json
# または
GOOGLE_SERVICE_ACCOUNT_JSON={"type": "service_account", ...}
```

### 3. Google認証の設定

#### 方法1: サービスアカウント認証ファイル
1. Google Cloud Consoleでサービスアカウントを作成
2. 認証情報JSONファイルをダウンロード
3. `GOOGLE_CREDENTIALS_FILE` に認証ファイルのパスを設定

#### 方法2: 環境変数に直接設定
1. 認証情報JSONの内容を `GOOGLE_SERVICE_ACCOUNT_JSON` に設定
2. JSON全体を1行の文字列として設定

### 4. スプレッドシートの共有設定

サービスアカウントのメールアドレスに対して、スプレッドシートの閲覧権限を付与してください。

## 使用方法

### APIエンドポイント経由での使用

1. **データベース状態の確認**
   ```bash
   curl http://localhost:8000/check-database-setup
   ```

2. **Google Sheetsからの同期**
   ```bash
   curl -X POST http://localhost:8000/sync-product-master
   ```

3. **商品在庫の確認**
   ```bash
   curl http://localhost:8000/product-stock/CM001
   ```

### コマンドラインからの使用

1. **CSVファイルからのインポート**
   ```bash
   python product_master/csv_import.py
   ```

2. **Google Sheetsからの同期**
   ```bash
   python product_master/sheets_sync.py
   ```

## データ構造

### 商品コード体系
- **CM**: 単品商品 (CM001, CM002...)
- **BC**: セット商品 (BC001, BC002...)
- **PC**: まとめ商品 (PC001, PC002...)

### 商品タイプ
- **単品**: 通常の個別商品
- **セット(選択)**: ユーザーが選択できるセット
- **セット(固定)**: 内容固定のセット
- **まとめ(固定)**: 同一商品の複数個セット
- **まとめ(複合)**: 複数種類を含むセット

## トラブルシューティング

### テーブルが作成されない場合
1. Supabaseダッシュボードで `create_tables.sql` を実行
2. エラーが出る場合は、既存テーブルとの競合を確認

### Google Sheets同期エラー
1. スプレッドシートIDが正しいか確認
2. サービスアカウントに共有権限があるか確認
3. シート名が正しいか確認（商品番号マッピング基本表、選択肢コード対応表、まとめ商品内訳テーブル）

### 在庫計算が正しくない場合
1. `common_code` が正しく設定されているか確認
2. まとめ商品の構成品が正しく登録されているか確認
3. 在庫テーブルの `common_code` が更新されているか確認
