# Claude Code プロジェクト固有の重要情報

## 【重要】Cloud Runデプロイ問題での反省（2025-08-03）

### 問題の詳細
**症状**: Cloud Runデプロイは成功するが、データが間違ったSupabaseプロジェクトに保存される

### なぜ2時間も苦戦したか

#### 1. 同じ失敗の繰り返し
- GitHub Secrets更新 → 3回
- Cloud Run環境変数再設定 → 4回  
- 再デプロイ → 5回以上
- **すべて効果なし**

#### 2. ユーザー指摘の軽視
ユーザーの発言:
- 「何回も同じことをしている」
- 「ハードコードされていないか確認して」

私の対応:
- 「ハードコードの可能性」に言及したが確認せず
- 環境変数設定を繰り返すだけ

#### 3. 実際の原因
```python
# main_cloudrun.py
os.environ.setdefault('SUPABASE_URL', 'https://jvkkvhdqtotbotjzngcv.supabase.co')
# ↑ 古いURLがハードコード
```

#### 4. あるべき対応
```bash
# 最初に実行すべきだった
grep -r "jvkkvhdqtotbotjzngcv" .
grep -r "SUPABASE_URL" .
cat Dockerfile.cloudrun
```

### 教訓
1. **コード確認を最優先**: 環境変数より先にコードを調査
2. **ユーザー指摘は即対応**: 「繰り返し」の指摘は危険信号
3. **思い込み排除**: 「設定は正しい」前提を疑う

**時間の浪費**: 2時間（実際は5分で解決可能だった）

## プロジェクト概要

### Supabase接続情報
- **プロジェクト名**: rakuten-sales-data
- **プロジェクトID**: equrcpeifogdrxoldkpe
- **URL**: https://equrcpeifogdrxoldkpe.supabase.co

### 環境変数
- SUPABASE_URL
- SUPABASE_KEY
- RAKUTEN_SERVICE_SECRET
- RAKUTEN_LICENSE_KEY

### デプロイ情報
- **プラットフォーム**: Google Cloud Run
- **CI/CD**: GitHub Actions
- **Dockerファイル**: Dockerfile.cloudrun
- **メインファイル**: main_cloudrun.py

## データベース構造

### 主要テーブル
1. **orders** - 注文情報
2. **order_items** - 注文商品詳細（楽天特有フィールド含む）
3. **product_master** - 商品マスタ（楽天SKU→共通コード）
4. **choice_code_mapping** - 選択肢コード対応表
5. **inventory** - 在庫テーブル
6. **package_components** - まとめ商品構成
7. **unprocessed_sales** - 未処理売上

### 楽天特有フィールド
- rakuten_variant_id
- rakuten_item_number
- choice_code
- item_type
- shop_item_code
- extended_rakuten_data (JSONB)

## Google Sheets連携

### 対象シート
1. **商品番号マッピング基本表** (gid=1290908701)
2. **選択肢コード対応表** (gid=1695475455)
3. **まとめ商品内訳テーブル** (gid=1670260677)

### スプレッドシートURL
https://docs.google.com/spreadsheets/d/1mLg1N0a1wubEIdKSouiW_jDaWUnuFLBxj8greczuS3E/

## 重要な実装ファイル

### コア機能
- `improved_mapping_system.py` - 在庫マッピングシステム
- `correct_choice_parser.py` - 選択肢コード抽出
- `google_sheets_csv_improved.py` - Google Sheets同期
- `scheduler.py` - 日次バッチ処理
- `daily_rakuten_processing.py` - 楽天注文処理

### API関連
- `api/rakuten_api.py` - 楽天API連携
- `main_cloudrun.py` - Cloud Runメインファイル

## Supabase Python Client API のトラブルシューティング

### よくあるエラーと修正方法

1. **`'SyncSelectRequestBuilder' object has no attribute 'or_'`**
   - **原因**: Supabase Python Clientの`or_()`構文の使用方法が間違っている
   - **間違った例**: `query.or_(f"column1.ilike.%{search}%,column2.ilike.%{search}%")`
   - **正しい修正**: `query.ilike('column1', f'%{search}%')` を使用
   - **または**: 複数条件の場合はクライアント側でフィルタリング

2. **`invalid input syntax for type integer: "column_name"`**
   - **原因**: SQL内での列同士の比較（`current_stock <= minimum_stock`）
   - **間違った例**: `query.lte('current_stock', 'minimum_stock')`
   - **正しい修正**: クライアント側でフィルタリング
   ```python
   items = [item for item in items if item['current_stock'] <= item['minimum_stock']]
   ```

3. **Supabase検索クエリのベストプラクティス**
   - **単一検索**: `query.ilike('column_name', f'%{search}%')`
   - **数値比較**: `query.lte('column_name', number_value)`
   - **複雑な条件**: サーバー側ではなくクライアント側で処理
   - **並び順**: `query.order('column_name', desc=False)`

4. **エラーハンドリングのパターン**
   ```python
   try:
       response = query.execute()
       items = response.data if response.data else []
       # クライアント側フィルタリング
       if complex_condition:
           items = [item for item in items if condition(item)]
   except Exception as e:
       return {"status": "error", "message": str(e)}
   ```

### API開発の重要なポイント
- **段階的テスト**: 基本機能→検索機能→フィルター機能の順でテスト
- **エラーレスポンス**: 常に200ステータスでエラー詳細を返す
- **クライアント側処理**: 複雑なSQL条件はPythonで処理する方が安全

## Docker & Cloud Run デプロイメントの重要事項

### Dockerfile の確認ポイント
1. **使用されるメインファイル**
   - `Dockerfile.cloudrun` では `main_cloudrun.py` が使用される
   - `CMD exec uvicorn main_cloudrun:app --host 0.0.0.0 --port $PORT`

2. **ハードコードされた環境変数の確認**
   - `main_cloudrun.py` 内の `os.environ.setdefault()` をチェック
   - 古いSupabase URLがハードコードされていないか必ず確認

3. **環境変数の優先順位**
   - GitHub Actions: `--set-env-vars` 
   - Cloud Run直接設定: `gcloud run services update`
   - コード内: `os.environ.setdefault()` (既存値がない場合のみ)
   - コード内: `os.environ['KEY'] = value` (強制上書き)

### トラブルシューティングの手順
1. **まずコードレベルのハードコードを確認** (`grep` コマンド使用)
2. **Dockerfileで使用されるメインファイルを確認**
3. **環境変数設定は最後の手段**

## トラブルシューティング

### よくある問題
1. **ハードコードされた値の確認**
   ```bash
   grep -r "古いURL" .
   grep -r "os.environ" .
   ```

2. **Dockerfileの確認**
   ```bash
   cat Dockerfile.cloudrun
   ```

3. **環境変数の優先順位**
   - コード内ハードコード > Cloud Run設定 > GitHub Secrets

### デバッグの順序
1. コード確認
2. Dockerfile確認
3. ログ確認
4. 環境変数確認（最後）