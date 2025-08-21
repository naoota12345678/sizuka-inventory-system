# 在庫同期システム 完全自動化 - 引継ぎ仕様書

## 📋 現在の状況（2025-08-21 完了）

### ✅ 完了事項

1. **Amazon SP-API同期スクリプト修正**
   - ファイル: `amazon_sp_api_sync.py`
   - 修正内容: 環境変数未定義エラー解決、クラス初期化完全化
   - 結果: 正常な環境変数チェックと適切なエラー表示

2. **楽天日次同期スクリプト修正**
   - ファイル: `daily_sync.py`
   - 修正内容: Supabase認証情報フォールバック追加
   - 結果: ローカルテスト実行可能、GitHub Actions対応

3. **製造在庫日次同期をGitHub Actionsに追加**
   - ファイル: `.github/workflows/daily-sync.yml`
   - 追加内容: `daily_manufacturing_sync.py --auto`
   - 設定: 毎日朝3時（日本時間）自動実行

4. **実行時刻の最適化**
   - 変更: 朝9時 → 朝3時
   - 理由: 前日分データの早朝処理

## 🔄 毎日3時の自動同期システム

### GitHub Actions実行内容（cron: '0 18 * * *' = JST 3:00）

```yaml
1. Keep Supabase Alive - データベース接続維持
2. Sync Rakuten Orders - 楽天注文同期（前日分）
3. Sync Amazon Orders - Amazon注文同期（前日分）
4. Sync Manufacturing Inventory - 製造在庫同期（前日分）
```

### 各同期の詳細

**楽天注文同期 (`daily_sync.py`)**
- API: 楽天 v2.0 API
- 処理: 前日の注文データ取得、在庫減算
- 認証: ESA認証方式

**Amazon注文同期 (`amazon_sp_api_sync.py daily`)**
- API: Amazon SP-API
- 処理: 前日の注文データ取得、在庫減算
- 認証: SP-API認証（OAuth）

**製造在庫同期 (`daily_manufacturing_sync.py --auto`)**
- データソース: Google Sheets（製造データ）
- 処理: スマレジIDベースのマッピング、在庫増加
- マッピング: product_master、choice_code_mapping使用

## 📊 次回実行時の確認事項

### 🕒 今晩（2025-08-21 → 2025-08-22 3:00 AM）の確認ポイント

1. **GitHub Actionsログ確認**
   ```
   URL: https://github.com/naoota12345678/sizuka-inventory-system/actions
   確認項目:
   - 4つの同期ステップすべてが緑✅
   - エラーログの有無
   - 実行時間の妥当性
   ```

2. **Supabaseデータ確認**
   ```python
   # 実行後のデータ確認コマンド（コピペ用）
   cd "C:\Users\naoot\Desktop\ｐ\sizukatest\rakuten-order-sync"
   python -c "
   from supabase import create_client
   import os
   os.environ['SUPABASE_URL'] = 'https://equrcpeifogdrxoldkpe.supabase.co'
   os.environ['SUPABASE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ'
   supabase = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_KEY'])
   
   # 最新の注文データ確認
   recent_orders = supabase.table('orders').select('order_number, order_date, platform').order('created_at', desc=True).limit(10).execute()
   print('最新注文データ:')
   for order in recent_orders.data:
       print(f'  {order[\"order_date\"][:10]}: {order[\"order_number\"]} ({order.get(\"platform\", \"unknown\")})')
   
   # 在庫変動確認
   inventory = supabase.table('inventory').select('common_code, current_stock, last_updated').order('last_updated', desc=True).limit(10).execute()
   print('\\n最新在庫変動:')
   for item in inventory.data:
       print(f'  {item[\"common_code\"]}: {item[\"current_stock\"]}個 (更新: {item[\"last_updated\"][:16]})')
   "
   ```

## 🚀 次回タスク：過去データ反映計画

### ⚠️ 自動同期成功確認後に実行

#### Phase 1: 製造在庫過去データ再構築

**目的**: 手動設定済みの製造在庫を正確なGoogle Sheetsデータで再構築

**実行手順**:
1. **現在の製造在庫バックアップ**
   ```python
   # 実行前バックアップ（コピペ用）
   python -c "
   from supabase import create_client
   import json, os
   os.environ['SUPABASE_URL'] = 'https://equrcpeifogdrxoldkpe.supabase.co'
   os.environ['SUPABASE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ'
   supabase = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_KEY'])
   
   backup = supabase.table('inventory').select('*').execute()
   with open('inventory_backup_' + str(int(__import__('time').time())) + '.json', 'w', encoding='utf-8') as f:
       json.dump(backup.data, f, ensure_ascii=False, indent=2)
   print(f'バックアップ完了: {len(backup.data)}件')
   "
   ```

2. **Google Sheets製造履歴データ取得期間設定**
   - 対象期間: 2025-02-10 ～ 2025-08-20
   - データソース: Google Sheets製造データ
   - マッピング: スマレジID → 共通コード

3. **製造在庫履歴再構築実行**
   ```python
   # 期間指定での製造在庫再構築
   python daily_manufacturing_sync.py --historical --start-date 2025-02-10 --end-date 2025-08-20
   ```

#### Phase 2: 過去売上データ履歴反映

**目的**: 楽天・Amazonの過去注文データによる在庫減算を正確に反映

**実行手順**:
1. **現在のorder_items確認**
   ```python
   # 既存データ範囲確認
   python -c "
   from supabase import create_client
   import os
   os.environ['SUPABASE_URL'] = 'https://equrcpeifogdrxoldkpe.supabase.co'
   os.environ['SUPABASE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ'
   supabase = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_KEY'])
   
   # 既存order_itemsの期間確認
   orders = supabase.table('orders').select('order_date').order('order_date').execute()
   if orders.data:
       print(f'最古の注文: {orders.data[0][\"order_date\"][:10]}')
       print(f'最新の注文: {orders.data[-1][\"order_date\"][:10]}')
       print(f'総注文数: {len(orders.data)}件')
   "
   ```

2. **在庫減算履歴処理実行**
   ```python
   # 改良マッピングシステムでの一括処理
   python improved_mapping_system.py --historical --apply-inventory-changes
   ```

#### Phase 3: 整合性確認とダッシュボード検証

**確認項目**:
1. 在庫数の論理チェック（負の在庫なし）
2. マッピング成功率100%確認
3. 売上ダッシュボードの期間別表示
4. 在庫ダッシュボードの商品名表示

## 🔧 重要ファイルとシステム構成

### 主要ファイル

```
## 日次同期システム
- daily_sync.py                    # 楽天注文同期
- amazon_sp_api_sync.py           # Amazon注文同期  
- daily_manufacturing_sync.py     # 製造在庫同期

## マッピングシステム
- improved_mapping_system.py      # 在庫マッピング統合システム
- correct_choice_parser.py        # 選択肢コード抽出

## GitHub Actions
- .github/workflows/daily-sync.yml # 毎日3時自動実行

## ダッシュボード
- main_cloudrun.py               # Cloud Run API（売上・在庫）
- dashboard.html                 # フロントエンド
```

### データベース構造

```sql
## 主要テーブル
- orders              # 注文情報
- order_items         # 注文商品詳細
- inventory           # 在庫テーブル
- product_master      # 楽天SKU→共通コードマッピング
- choice_code_mapping # 選択肢コード→共通コードマッピング
```

### 環境情報

```
## Supabase
- URL: https://equrcpeifogdrxoldkpe.supabase.co
- プロジェクト: rakuten-sales-data

## Cloud Run
- URL: https://sizuka-inventory-system-1025485420770.asia-northeast1.run.app
- デプロイ: GitHub Actions自動

## Google Sheets
- 製造データ: 1YFFgRm2uYQ16eNx2-ILuM-_4dTD09OP2gtWbeu5EeAQ
- マッピング: 1mLg1N0a1wubEIdKSouiW_jDaWUnuFLBxj8greczuS3E
```

## 🎯 成功判定基準

### 今晩の自動同期成功判定
- [ ] GitHub Actions 4ステップすべて緑✅
- [ ] エラーログなし
- [ ] 新規注文データ取得確認
- [ ] 在庫変動記録確認

### 過去データ反映完了判定
- [ ] 製造在庫マッピング成功率100%
- [ ] 売上在庫減算処理完了
- [ ] 在庫数の論理整合性確認
- [ ] ダッシュボード表示正常

## 📞 トラブルシューティング

### よくある問題と対処法

1. **GitHub Actions失敗時**
   ```
   - ログ確認: Actions タブ → 該当ワークフロー → 詳細表示
   - 再実行: "Re-run failed jobs" ボタン
   - 手動実行: "Run workflow" → "workflow_dispatch"
   ```

2. **環境変数エラー時**
   ```
   - GitHub Secrets確認: Settings → Secrets and variables → Actions
   - 必要な変数: SUPABASE_URL, SUPABASE_KEY, RAKUTEN_*, AMAZON_*
   ```

3. **Supabase接続エラー時**
   ```
   - プロジェクト状態確認: Supabaseダッシュボード
   - API制限確認: 利用量モニタリング
   ```

## 🔄 次回チャット開始時のアクション

1. **今晩の結果確認** - 上記の確認コマンド実行
2. **成功時** → Phase 1: 製造在庫再構築開始
3. **失敗時** → エラー解析とシステム修正
4. **完了時** → 在庫システム完全統合完了

---

**最終更新**: 2025-08-21
**次回確認予定**: 2025-08-22 朝（自動同期実行後）
**担当システム**: 在庫同期完全自動化システム