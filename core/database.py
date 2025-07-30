#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
データベース接続管理モジュール
Supabaseクライアントの初期化と接続管理
"""

import logging
from typing import Optional
from supabase import create_client, Client
from .config import Config

logger = logging.getLogger(__name__)

class Database:
    """データベース接続管理クラス"""
    
    _instance: Optional[Client] = None
    
    @classmethod
    def get_client(cls) -> Optional[Client]:
        """Supabaseクライアントを取得"""
        if cls._instance is None:
            cls._instance = cls._initialize_client()
        return cls._instance
    
    @classmethod
    def _initialize_client(cls) -> Optional[Client]:
        """Supabaseクライアントを初期化"""
        try:
            if not Config.SUPABASE_URL or not Config.SUPABASE_KEY:
                logger.warning("Supabase認証情報が設定されていません")
                return None
            
            client = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
            logger.info("Supabaseクライアントを正常に初期化しました")
            return client
            
        except Exception as e:
            logger.error(f"Supabaseクライアントの初期化に失敗しました: {e}")
            return None
    
    @classmethod
    def test_connection(cls) -> bool:
        """データベース接続をテスト"""
        client = cls.get_client()
        if not client:
            return False
        
        try:
            # platformテーブルから1件取得してテスト
            result = client.table("platform").select("id").limit(1).execute()
            return True
        except Exception as e:
            logger.error(f"データベース接続テストに失敗しました: {e}")
            return False

# グローバルなSupabaseクライアントインスタンス
supabase = Database.get_client()