#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Supabaseプロジェクトをアクティブに保つスクリプト
定期的に実行することでプロジェクトの一時停止を防ぐ
"""

import os
import sys
import logging
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client

# 環境変数読み込み
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def keep_alive():
    """Supabaseにアクセスしてプロジェクトをアクティブに保つ"""
    try:
        # Supabaseクライアント作成
        url = os.getenv('SUPABASE_URL')
        key = os.getenv('SUPABASE_KEY')
        
        if not url or not key:
            logger.error("Supabase認証情報が設定されていません")
            return False
        
        supabase = create_client(url, key)
        
        # platformテーブルから1件取得（軽量なクエリ）
        result = supabase.table('platform').select('id').limit(1).execute()
        
        # keep_aliveログをテーブルに記録
        log_data = {
            'action': 'keep_alive',
            'timestamp': datetime.now().isoformat(),
            'status': 'success'
        }
        
        # Keep aliveは成功（sync_logへの記録は不要）
        
        logger.info(f"Keep alive成功: {datetime.now()}")
        return True
        
    except Exception as e:
        logger.error(f"Keep aliveエラー: {str(e)}")
        return False

if __name__ == "__main__":
    if keep_alive():
        print("Supabaseプロジェクトのアクティブ化に成功しました")
    else:
        print("Supabaseプロジェクトのアクティブ化に失敗しました")