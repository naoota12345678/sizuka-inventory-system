#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
設定管理モジュール
環境変数の読み込みと設定値の管理
"""

import os
import logging
from dotenv import load_dotenv

# 環境変数の読み込み
load_dotenv()

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Config:
    """アプリケーション設定"""
    
    # Supabase設定（動的に環境変数を取得）
    @classmethod
    def get_supabase_url(cls):
        return os.getenv('SUPABASE_URL')
    
    @classmethod
    def get_supabase_key(cls):
        return os.getenv('SUPABASE_KEY')
    
    # 後方互換性のためのプロパティ
    @property
    def SUPABASE_URL(self):
        return os.getenv('SUPABASE_URL')
    
    @property
    def SUPABASE_KEY(self):
        return os.getenv('SUPABASE_KEY')
    
    # 楽天API設定
    RAKUTEN_SERVICE_SECRET = os.getenv('RAKUTEN_SERVICE_SECRET')
    RAKUTEN_LICENSE_KEY = os.getenv('RAKUTEN_LICENSE_KEY')
    
    # Google Sheets設定
    GOOGLE_CREDENTIALS_FILE = os.getenv('GOOGLE_CREDENTIALS_FILE')
    GOOGLE_APPLICATION_CREDENTIALS = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    GOOGLE_SERVICE_ACCOUNT_JSON = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
    PRODUCT_MASTER_SPREADSHEET_ID = os.getenv('PRODUCT_MASTER_SPREADSHEET_ID')
    
    # アプリケーション設定
    APP_NAME = "Rakuten Order Sync API"
    APP_VERSION = "1.0.0"
    
    @classmethod
    def validate_required_env(cls):
        """必須環境変数の検証"""
        required = {
            'SUPABASE_URL': cls.SUPABASE_URL,
            'SUPABASE_KEY': cls.SUPABASE_KEY,
            'RAKUTEN_SERVICE_SECRET': cls.RAKUTEN_SERVICE_SECRET,
            'RAKUTEN_LICENSE_KEY': cls.RAKUTEN_LICENSE_KEY
        }
        
        missing = [key for key, value in required.items() if not value]
        
        if missing:
            error_msg = f"必須の環境変数が設定されていません: {', '.join(missing)}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        return True
    
    @classmethod
    def is_sheets_sync_available(cls):
        """Google Sheets同期が利用可能かチェック"""
        # 認証ファイルのパスを探す
        cred_paths = [
            cls.GOOGLE_CREDENTIALS_FILE,
            cls.GOOGLE_APPLICATION_CREDENTIALS,
            '/app/credentials.json',
            'google-credentials.json'
        ]
        
        # ファイルが存在するかチェック
        for path in cred_paths:
            if path and os.path.exists(path):
                logger.info(f"Google認証ファイルが見つかりました: {path}")
                return True
        
        # JSON形式の認証情報があるかチェック
        if cls.GOOGLE_SERVICE_ACCOUNT_JSON:
            logger.info("Google認証情報（JSON）が環境変数に設定されています")
            return True
        
        logger.warning("Google Sheets同期に必要な認証情報が見つかりません")
        return False
    
    @classmethod
    def get_google_creds_path(cls):
        """利用可能なGoogle認証ファイルのパスを取得"""
        cred_paths = [
            cls.GOOGLE_CREDENTIALS_FILE,
            cls.GOOGLE_APPLICATION_CREDENTIALS,
            '/app/credentials.json',
            'google-credentials.json'
        ]
        
        for path in cred_paths:
            if path and os.path.exists(path):
                return path
        
        return None