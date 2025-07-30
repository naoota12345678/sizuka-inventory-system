#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ユーティリティ関数
データ処理やヘルパー関数
"""

import re
import json
from typing import List, Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

def extract_product_code_prefix(product_name: str) -> str:
    """商品名から先頭の商品コード部分を抽出する
    
    例: "S01 ひとくちサーモン 30g" -> "S01"
    """
    if not product_name:
        return ""
    
    # 空白またはハイフンの前までの文字列を取得
    parts = product_name.split()
    if not parts:
        return ""
    
    # 先頭部分が商品コードのパターンに一致するか確認（S01など）
    prefix = parts[0]
    if re.match(r'^[A-Z]\d{2}$', prefix):  # 「アルファベット1文字+数字2桁」のパターン
        return prefix
    
    return ""

def extract_sku_data(sku_models: List[Dict]) -> Tuple[str, str, str, Dict]:
    """SKUモデルから必要なデータを抽出する
    
    Args:
        sku_models: SkuModelListのデータ
        
    Returns:
        Tuple containing:
            merchant_item_id: 商品管理番号
            item_number: 商品番号（JANコードなど）
            variant_id: バリエーションID
            item_choice: 選択肢情報（辞書形式）
    """
    # デフォルト値を設定
    merchant_item_id = ""
    item_number = ""
    variant_id = ""
    item_choice = {}
    
    if not sku_models:
        return merchant_item_id, item_number, variant_id, item_choice
    
    # 最初のSKUモデルを使用する
    sku = sku_models[0]
    
    # 商品管理番号（merchantDefinedSkuId）を抽出
    if sku.get("merchantDefinedSkuId") is not None:
        merchant_item_id = str(sku.get("merchantDefinedSkuId"))
    
    # バリエーションID（variantId）を抽出
    if sku.get("variantId") is not None:
        variant_id = str(sku.get("variantId"))
    
    # 選択肢情報（skuInfo）を抽出
    sku_info = sku.get("skuInfo")
    if isinstance(sku_info, dict):
        item_choice = sku_info
        
        # JANコードなどを探す（skuInfoにデータがある場合）
        if "janCode" in sku_info:
            item_number = str(sku_info.get("janCode", ""))
    
    return merchant_item_id, item_number, variant_id, item_choice

def extract_selected_choices(selected_choice_text: str) -> List[Dict[str, str]]:
    """
    selectedChoiceテキストから選択された商品コードと商品名を抽出する
    
    Args:
        selected_choice_text: selectedChoiceフィールドのテキスト
        
    Returns:
        選択された商品コードと商品名のリスト
    """
    if not selected_choice_text:
        return []
    
    choices = []
    
    # 改行で分割
    lines = selected_choice_text.split('\n')
    
    # 選択肢の行を処理（◆から始まる行）
    for line in lines:
        if line.startswith('◆'):
            # コロンで分割して右側（選択内容）を取得
            parts = line.split(':', 1)
            if len(parts) > 1:
                choice_info = parts[1].strip()
                
                # 商品コード（RXXなど）を抽出
                code_match = re.search(r'(R\d+|S\d+)', choice_info)
                code = code_match.group(1) if code_match else ""
                
                # 商品名（コードの後のテキスト）
                name = choice_info
                if code:
                    name = re.sub(r'^' + re.escape(code) + r'\s+', '', choice_info)
                
                choices.append({
                    "code": code,
                    "name": name
                })
    
    return choices