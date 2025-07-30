#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Google Sheets同期モジュール（条件付きインポート）
必要な依存関係がインストールされている場合のみ動作
"""

import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# Google Sheets同期クラスのインポートを試みる
GoogleSheetsSync = None
SHEETS_SYNC_AVAILABLE = False

try:
    # 必要なパッケージがインストールされているか確認
    import google.auth
    import googleapiclient
    
    # 元のsheets_syncモジュールをインポート
    from product_master.sheets_sync import GoogleSheetsSync as _GoogleSheetsSync
    GoogleSheetsSync = _GoogleSheetsSync
    SHEETS_SYNC_AVAILABLE = True
    logger.info("Google Sheets同期モジュールが正常にロードされました")
    
except ImportError as e:
    logger.warning(f"Google Sheets同期は利用できません - 依存関係が不足しています: {e}")
except Exception as e:
    logger.warning(f"Google Sheets同期モジュールのロードに失敗しました: {e}")

def get_sheets_sync_instance(credentials_file: Optional[str] = None) -> Optional[Any]:
    """Google Sheets同期インスタンスを取得（利用可能な場合）"""
    if not SHEETS_SYNC_AVAILABLE or not GoogleSheetsSync:
        logger.warning("Google Sheets同期は利用できません")
        return None
    
    try:
        return GoogleSheetsSync(credentials_file)
    except Exception as e:
        logger.error(f"Google Sheets同期インスタンスの作成に失敗しました: {e}")
        return None

def sync_product_master() -> Dict[str, Any]:
    """商品マスターの同期を実行（利用可能な場合）"""
    if not SHEETS_SYNC_AVAILABLE:
        return {
            "status": "unavailable",
            "message": "Google Sheets同期は利用できません"
        }
    
    sync_instance = get_sheets_sync_instance()
    if not sync_instance:
        return {
            "status": "error",
            "message": "Google Sheets同期インスタンスの作成に失敗しました"
        }
    
    try:
        results = sync_instance.sync_all()
        return {
            "status": "success",
            "results": results
        }
    except Exception as e:
        logger.error(f"商品マスター同期エラー: {e}")
        return {
            "status": "error",
            "message": str(e)
        }