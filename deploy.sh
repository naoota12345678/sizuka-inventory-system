#!/bin/bash
# deploy.sh - Cloud RunとCloud Schedulerを一括デプロイ

set -e

# 設定
PROJECT_ID="sizuka-syouhin"
REGION="asia-northeast1"
SERVICE_NAME="rakuten-order-sync"

echo "🚀 デプロイを開始します..."

# 1. プロジェクトの設定
echo "📋 プロジェクトを設定中..."
gcloud config set project ${PROJECT_ID}

# 2. 必要なAPIを有効化
echo "🔧 必要なAPIを有効化中..."
gcloud services enable \
  cloudbuild.googleapis.com \
  run.googleapis.com \
  cloudscheduler.googleapis.com \
  sheets.googleapis.com \
  secretmanager.googleapis.com

# 3. Secret Managerに環境変数を保存
echo "🔐 秘密情報を保存中..."
echo -n "SP338531_d1NJjF2R5OwZpWH6" | gcloud secrets create RAKUTEN_SERVICE_SECRET --data-file=- 2>/dev/null || echo "RAKUTEN_SERVICE_SECRET already exists"
echo -n "SL338531_kUvqO4kIHaMbr9ik" | gcloud secrets create RAKUTEN_LICENSE_KEY --data-file=- 2>/dev/null || echo "RAKUTEN_LICENSE_KEY already exists"
echo -n "https://equrcpeifogdrxoldkpe.supabase.co" | gcloud secrets create SUPABASE_URL --data-file=- 2>/dev/null || echo "SUPABASE_URL already exists"
echo -n "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ" | gcloud secrets create SUPABASE_KEY --data-file=- 2>/dev/null || echo "SUPABASE_KEY already exists"

# 4. Cloud Buildでデプロイ
echo "🏗️ アプリケーションをビルド・デプロイ中..."
gcloud builds submit --config=cloudbuild.yaml

# 5. 環境変数を設定
echo "⚙️ 環境変数を設定中..."
gcloud run services update ${SERVICE_NAME} \
  --region=${REGION} \
  --set-env-vars="PRODUCT_MASTER_SPREADSHEET_ID=1mLg1N0a1wubEIdKSouiW_jDaWUnuFLBxj8greczuS3E" \
  --set-secrets="RAKUTEN_SERVICE_SECRET=RAKUTEN_SERVICE_SECRET:latest" \
  --set-secrets="RAKUTEN_LICENSE_KEY=RAKUTEN_LICENSE_KEY:latest" \
  --set-secrets="SUPABASE_URL=SUPABASE_URL:latest" \
  --set-secrets="SUPABASE_KEY=SUPABASE_KEY:latest"

# 6. サービスURLを取得
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} --region=${REGION} --format="value(status.url)")
echo "✅ Cloud Runデプロイ完了: ${SERVICE_URL}"

# 7. サービスアカウントを取得
PROJECT_NUMBER=$(gcloud projects describe ${PROJECT_ID} --format="value(projectNumber)")
SERVICE_ACCOUNT="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

# 8. Cloud Runの呼び出し権限を付与
echo "🔑 サービスアカウントに権限を付与中..."
gcloud run services add-iam-policy-binding ${SERVICE_NAME} \
  --region=${REGION} \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/run.invoker"

# 9. Cloud Schedulerのジョブを作成
echo "⏰ Cloud Schedulerを設定中..."
gcloud scheduler jobs create http daily-rakuten-sync \
  --location=${REGION} \
  --schedule="0 2 * * *" \
  --uri="${SERVICE_URL}/daily-sync-all" \
  --http-method=POST \
  --headers="Content-Type=application/json" \
  --body='{"days":1}' \
  --oidc-service-account-email="${SERVICE_ACCOUNT}" \
  --time-zone="Asia/Tokyo" \
  --description="楽天注文データと商品マスターの日次同期（毎日午前2時）" \
  2>/dev/null || echo "Scheduler job already exists"

echo "
========================================
✨ デプロイが完了しました！
========================================
🌐 サービスURL: ${SERVICE_URL}
⏰ 自動実行: 毎日午前2時（JST）
📊 ヘルスチェック: ${SERVICE_URL}/health
📋 手動同期:
   - 商品マスター: curl -X POST ${SERVICE_URL}/sync-product-master
   - 日次処理: curl -X POST ${SERVICE_URL}/daily-sync-all -H 'Content-Type: application/json' -d '{\"days\":1}'

📌 注意事項:
1. Google Sheetsにサービスアカウント（${SERVICE_ACCOUNT}）の閲覧権限を付与してください
2. 初回は手動で動作確認することを推奨します
"
