@echo off
cd /d C:\Users\naoot\Desktop\p\sizukatest\rakuten-order-sync

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo Running test data import...
python test_integration.py

echo.
echo Import completed. Press any key to exit...
pause
