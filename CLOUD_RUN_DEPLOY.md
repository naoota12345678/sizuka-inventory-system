# Google Cloud Run デプロイ手順

## 前提条件
- Google Cloud project "sizuka-inventory-system" が作成済み
- 課金アカウントが設定済み (Cloud Run使用に必要)
- Google Cloud SDK がインストール済み

## 1. 課金設定
Google Cloud Console で以下を実行:
- [課金] → [アカウントをリンク] → 課金アカウントを選択
- または新規作成 (クレジットカード必要)

## 2. 必要なAPIを有効化
```bash
cd "C:\Users\naoot\Desktop\ｐ\sizukatest\rakuten-order-sync"
gcloud services enable cloudbuild.googleapis.com run.googleapis.com
```

## 3. Cloud Buildを使用したデプロイ
```bash
gcloud builds submit --config cloudbuild.yaml .
```

## 4. 手動デプロイ（Cloud Build未使用の場合）
```bash
# イメージをビルドしてプッシュ
gcloud builds submit --tag gcr.io/sizuka-inventory-system/sizuka-inventory .

# Cloud Runにデプロイ
gcloud run deploy sizuka-inventory-system \
  --image gcr.io/sizuka-inventory-system/sizuka-inventory \
  --platform managed \
  --region asia-northeast1 \
  --allow-unauthenticated \
  --set-env-vars SUPABASE_URL=https://jvkkvhdqtotbotjzngcv.supabase.co,SUPABASE_KEY=眉JhbG... \
  --memory 1Gi \
  --cpu 1 \
  --max-instances 10
```

## 5. デプロイ後の確認
```bash
# サービスURL取得
gcloud run services describe sizuka-inventory-system --region asia-northeast1 --format "value(status.url)"

# ヘルスチェック
curl -X GET [SERVICE_URL]/health
```

## Cloud Run版のメリット
1. **制限なし**: Vercelの12関数制限を解決
2. **統合**: 全APIが単一アプリケーション
3. **スケーラブル**: 自動スケーリング
4. **コスト効率**: 使用時のみ課金

## 主要エンドポイント
- `/` - メイン画面
- `/health` - ヘルスチェック
- `/api/inventory_list` - 在庫一覧
- `/api/sales_dashboard` - 売上ダッシュボード
- `/api/platform_sync` - プラットフォーム同期
- `/api/extract_choice_codes` - 選択肢コード抽出
- `/docs` - API ドキュメント