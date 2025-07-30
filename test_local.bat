@echo off
echo 📋 ローカルテストを開始します...

cd /d "C:\Users\naoot\Desktop\ｐ\sizukatest\rakuten-order-sync"

:: Python仮想環境をアクティベート
call venv\Scripts\activate

:: アプリケーションを起動
echo 🚀 アプリケーションを起動中...
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000