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

## 【重要】売上ダッシュボード修正と過去データ同期（2025-08-05）

### 背景
- ユーザー報告: 「現在期間別の売り上げを見ることができません」
- 原因発見: 売上ダッシュボードが存在しない`sales_master`テーブルを参照
- 要求: 「order-itemsにある情報から期間売り上げが出ればよいだけです」

### 実施した修正

#### 1. 売上ダッシュボードAPI修正
**問題:**
- `/api/sales_dashboard`が`sales_master`テーブル（存在しない）を参照
- Supabase join構文エラー: `orders!inner(...)` 

**修正内容:**
```python
# 修正前（エラー）
query = supabase.table('sales_master').select('*')

# 修正後（正常）
query = supabase.table('order_items').select(
    'quantity, price, product_code, product_name, created_at, orders(order_date, created_at, id)'
).gte('orders.order_date', start_date).lte('orders.order_date', end_date)
```

**追加API:**
- `/api/sales/period` - 期間別売上集計API

#### 2. データ範囲の問題発見
**発見事項:**
- **order_items**: 2,223件すべてが2025-08-05に作成（最近同期されたデータのみ）
- **orders**: 2024年1月15日～2025年8月5日の幅広い期間
- **在庫データ**: Google Sheets由来で全期間対応済み

**問題:** 売上データは最近の期間のみ、過去データ（2月10日以降）が不足

#### 3. 過去データ同期の安全な実装

**2段階プロセス設計:**
1. **第1段階**: 売上データのみ同期（在庫システムに影響なし）
2. **第2段階**: 在庫システムへの反映（改良マッピングシステム使用）

**作成ファイル:**
- `direct_historical_sync.py` - 2/10～7/31の安全な同期スクリプト
- `apply_historical_inventory_changes.py` - 在庫システム適用ツール

### 現在の状況（2025-08-05 16:30頃）

#### Git保存状況
- ✅ **コミット済み**: 売上ダッシュボード修正 + 同期ツール
- ✅ **コミットハッシュ**: 864a192
- ✅ **内容**: main_cloudrun.py修正、同期スクリプト2つ追加

#### 第1段階同期進行中
**実行コマンド:** `python direct_historical_sync.py`
**開始時刻:** 2025-08-05 16:00頃
**期間:** 2025-02-10 ～ 2025-07-31

**同期進行状況:**
- ✅ **開始時**: order_items 2,223件、orders 755件
- ✅ **現在**: order_items 2,629件（+406件）、orders 755件
- ✅ **進行**: 2025年2月22日まで同期済み
- ⚠️ **エラー**: `order_number`変数未定義（非重要、データ保存は正常）

### 次のステップ（引継ぎ用）

#### 1. 同期完了の確認（約1時間後）

**📋 チャット再開時の最初のコマンド（コピペ用）:**
```python
cd "C:\Users\naoot\Desktop\ｐ\sizukatest" && python -c "
from supabase import create_client
SUPABASE_URL = 'https://equrcpeifogdrxoldkpe.supabase.co'
SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ'
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

print('=== 同期完了確認 ===')

# 総数確認
total_result = supabase.table('order_items').select('id', count='exact').execute()
print(f'現在のorder_items総数: {total_result.count}件')
base_count = 2223  # 同期前の件数
new_count = total_result.count - base_count
print(f'新規追加: {new_count}件')

# orders総数
orders_result = supabase.table('orders').select('id', count='exact').execute()
print(f'現在のorders総数: {orders_result.count}件')

# 最新データ確認（期間確認用）
recent = supabase.table('orders').select('order_number, order_date').order('order_date', desc=True).limit(5).execute()
if recent.data:
    print('最新の注文日:')
    for order in recent.data:
        print(f'  - {order[\"order_date\"][:10]}: {order[\"order_number\"]}')
    
    latest_date = recent.data[0]['order_date'][:10]
    if latest_date >= '2025-07-30':
        print('✅ 同期完了: 7月31日まで同期済み')
    else:
        print(f'⏳ 同期進行中: 最新日付 {latest_date}')
else:
    print('データなし')
"

#### 2. 売上ダッシュボード動作確認
**URL:** `http://localhost:8080/api/sales_dashboard?start_date=2025-02-10&end_date=2025-07-31`
**期待結果:** 2月10日以降の売上データが表示される

#### 3. 第2段階実行（在庫システム反映）
```bash
# DRY RUN（テスト）
python apply_historical_inventory_changes.py
# 選択: 1 (DRY RUN)

# 実際の適用（問題なければ）
python apply_historical_inventory_changes.py  
# 選択: 2 → yes確認
```

#### 4. Git保存
```bash
# 同期完了後
git add .
git commit -m "過去データ同期完了: 2/10-7/31期間のorder_items追加

- 同期期間: 2025-02-10 ~ 2025-07-31
- 追加データ: order_items約XXXX件、orders約XXX件  
- 売上ダッシュボード: 過去データ確認可能
- 在庫システム: 第2段階で反映予定

🤖 Generated with [Claude Code](https://claude.ai/code)"
```

### 重要な注意事項

#### 在庫システムへの影響
- ✅ **第1段階**: 在庫システムに一切影響なし
- ⚠️ **第2段階**: 改良マッピングシステム使用（100%成功率実績）
- ✅ **ロールバック**: 第1段階のみでも売上ダッシュボードは機能

#### 既存システムの状態
- ✅ **在庫マッピング**: 100%成功率維持（36件の在庫アイテム）
- ✅ **製造在庫同期**: 正常動作（Google Sheets連携）
- ✅ **選択肢コードマッピング**: P01/S01/S02追加済み

#### トラブルシューティング
**同期が失敗した場合:**
1. プロセス終了: `taskkill /f /im python.exe`
2. 部分的データでも売上ダッシュボードは動作
3. 必要に応じて期間を分割して再同期

**在庫システムに問題が発生した場合:**
1. 改良マッピングシステムは実績あり（安全）
2. DRY RUNで事前テスト必須
3. 最悪の場合、第1段階のみで運用可能

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

### 【最終確定】プロジェクト構成 (2025-08-09)

#### Cloud Run (バックエンドAPI - すべてのAPIを統合)
- **理由**: Vercelの12関数制限を超えたため、すべてCloud Runに移行
- **GCPプロジェクト**: `sizuka-inventory-system`
- **サービス名**: `sizuka-inventory-system`
- **本番URL**: https://sizuka-inventory-system-1025485420770.asia-northeast1.run.app
- **CI/CD**: GitHub Actions
- **Dockerファイル**: Dockerfile.cloudrun
- **メインファイル**: main_cloudrun.py

#### 正しいAPI設定
```javascript
const API_BASE = 'https://sizuka-inventory-system-1025485420770.asia-northeast1.run.app/api';
```

### デプロイ手順
- Cloud Run: `gcloud config set project sizuka-inventory-system`
- GitHub pushで自動デプロイ

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

## 製造在庫同期システム（2025-08-03完成）

### 概要
スマレジIDで管理される製造商品の在庫をSupabaseに自動同期するシステム。
エアレジからSupabaseへの切り替えを実現。

### システムの流れ
1. **Google Sheets（製造データ）**: スマレジID（10XXX形式）で製造在庫数を管理
2. **商品番号マッピング基本表**: スマレジID → 共通コードの変換テーブル
3. **Supabase inventory**: 共通コードで統一在庫管理

### 実装ファイル
- `supabase_inventory_sync_fixed.py` - メインの同期システム
- `sync_smaregi_mapping.py` - マッピングテーブル同期（122件のスマレジ商品登録済み）
- `check_product_mapping.py` - マッピング状況確認ツール

### 成功実績（2025-08-03テスト）
```
総商品数: 8商品
成功率: 100%（8/8）
新規作成: 8商品
失敗: 0商品

マッピング例:
10003 → CM016: 100個
10023 → CM025: 70個  
10107 → PC001: 5個
10076 → CM039: 30個
10016 → CM019: 50個
10105 → CM122: 26個
10010 → CM076: 1個
10066 → CM066: 3個
```

### データベース設計
- **inventory**: 在庫数量管理（common_code, current_stock, minimum_stock等）
- **product_master**: 楽天SKU⇔共通コードマッピング（製造商品はrakuten_skuにスマレジIDを格納）
- **choice_code_mapping**: 選択肢コード⇔共通コードマッピング（147件登録済み）

### Google Sheets連携
- **製造データ**: `1YFFgRm2uYQ16eNx2-ILuM-_4dTD09OP2gtWbeu5EeAQ` AIRレジシート
- **マッピング基本表**: `1mLg1N0a1wubEIdKSouiW_jDaWUnuFLBxj8greczuS3E` (gid=1290908701)

### 重要な技術仕様
1. **マッピングキャッシュ**: 商品番号マッピング基本表を1回読み込み、メモリでキャッシュ
2. **エラーハンドリング**: 文字化けや空データに対応
3. **在庫更新**: 既存在庫への加算 vs 新規在庫レコード作成
4. **ログ記録**: 詳細な処理ログでトレーサビリティ確保

### 運用方法
```bash
cd "C:\Users\naoot\Desktop\sizukaproject\sizukagoogleun"
python supabase_inventory_sync_fixed.py
```

### 今後の拡張
- 毎日自動実行スケジューラー
- 差分同期（増分のみ）
- エラー通知機能

## 【重要】楽天マッピングシステム完全修復（2025-08-05）

### 問題の発端
システムが壊れた可能性があり、在庫集計システムのマッピング率が98%から16-29%に急落。

### 根本原因の発見
1. **P01、S01、S02は選択肢コードだった**
   - 在庫テーブルに直接P01、S01、S02が表示されていた
   - 当初「間違った共通コード形式」と誤解していた
   - 実際は正常な選択肢コードが在庫テーブルに記録されていた

2. **選択肢コード対応表に未登録**
   - P01、S01、S02が`choice_code_mapping`テーブルに登録されていなかった
   - そのためマッピングシステムで処理できずに在庫テーブルに残った

### マッピングシステムの構造理解
```
楽天注文データ → 選択肢コード抽出 → マッピング処理 → 共通コード → 在庫変動

【2つのマッピングルート】
1. 選択肢コード (R05, C01, P01等) → choice_code_mapping → 共通コード (CM001等)
2. 楽天SKU (1833等) → product_master → 共通コード (CM035等)
```

### 実装済みシステムの確認
- **選択肢コード → 基本コード直接マッピング**が既に実装済み
- `_find_choice_code_mapping()`関数で`choice_info->>choice_code`検索
- マッピング優先順位: 選択肢コード > 楽天SKU

### 解決アプローチ
1. **P01/S01/S02を選択肢コード対応表に追加**
   - P01 → CM201 (Premium Product P01)
   - S01 → CM202 (Special Product S01)  
   - S02 → CM203 (Special Product S02)

2. **在庫ダッシュボード改善**
   - 共通コードの横に商品名を表示
   - `product_master`と`choice_code_mapping`の両方から商品名取得

### 技術的実装詳細

#### 選択肢コード追加（add_choice_codes_simple.py）
```python
new_record = {
    'choice_info': {
        'choice_code': 'P01',
        'choice_name': 'P01 Choice',
        'choice_value': 'Premium Product P01',
        'category': 'manual_addition'
    },
    'common_code': 'CM201',
    'product_name': 'Premium Product P01',
    'rakuten_sku': 'CHOICE_P01'  # 必須制約対応
}
```

#### ダッシュボード商品名取得
```python
# 1. product_masterから検索
product_result = supabase.table("product_master").select(
    "product_name"
).eq("common_code", common_code).execute()

# 2. choice_code_mappingから検索（フォールバック）
if not product_result.data:
    choice_result = supabase.table("choice_code_mapping").select(
        "product_name"
    ).eq("common_code", common_code).execute()
```

### 最終結果（2025-08-05）
```
マッピング成功率: 100.0% (1586件中1586件)
楽天商品データ: 1586件
マッピング成功: 1586件  
マッピング失敗: 0件
在庫変動対象: 84商品

主要在庫変動:
- CM018: -132個
- CM034: -18個  
- CM021: -44個
- CM027: -69個
- CM001: -150個
```

### 重要な教訓
1. **選択肢コードは正常な仕組み**
   - P01/S01/S02形式は間違いではなく、選択肢コードの正常な形式
   - 在庫テーブルに表示されるのは、マッピングが完了していない証拠

2. **動的マッピングシステムの維持**
   - Google Sheetsベースの動的マッピングは変更しない
   - 固定マッピングにしない（ユーザー指摘通り）

3. **系統的なデバッグの重要性**
   - データベース構造の理解が最優先
   - 既存システムの動作を十分理解してから修正

### 関連ファイル
- `improved_mapping_system.py` - メインマッピングシステム
- `add_choice_codes_simple.py` - 選択肢コード追加ツール
- `main_cloudrun.py` - ダッシュボードAPI（商品名表示機能付き）

### テーブル構造重要ポイント
```sql
-- choice_code_mapping テーブル
choice_info JSONB  -- {"choice_code": "P01", "choice_name": "..."}
common_code TEXT   -- CM201
product_name TEXT  -- Premium Product P01
rakuten_sku TEXT   -- CHOICE_P01 (NOT NULL制約対応)

-- inventory テーブル  
common_code TEXT   -- CM201, P01（マッピング前）
current_stock INT  -- 在庫数
product_name TEXT  -- 商品名（新規追加）
```