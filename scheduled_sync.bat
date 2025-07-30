@echo off
REM 毎日実行するバッチファイル

cd /d "C:\Users\naoot\Desktop\ｐ\sizukatest\rakuten-order-sync"

echo [%date% %time%] Keep Alive実行開始 >> sync_log.txt
python keep_alive.py >> sync_log.txt 2>&1

echo [%date% %time%] 注文同期実行開始 >> sync_log.txt
python -c "import requests; r=requests.get('http://localhost:8080/sync-orders?days=1'); print(r.json())" >> sync_log.txt 2>&1

echo [%date% %time%] 実行完了 >> sync_log.txt
echo. >> sync_log.txt