# deploy.bat - Windows用デプロイスクリプト

@echo off
echo 🚀 デプロイを開始します...

:: プロジェクトの設定
echo 📋 プロジェクトを設定中...
gcloud config set project sizuka-syouhin

:: 必要なAPIを有効化
echo 🔧 必要なAPIを有効化中...
gcloud services enable cloudbuild.googleapis.com run.googleapis.com cloudscheduler.googleapis.com sheets.googleapis.com secretmanager.googleapis.com

:: Secret Managerに環境変数を保存
echo 🔐 秘密情報を保存中...
echo|set /p="SP338531_d1NJjF2R5OwZpWH6" | gcloud secrets create RAKUTEN_SERVICE_SECRET --data-file=- 2>nul || echo RAKUTEN_SERVICE_SECRET already exists
echo|set /p="SL338531_kUvqO4kIHaMbr9ik" | gcloud secrets create RAKUTEN_LICENSE_KEY --data-file=- 2>nul || echo RAKUTEN_LICENSE_KEY already exists
echo|set /p="https://equrcpeifogdrxoldkpe.supabase.co" | gcloud secrets create SUPABASE_URL --data-file=- 2>nul || echo SUPABASE_URL already exists
echo|set /p="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ" | gcloud secrets create SUPABASE_KEY --data-file=- 2>nul || echo SUPABASE_KEY already exists

:: Cloud Buildでデプロイ
echo 🏗️ アプリケーションをビルド・デプロイ中...
gcloud builds submit --config=cloudbuild.yaml

:: 環境変数を設定
echo ⚙️ 環境変数を設定中...
gcloud run services update rakuten-order-sync ^
  --region=asia-northeast1 ^
  --set-env-vars="PRODUCT_MASTER_SPREADSHEET_ID=1mLg1N0a1wubEIdKSouiW_jDaWUnuFLBxj8greczuS3E" ^
  --set-secrets="RAKUTEN_SERVICE_SECRET=RAKUTEN_SERVICE_SECRET:latest" ^
  --set-secrets="RAKUTEN_LICENSE_KEY=RAKUTEN_LICENSE_KEY:latest" ^
  --set-secrets="SUPABASE_URL=SUPABASE_URL:latest" ^
  --set-secrets="SUPABASE_KEY=SUPABASE_KEY:latest"

:: サービスURLを取得
for /f "tokens=*" %%i in ('gcloud run services describe rakuten-order-sync --region=asia-northeast1 --format="value(status.url)"') do set SERVICE_URL=%%i
echo ✅ Cloud Runデプロイ完了: %SERVICE_URL%

:: サービスアカウントを取得
for /f "tokens=*" %%i in ('gcloud projects describe sizuka-syouhin --format="value(projectNumber)"') do set PROJECT_NUMBER=%%i
set SERVICE_ACCOUNT=%PROJECT_NUMBER%-compute@developer.gserviceaccount.com

:: Cloud Runの呼び出し権限を付与
echo 🔑 サービスアカウントに権限を付与中...
gcloud run services add-iam-policy-binding rakuten-order-sync ^
  --region=asia-northeast1 ^
  --member="serviceAccount:%SERVICE_ACCOUNT%" ^
  --role="roles/run.invoker"

:: Cloud Schedulerのジョブを作成
echo ⏰ Cloud Schedulerを設定中...
gcloud scheduler jobs create http daily-rakuten-sync ^
  --location=asia-northeast1 ^
  --schedule="0 2 * * *" ^
  --uri="%SERVICE_URL%/daily-sync-all" ^
  --http-method=POST ^
  --headers="Content-Type=application/json" ^
  --body="{\"days\":1}" ^
  --oidc-service-account-email="%SERVICE_ACCOUNT%" ^
  --time-zone="Asia/Tokyo" ^
  --description="楽天注文データと商品マスターの日次同期（毎日午前2時）" ^
  2>nul || echo Scheduler job already exists

echo.
echo ========================================
echo ✨ デプロイが完了しました！
echo ========================================
echo 🌐 サービスURL: %SERVICE_URL%
echo ⏰ 自動実行: 毎日午前2時（JST）
echo 📊 ヘルスチェック: %SERVICE_URL%/health
echo.
echo 📌 注意事項:
echo 1. Google Sheetsにサービスアカウント（%SERVICE_ACCOUNT%）の閲覧権限を付与してください
echo 2. 初回は手動で動作確認することを推奨します
echo.
pause
