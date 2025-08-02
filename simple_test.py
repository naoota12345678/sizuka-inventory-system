#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
最小限のテスト用FastAPIアプリ
Cloud Runデプロイメント問題の切り分け用
"""

from fastapi import FastAPI
import os

app = FastAPI(title="Simple Test App")

@app.get("/")
async def root():
    return {
        "message": "Simple test app is running",
        "status": "ok",
        "port": os.environ.get("PORT", "8080")
    }

@app.get("/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)