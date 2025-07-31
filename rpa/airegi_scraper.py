#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
エアレジ用ブラウザ自動化スクリプト
Seleniumを使用してエアレジからデータを取得・商品をアップロード
"""

import os
import time
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from supabase import create_client
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AiregiAutomation:
    """エアレジ自動化クラス"""
    
    def __init__(self):
        self.supabase = create_client(
            os.getenv('SUPABASE_URL'),
            os.getenv('SUPABASE_KEY')
        )
        self.driver = None
        self.wait = None
        
        # エアレジ認証情報
        self.airegi_email = os.getenv('AIREGI_EMAIL')
        self.airegi_password = os.getenv('AIREGI_PASSWORD')
        
    def setup_driver(self, headless=True):
        """Webドライバーを初期化"""
        chrome_options = Options()
        if headless:
            chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        
        # Cloud Run環境での設定
        if os.getenv('ENVIRONMENT') == 'production':
            chrome_options.binary_location = '/usr/bin/google-chrome'
            
        self.driver = webdriver.Chrome(options=chrome_options)
        self.wait = WebDriverWait(self.driver, 30)
        
    def login(self):
        """エアレジにログイン"""
        try:
            logger.info("エアレジにログイン中...")
            self.driver.get("https://airregi.jp/login")
            
            # メールアドレス入力
            email_field = self.wait.until(
                EC.presence_of_element_located((By.NAME, "email"))
            )
            email_field.send_keys(self.airegi_email)
            
            # パスワード入力
            password_field = self.driver.find_element(By.NAME, "password")
            password_field.send_keys(self.airegi_password)
            
            # ログインボタンクリック
            login_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            login_button.click()
            
            # ログイン完了まで待機
            self.wait.until(
                EC.presence_of_element_located((By.CLASS_NAME, "dashboard"))
            )
            logger.info("ログイン成功")
            return True
            
        except TimeoutException:
            logger.error("ログインタイムアウト")
            return False
        except Exception as e:
            logger.error(f"ログインエラー: {str(e)}")
            return False
    
    def scrape_sales_data(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """売上データを取得"""
        sales_data = []
        
        try:
            logger.info(f"売上データ取得: {start_date} - {end_date}")
            
            # 売上レポート画面に移動
            self.driver.get("https://airregi.jp/pos/reports/sales")
            
            # 日付範囲を設定
            start_date_field = self.wait.until(
                EC.element_to_be_clickable((By.NAME, "start_date"))
            )
            start_date_field.clear()
            start_date_field.send_keys(start_date.strftime("%Y-%m-%d"))
            
            end_date_field = self.driver.find_element(By.NAME, "end_date")
            end_date_field.clear()
            end_date_field.send_keys(end_date.strftime("%Y-%m-%d"))
            
            # 検索実行
            search_button = self.driver.find_element(By.CSS_SELECTOR, "button.search-btn")
            search_button.click()
            
            # データ読み込み待機
            time.sleep(3)
            
            # 売上データをスクレイピング
            sales_rows = self.driver.find_elements(By.CSS_SELECTOR, "table.sales-table tbody tr")
            
            for row in sales_rows:
                cells = row.find_elements(By.TAG_NAME, "td")
                if len(cells) >= 6:
                    sale_data = {
                        'transaction_id': cells[0].text.strip(),
                        'sale_date': self._parse_date(cells[1].text.strip()),
                        'product_name': cells[2].text.strip(),
                        'quantity': int(cells[3].text.strip() or 0),
                        'unit_price': float(cells[4].text.strip().replace(',', '') or 0),
                        'total_amount': float(cells[5].text.strip().replace(',', '') or 0),
                        'platform': 'airegi'
                    }
                    sales_data.append(sale_data)
            
            logger.info(f"売上データ取得完了: {len(sales_data)}件")
            return sales_data
            
        except Exception as e:
            logger.error(f"売上データ取得エラー: {str(e)}")
            return []
    
    def upload_products(self, products: List[Dict]) -> Dict:
        """商品をエアレジにアップロード"""
        results = {'success': 0, 'failed': 0, 'errors': []}
        
        try:
            logger.info(f"商品アップロード開始: {len(products)}件")
            
            # 商品管理画面に移動
            self.driver.get("https://airregi.jp/pos/items")
            
            for product in products:
                try:
                    # 新規商品登録ボタンクリック
                    add_button = self.wait.until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, "button.add-item-btn"))
                    )
                    add_button.click()
                    
                    # 商品情報入力
                    self._fill_product_form(product)
                    
                    # 保存
                    save_button = self.driver.find_element(By.CSS_SELECTOR, "button.save-btn")
                    save_button.click()
                    
                    # 保存完了待機
                    self.wait.until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".success-message"))
                    )
                    
                    results['success'] += 1
                    logger.info(f"商品登録成功: {product.get('name', 'Unknown')}")
                    
                except Exception as e:
                    results['failed'] += 1
                    error_msg = f"商品登録失敗: {product.get('name', 'Unknown')} - {str(e)}"
                    results['errors'].append(error_msg)
                    logger.error(error_msg)
                    
                    # エラー時は一覧画面に戻る
                    self.driver.get("https://airregi.jp/pos/items")
                
                # 次の商品のため少し待機
                time.sleep(1)
            
            logger.info(f"商品アップロード完了: 成功{results['success']}件, 失敗{results['failed']}件")
            return results
            
        except Exception as e:
            logger.error(f"商品アップロードエラー: {str(e)}")
            results['errors'].append(str(e))
            return results
    
    def _fill_product_form(self, product: Dict):
        """商品フォームに情報を入力"""
        # 商品名
        name_field = self.driver.find_element(By.NAME, "item_name")
        name_field.clear()
        name_field.send_keys(product.get('name', ''))
        
        # 価格
        price_field = self.driver.find_element(By.NAME, "price")
        price_field.clear()
        price_field.send_keys(str(product.get('price', 0)))
        
        # SKU/商品コード
        if product.get('sku'):
            sku_field = self.driver.find_element(By.NAME, "item_code")
            sku_field.clear()
            sku_field.send_keys(product.get('sku'))
        
        # カテゴリ（オプション）
        if product.get('category'):
            category_select = self.driver.find_element(By.NAME, "category")
            # カテゴリ選択ロジック（エアレジのUIに応じて調整）
            pass
    
    def _parse_date(self, date_str: str) -> str:
        """日付文字列をISO形式に変換"""
        try:
            # エアレジの日付形式に応じて調整
            dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M")
            return dt.isoformat()
        except:
            return datetime.now().isoformat()
    
    def save_to_database(self, sales_data: List[Dict], platform_id: int):
        """売上データをデータベースに保存"""
        try:
            # プラットフォームIDを取得（エアレジ）
            platform_result = self.supabase.table('platform').select('id').eq('platform_code', 'airegi').execute()
            if not platform_result.data:
                logger.error("エアレジプラットフォームが見つかりません")
                return
            
            platform_id = platform_result.data[0]['id']
            
            for sale in sales_data:
                # 商品の共通コードを取得（商品名から逆引き）
                common_code = self._get_common_code_by_name(sale['product_name'])
                if not common_code:
                    logger.warning(f"商品の共通コードが見つかりません: {sale['product_name']}")
                    continue
                
                # 売上データを保存
                transaction_data = {
                    'transaction_id': sale['transaction_id'],
                    'platform_id': platform_id,
                    'common_code': common_code,
                    'sale_date': sale['sale_date'],
                    'quantity': sale['quantity'],
                    'unit_price': sale['unit_price'],
                    'total_amount': sale['total_amount'],
                    'net_amount': sale['total_amount'],  # エアレジは手数料なし
                    'customer_type': 'retail',
                    'sync_source': 'rpa',
                    'raw_data': sale
                }
                
                # 重複チェック後に保存
                existing = self.supabase.table('sales_transactions').select('id').eq(
                    'platform_id', platform_id
                ).eq('transaction_id', sale['transaction_id']).execute()
                
                if not existing.data:
                    self.supabase.table('sales_transactions').insert(transaction_data).execute()
                    logger.debug(f"売上データ保存: {sale['transaction_id']}")
            
            logger.info(f"データベース保存完了: {len(sales_data)}件")
            
        except Exception as e:
            logger.error(f"データベース保存エラー: {str(e)}")
    
    def _get_common_code_by_name(self, product_name: str) -> Optional[str]:
        """商品名から共通コードを取得"""
        try:
            result = self.supabase.table('product_master').select('common_code').ilike(
                'product_name', f'%{product_name}%'
            ).limit(1).execute()
            
            if result.data:
                return result.data[0]['common_code']
            return None
        except:
            return None
    
    def close(self):
        """ドライバーを閉じる"""
        if self.driver:
            self.driver.quit()

# 使用例
if __name__ == "__main__":
    automation = AiregiAutomation()
    try:
        automation.setup_driver(headless=False)  # 開発時はheadless=False
        
        if automation.login():
            # 過去1週間の売上データを取得
            end_date = datetime.now()
            start_date = end_date - timedelta(days=7)
            
            sales_data = automation.scrape_sales_data(start_date, end_date)
            if sales_data:
                automation.save_to_database(sales_data, platform_id=None)
        
    finally:
        automation.close()