#!/usr/bin/env python
# -*- coding: utf-8 -*-

from fastapi import FastAPI
import os
import logging

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPIアプリケーションの作成
app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Hello from Rakuten Order Sync"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    logger.info(f"Starting server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
