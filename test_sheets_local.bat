@echo off
echo ローカル環境でGoogle Sheets同期をテストします...
echo.

REM 現在のディレクトリを確認
cd /d "C:\Users\naoot\Desktop\ｐ\sizukatest\rakuten-order-sync"

REM 環境変数を設定
echo 環境変数を設定しています...
set GOOGLE_APPLICATION_CREDENTIALS=google-credentials.json
set GOOGLE_CREDENTIALS_FILE=google-credentials.json

REM ローカルサーバーを起動
echo.
echo ローカルサーバーを起動しています...
start cmd /k "python -m uvicorn main:app --reload --port 8080"

REM サーバーの起動を待つ
echo サーバーの起動を待っています...
timeout /t 5 /nobreak > nul

REM テストを実行
echo.
echo テストを実行しています...
python test_sheets_sync_test.py --local

echo.
echo テストが完了しました。
echo ローカルサーバーを停止するには、サーバーウィンドウでCtrl+Cを押してください。
pause