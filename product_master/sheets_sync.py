#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Google Sheetsとの自動同期モジュール（軽量版）
pandasを使用せず、標準ライブラリのみで実装
"""

import os
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from supabase import create_client
from dotenv import load_dotenv

# 環境変数の読み込み
load_dotenv()

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Supabase接続
supabase = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_KEY')
)

class GoogleSheetsSync:
    """Google Sheetsとの同期を管理するクラス（軽量版）"""
    
    def __init__(self, credentials_file: Optional[str] = None):
        """
        初期化
        
        Args:
            credentials_file: Google認証情報ファイルのパス
        """
        self.credentials_file = credentials_file or os.getenv('GOOGLE_CREDENTIALS_FILE')
        self.spreadsheet_id = os.getenv('PRODUCT_MASTER_SPREADSHEET_ID')
        self.service = None
        
        # Google認証情報の確認
        self.google_creds_json = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
        
        if not self.spreadsheet_id:
            raise ValueError("PRODUCT_MASTER_SPREADSHEET_ID環境変数が設定されていません")
    
    def authenticate(self):
        """Google Sheets APIの認証"""
        try:
            if self.credentials_file and os.path.exists(self.credentials_file):
                # サービスアカウント認証（ファイルから）
                logger.info(f"認証ファイルを使用: {self.credentials_file}")
                credentials = service_account.Credentials.from_service_account_file(
                    self.credentials_file,
                    scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
                )
            elif self.google_creds_json:
                # 環境変数から認証情報を取得
                logger.info("環境変数から認証情報を取得")
                service_account_info = json.loads(self.google_creds_json)
                credentials = service_account.Credentials.from_service_account_info(
                    service_account_info,
                    scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
                )
            else:
                raise ValueError("Google認証情報が見つかりません")
            
            self.service = build('sheets', 'v4', credentials=credentials)
            logger.info("Google Sheets API認証成功")
            
        except Exception as e:
            logger.error(f"Google Sheets API認証エラー: {str(e)}")
            raise
    
    def read_sheet(self, sheet_name: str, range_name: str = 'A:Z') -> List[List[str]]:
        """
        スプレッドシートからデータを読み取る
        
        Args:
            sheet_name: シート名
            range_name: 読み取り範囲（デフォルトは全列）
            
        Returns:
            セルデータの2次元リスト
        """
        if not self.service:
            self.authenticate()
        
        try:
            sheet = self.service.spreadsheets()
            result = sheet.values().get(
                spreadsheetId=self.spreadsheet_id,
                range=f'{sheet_name}!{range_name}'
            ).execute()
            
            values = result.get('values', [])
            logger.info(f"シート '{sheet_name}' から {len(values)} 行を読み取りました")
            return values
            
        except HttpError as error:
            logger.error(f"Google Sheets APIエラー: {error}")
            raise
    
    def sync_product_master(self):
        """商品番号マッピング基本表を同期"""
        logger.info("商品マスターの同期を開始します...")
        
        # スプレッドシートからデータを読み取る
        data = self.read_sheet('商品番号マッピング基本表')
        
        if not data or len(data) < 2:
            logger.warning("データが見つかりません")
            return 0, 0
        
        # ヘッダーとデータを分離
        headers = data[0]
        rows = data[1:]
        
        # ヘッダーのインデックスマップを作成
        header_map = {header: idx for idx, header in enumerate(headers)}
        
        success_count = 0
        error_count = 0
        
        for row_num, row in enumerate(rows, start=2):
            try:
                # 行データを辞書に変換
                row_data = {}
                for header, idx in header_map.items():
                    if idx < len(row):
                        row_data[header] = row[idx]
                    else:
                        row_data[header] = ''
                
                common_code = self._clean_value(row_data.get('共通コード'))
                if not common_code:
                    continue
                
                # 商品タイプの判定
                product_type = self._determine_product_type(
                    common_code, 
                    row_data.get('商品タイプ', '')
                )
                
                # 楽天SKUの処理
                rakuten_sku = self._clean_value(row_data.get('楽天SKU', ''))
                if rakuten_sku and '/' in rakuten_sku:
                    rakuten_sku = rakuten_sku.split('/')[0]
                
                # データの準備
                product_data = {
                    'common_code': common_code,
                    'jan_code': self._clean_value(row_data.get('JAN/EANコード')),
                    'product_name': self._clean_value(row_data.get('基本商品名')),
                    'product_type': product_type,
                    'rakuten_sku': rakuten_sku,
                    'colorme_id': self._clean_value(row_data.get('カラーミーID')),
                    'smaregi_id': self._clean_value(row_data.get('スマレジID')),
                    'yahoo_id': self._clean_value(row_data.get('Yahoo商品ID')),
                    'amazon_asin': self._clean_value(row_data.get('Amazon ASIN')),
                    'mercari_id': self._clean_value(row_data.get('メルカリ商品ID')),
                    'remarks': self._clean_value(row_data.get('備考')),
                    'is_limited': '限定' in str(row_data.get('備考', '')),
                    'is_active': True,
                    'updated_at': datetime.now(timezone.utc).isoformat()
                }
                
                # 既存レコードの確認
                existing = supabase.table('product_master').select('id').eq(
                    'common_code', common_code
                ).execute()
                
                if existing.data:
                    # 更新
                    result = supabase.table('product_master').update(
                        product_data
                    ).eq('common_code', common_code).execute()
                else:
                    # 新規作成
                    product_data['created_at'] = datetime.now(timezone.utc).isoformat()
                    result = supabase.table('product_master').insert(
                        product_data
                    ).execute()
                
                success_count += 1
                logger.debug(f"行 {row_num}: {common_code} を処理しました")
                
            except Exception as e:
                error_count += 1
                logger.error(f"行 {row_num} でエラー: {str(e)}")
        
        logger.info(f"商品マスター同期完了: 成功 {success_count}件, エラー {error_count}件")
        return success_count, error_count
    
    def sync_choice_codes(self):
        """選択肢コード対応表を同期"""
        logger.info("選択肢コードの同期を開始します...")
        
        # スプレッドシートからデータを読み取る
        data = self.read_sheet('選択肢コード対応表')
        
        if not data or len(data) < 2:
            logger.warning("データが見つかりません")
            return 0, 0
        
        headers = data[0]
        rows = data[1:]
        header_map = {header: idx for idx, header in enumerate(headers)}
        
        success_count = 0
        error_count = 0
        
        for row_num, row in enumerate(rows, start=2):
            try:
                # 行データを辞書に変換
                row_data = {}
                for header, idx in header_map.items():
                    if idx < len(row):
                        row_data[header] = row[idx]
                    else:
                        row_data[header] = ''
                
                choice_code = self._clean_value(row_data.get('選択肢コード'))
                common_code = self._clean_value(row_data.get('新共通コード'))
                
                if not choice_code or not common_code:
                    continue
                
                choice_data = {
                    'choice_code': choice_code,
                    'common_code': common_code,
                    'jan_code': self._clean_value(row_data.get('JAN')),
                    'rakuten_sku': self._clean_value(row_data.get('楽天SKU管理番号')),
                    'product_name': self._clean_value(row_data.get('商品名')),
                    'updated_at': datetime.now(timezone.utc).isoformat()
                }
                
                # 既存レコードの確認
                existing = supabase.table('choice_code_mapping').select('id').eq(
                    'choice_code', choice_code
                ).execute()
                
                if existing.data:
                    result = supabase.table('choice_code_mapping').update(
                        choice_data
                    ).eq('choice_code', choice_code).execute()
                else:
                    choice_data['created_at'] = datetime.now(timezone.utc).isoformat()
                    result = supabase.table('choice_code_mapping').insert(
                        choice_data
                    ).execute()
                
                success_count += 1
                logger.debug(f"行 {row_num}: {choice_code} を処理しました")
                
            except Exception as e:
                error_count += 1
                logger.error(f"行 {row_num} でエラー: {str(e)}")
        
        logger.info(f"選択肢コード同期完了: 成功 {success_count}件, エラー {error_count}件")
        return success_count, error_count
    
    def sync_package_components(self):
        """まとめ商品内訳を同期"""
        logger.info("まとめ商品内訳の同期を開始します...")
        
        # スプレッドシートからデータを読み取る
        data = self.read_sheet('まとめ商品内訳テーブル')
        
        if not data or len(data) < 2:
            logger.warning("データが見つかりません")
            return 0, 0
        
        # 最初の有効なヘッダーを見つける
        headers = None
        header_row_index = 0
        
        for i, row in enumerate(data):
            # 空行をスキップ
            if not row or all(cell == '' for cell in row):
                continue
            # ヘッダー行の特徴をチェック（「内訳ID」を含む）
            if any('内訳ID' in str(cell) for cell in row):
                headers = row
                header_row_index = i
                logger.info(f"ヘッダー行を {i+1} 行目で検出しました")
                break
        
        if not headers:
            logger.error("有効なヘッダー行が見つかりません")
            return 0, 0
        
        rows = data[header_row_index + 1:]
        header_map = {header: idx for idx, header in enumerate(headers)}
        
        # 既存データを削除（完全入れ替え）
        supabase.table('package_components').delete().neq('id', 0).execute()
        
        success_count = 0
        error_count = 0
        
        for row_num, row in enumerate(rows, start=2):
            try:
                # 行データを辞書に変換
                row_data = {}
                for header, idx in header_map.items():
                    if idx < len(row):
                        row_data[header] = row[idx]
                    else:
                        row_data[header] = ''
                
                package_code = self._clean_value(row_data.get('まとめ商品共通コード'))
                component_code = self._clean_value(row_data.get('構成品共通コード'))
                
                if not package_code or not component_code:
                    continue
                
                # 内訳IDの処理
                detail_id = None
                if row_data.get('内訳ID'):
                    try:
                        detail_id = int(row_data.get('内訳ID'))
                    except ValueError:
                        pass
                
                # 数量の処理
                quantity = 1
                if row_data.get('数量'):
                    try:
                        quantity = int(row_data.get('数量'))
                    except ValueError:
                        quantity = 1
                
                component_data = {
                    'detail_id': detail_id,
                    'package_code': package_code,
                    'package_name': self._clean_value(row_data.get('まとめ商品名')),
                    'component_code': component_code,
                    'quantity': quantity,
                    'remarks': self._clean_value(row_data.get('備考')),
                    'created_at': datetime.now(timezone.utc).isoformat(),
                    'updated_at': datetime.now(timezone.utc).isoformat()
                }
                
                result = supabase.table('package_components').insert(
                    component_data
                ).execute()
                
                success_count += 1
                logger.debug(f"行 {row_num}: {package_code} -> {component_code} を処理しました")
                
            except Exception as e:
                error_count += 1
                logger.error(f"行 {row_num} でエラー: {str(e)}")
        
        logger.info(f"まとめ商品内訳同期完了: 成功 {success_count}件, エラー {error_count}件")
        return success_count, error_count
    
    def sync_all(self):
        """すべてのシートを同期"""
        results = {
            'product_master': {'success': 0, 'error': 0},
            'choice_codes': {'success': 0, 'error': 0},
            'package_components': {'success': 0, 'error': 0}
        }
        
        try:
            # 商品マスター
            success, error = self.sync_product_master()
            results['product_master'] = {'success': success, 'error': error}
        except Exception as e:
            logger.error(f"商品マスター同期エラー: {str(e)}")
            results['product_master']['error'] = -1
            results['product_master']['error_message'] = str(e)
        
        try:
            # 選択肢コード
            success, error = self.sync_choice_codes()
            results['choice_codes'] = {'success': success, 'error': error}
        except Exception as e:
            logger.error(f"選択肢コード同期エラー: {str(e)}")
            results['choice_codes']['error'] = -1
            results['choice_codes']['error_message'] = str(e)
        
        try:
            # まとめ商品内訳
            success, error = self.sync_package_components()
            results['package_components'] = {'success': success, 'error': error}
        except Exception as e:
            logger.error(f"まとめ商品内訳同期エラー: {str(e)}")
            results['package_components']['error'] = -1
            results['package_components']['error_message'] = str(e)
        
        return results
    
    def _clean_value(self, value: Any) -> Optional[str]:
        """データのクリーニング"""
        if value is None or value == '':
            return None
        return str(value).strip()
    
    def _determine_product_type(self, common_code: str, type_str: Optional[str] = None) -> str:
        """商品タイプを判定"""
        if common_code.startswith('CM'):
            return '単品'
        elif common_code.startswith('BC'):
            if 'チョイス' in str(type_str) or '選択' in str(type_str):
                return 'セット(選択)'
            else:
                return 'セット(固定)'
        elif common_code.startswith('PC'):
            if '複合' in str(type_str):
                return 'まとめ(複合)'
            else:
                return 'まとめ(固定)'
        return '単品'

# メイン実行
if __name__ == "__main__":
    # 環境変数の例を表示
    print("必要な環境変数:")
    print("GOOGLE_CREDENTIALS_FILE: Google認証情報ファイルのパス")
    print("PRODUCT_MASTER_SPREADSHEET_ID: スプレッドシートのID")
    print("または")
    print("GOOGLE_SERVICE_ACCOUNT_JSON: サービスアカウントのJSON文字列")
    
    # 同期実行の例
    try:
        sync = GoogleSheetsSync()
        results = sync.sync_all()
        print(f"同期結果: {results}")
    except Exception as e:
        print(f"エラー: {str(e)}")
