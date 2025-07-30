@echo off
echo 直接デプロイを開始します...

echo Dockerイメージをビルド中...
docker build -t gcr.io/sizuka-syouhin/rakuten-order-sync:latest .

echo 認証設定中...
gcloud auth configure-docker

echo イメージをプッシュ中...
docker push gcr.io/sizuka-syouhin/rakuten-order-sync:latest

echo Cloud Runにデプロイ中...
gcloud run deploy rakuten-order-sync ^
  --image gcr.io/sizuka-syouhin/rakuten-order-sync:latest ^
  --platform managed ^
  --region asia-northeast1 ^
  --allow-unauthenticated ^
  --memory 1Gi ^
  --timeout 300 ^
  --set-env-vars="PRODUCT_MASTER_SPREADSHEET_ID=1mLg1N0a1wubEIdKSouiW_jDaWUnuFLBxj8greczuS3E" ^
  --set-secrets="RAKUTEN_SERVICE_SECRET=RAKUTEN_SERVICE_SECRET:latest" ^
  --set-secrets="RAKUTEN_LICENSE_KEY=RAKUTEN_LICENSE_KEY:latest" ^
  --set-secrets="SUPABASE_URL=SUPABASE_URL:latest" ^
  --set-secrets="SUPABASE_KEY=SUPABASE_KEY:latest"

echo デプロイ完了！
pause
