@echo off
echo 🚀 楽天注文同期APIのデプロイを開始します...

:: プロジェクトディレクトリに移動
cd /d "C:\Users\naoot\Desktop\ｐ\sizukatest\rakuten-order-sync"

:: プロジェクトの設定
echo 📋 プロジェクトを設定中...
gcloud config set project sizuka-syouhin

:: デプロイ実行
echo 🏗️ アプリケーションをビルド・デプロイ中...
gcloud builds submit --config=cloudbuild.yaml

echo.
echo ✅ デプロイコマンドを実行しました
echo.
echo ビルドの状況を確認するには、以下のコマンドを実行してください:
echo gcloud builds list --limit=1
echo.
pause