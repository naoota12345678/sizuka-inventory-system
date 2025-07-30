@echo off
echo Google Sheets同期修正デプロイを開始します...
echo.

REM 現在のディレクトリを確認
cd /d "C:\Users\naoot\Desktop\ｐ\sizukatest\rakuten-order-sync"

REM Google認証ファイルの存在確認
if not exist "google-credentials.json" (
    echo ❌ エラー: google-credentials.json ファイルが見つかりません
    pause
    exit /b 1
)

echo ✅ Google認証ファイルを確認しました

REM .envファイルに環境変数を追加（既に追加済み）
echo ✅ 環境変数を設定しました

REM Google Cloud CLIの認証確認
echo.
echo Google Cloud CLIの認証を確認しています...
gcloud auth list
if errorlevel 1 (
    echo ❌ Google Cloud CLIが認証されていません
    echo 以下のコマンドを実行してください:
    echo gcloud auth login
    pause
    exit /b 1
)

REM プロジェクトの設定
echo.
echo プロジェクトを設定しています...
gcloud config set project sizuka-syouhin

REM Cloud Buildを使用してデプロイ
echo.
echo Cloud Buildを使用してデプロイを開始します...
gcloud builds submit --config cloudbuild.yaml

if errorlevel 1 (
    echo.
    echo ❌ デプロイに失敗しました
    pause
    exit /b 1
)

echo.
echo ✅ デプロイが完了しました！

REM デプロイの確認
echo.
echo デプロイされたサービスを確認しています...
gcloud run services describe rakuten-order-sync --region asia-northeast1 --format "value(status.url)"

REM テストの実行
echo.
echo Google Sheets同期機能をテストしますか？ (Y/N)
set /p TEST_CHOICE=

if /i "%TEST_CHOICE%"=="Y" (
    echo.
    echo テストを実行しています...
    python test_sheets_sync_test.py
)

echo.
echo デプロイプロセスが完了しました。
pause