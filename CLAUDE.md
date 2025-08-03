# Claude Code プロジェクト固有の重要情報

## 【重要】ユーザー指示の対応についての反省事項（2025-08-03）

### 問題のある対応パターン
1. **可能性として言及したことを実際に確認せずに、別のアプローチを繰り返す**
   - 例：「ハードコードされている可能性がある」と言ったにも関わらず、環境変数設定を何度も繰り返した
   - 結果：ユーザーが明確に「ハードコードをチェックしろ」と指示するまで実際の確認をしなかった

2. **同じ失敗を繰り返し、ユーザーの指示を軽視する**
   - GitHub Secretsの更新、Cloud Runの環境変数設定など、同じアプローチを複数回実行
   - ユーザーが「何回も同じことをしている」と指摘しても、根本原因の調査をしなかった

3. **最終的にDockerfile内の`main_cloudrun.py`に古いSupabase URL（`jvkkvhdqtotbotjzngcv`）がハードコードされていることが判明**

### 必須の対応改善事項
1. **ユーザーの指示は最優先で実行する** - 「可能性」として言及したことは即座に確認する
2. **同じアプローチを2回以上繰り返す前に、必ず根本原因を調査する**
3. **「何回も同じこと」「ループしている」という指摘があった時点で、必ずアプローチを変更する**
4. **コードの詳細確認（grep、ファイル検索）を最初に行う** - 環境変数などの設定変更は後回し

この反省を忘れず、今後は効率的で的確な対応を心がけること。

## Vercel Python デプロイメントの注意事項

### 重要な仕様
1. **Vercelは各Pythonファイルを個別のエンドポイントとして扱う**
   - `api/`フォルダ内の各`.py`ファイルが1つのエンドポイントになる
   - 例: `api/hello.py` → `https://domain.vercel.app/api/hello`

2. **1つのファイルに複数のルートを定義しても認識されない**
   - FastAPIで複数の`@app.get()`を定義しても、最初のルートのみが有効
   - 各エンドポイントには個別のファイルが必要

### 正しい構造
```
api/
├── index.py    # /api エンドポイント
├── python.py   # /api/python エンドポイント
├── test.py     # /api/test エンドポイント
└── hello.py    # /api/hello エンドポイント
```

### 間違った例（動作しない）
```python
# api/index.py
@app.get("/api")        # ✅ これは動作する
def root(): ...

@app.get("/api/python") # ❌ これは無視される
def python(): ...
```

### 環境変数
- SUPABASE_URL
- SUPABASE_KEY
- RAKUTEN_SERVICE_SECRET
- RAKUTEN_LICENSE_KEY

### デプロイ時の設定
- Root Directory: 空欄（リポジトリのルート）
- Framework Preset: Other
- Build Settings: デフォルトのまま

### トラブルシューティング
- 404エラーが発生する場合は、各エンドポイントが個別のファイルになっているか確認
- Vercelダッシュボードの Functions タブで登録された関数を確認
- キャッシュの問題がある場合は、Redeploy時に「Use existing Build Cache」のチェックを外す

### Vercelアカウントとデプロイメントに関する重要事項

1. **GitコミットのAuthor確認**
   - Gitの設定（user.name, user.email）が正しいか必ず確認
   - 間違ったアカウントでコミットすると、別のVercelプロジェクトにデプロイされる可能性がある
   - 例: `maruyamadr` vs `naoota12345678`

2. **デプロイメントURLの種類**
   - **Production URL**: `https://[project-name].vercel.app` （固定）
   - **Preview URL**: `https://[project-name]-[random-string].vercel.app` （デプロイごとに変わる）
   - 新しい機能をテストする場合は、最新のPreview URLを使用

3. **正しいプロジェクトの確認方法**
   - Vercelダッシュボードで正しいアカウントでログインしているか確認
   - プロジェクト名とGitHubリポジトリが一致しているか確認
   - デプロイ履歴でコミットAuthorが正しいか確認

4. **複数のVercelプロジェクトが存在する場合**
   - 古いプロジェクトは削除して、正しいアカウントで新規作成
   - 環境変数を再設定することを忘れずに

## データベーススキーマ情報

### 最新のデータベース構造
- **ファイル**: `/DATABASE_SCHEMA_CURRENT.md`
- **内容**: 現在のordersテーブル、order_itemsテーブルの構造
- **更新**: 2025-08-02 楽天注文同期エラー調査結果

### 楽天注文同期の問題と解決策
- **問題**: ordersテーブルに楽天API必須カラムが不足
- **不足カラム**: `coupon_amount`, `shipping_fee`, `payment_method`, `order_status`, `point_amount`, `request_price`, `deal_price`, `platform_data`, `updated_at`
- **解決**: `DATABASE_SCHEMA_CURRENT.md`記載のALTER文でSupabaseに手動追加

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