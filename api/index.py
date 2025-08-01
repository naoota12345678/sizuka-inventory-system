from fastapi import FastAPI, Response
from fastapi.responses import JSONResponse
import os
from datetime import datetime
import pytz

app = FastAPI()

@app.get("/api")
def root():
    return {
        "status": "success",
        "message": "Sizuka Inventory System API は正常に動作しています",
        "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat(),
        "endpoints": [
            "GET /api - システム状態確認",
            "GET /api/health - ヘルスチェック"
        ]
    }

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
    }

@app.get("/api/python")
def hello_python():
    return {"message": "Hello from Python"}

@app.get("/api/favicon.ico")
def favicon():
    return Response(status_code=204)