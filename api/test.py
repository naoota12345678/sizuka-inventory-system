#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Vercel用の最小限のテストエンドポイント
"""

from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Hello from Vercel!"}

@app.get("/favicon.ico")
async def favicon():
    return JSONResponse(content={}, status_code=204)

# Vercel用のハンドラー
handler = app