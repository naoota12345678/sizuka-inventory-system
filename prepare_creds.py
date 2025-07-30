#!/usr/bin/env python
# -*- coding: utf-8 -*-
import json

# google-credentials.jsonを読み込んで、1行のJSON文字列として保存
with open('google-credentials.json', 'r') as f:
    creds = json.load(f)

# 1行のJSON文字列に変換
creds_json = json.dumps(creds, separators=(',', ':'))

# ファイルに保存
with open('google-creds-oneline.json', 'w') as f:
    f.write(creds_json)

print("✅ google-creds-oneline.json を作成しました")