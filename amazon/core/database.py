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
    def reset_client(cls):
        """クライアントをリセット（環境変数変更時に使用）"""
        cls._instance = None
    
    @classmethod
    def _initialize_client(cls) -> Optional[Client]:
        """Supabaseクライアントを初期化"""
        try:
            # 動的に環境変数を取得
            supabase_url = Config.get_supabase_url()
            supabase_key = Config.get_supabase_key()
            
            if not supabase_url or not supabase_key:
                logger.warning("Supabase認証情報が設定されていません")
                return None
            
            client = create_client(supabase_url, supabase_key)
            logger.info(f"Supabaseクライアントを正常に初期化しました: {supabase_url}")
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

# グローバルなSupabaseクライアントインスタンス（動的に取得）
def get_supabase():
    return Database.get_client()

supabase = get_supabase()