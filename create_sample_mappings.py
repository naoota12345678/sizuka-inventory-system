#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
楽天選択肢コードのサンプルマッピングデータを作成
実際の楽天注文で使用されているコードでテスト
"""

from supabase import create_client
from datetime import datetime, timezone

SUPABASE_URL = "https://equrcpeifogdrxoldkpe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ"

print("=== Creating Sample Choice Code Mappings ===")

# 実際の楽天注文で使用されている選択肢コード
# （earlier analysisで発見された40種類のコード）
sample_mappings = [
    # ユーザーが提供した例から
    {"choice_code": "R05", "common_code": "S01", "product_name": "エゾ鹿レバー30g"},
    {"choice_code": "R13", "common_code": "S02", "product_name": "鶏砂肝ジャーキー30g"},
    {"choice_code": "R14", "common_code": "S03", "product_name": "豚ハツスライス30g"},
    {"choice_code": "R08", "common_code": "S04", "product_name": "ひとくちサーモン30g"},
    
    # その他のよく使用されるコード
    {"choice_code": "R01", "common_code": "S05", "product_name": "エゾ鹿スライス30g"},
    {"choice_code": "R11", "common_code": "S06", "product_name": "鶏ささみスライス30g"},
    {"choice_code": "R12", "common_code": "S07", "product_name": "鶏むねスライス30g"},
    {"choice_code": "N03", "common_code": "S08", "product_name": "サーモンチップ10g"},
    {"choice_code": "N06", "common_code": "S09", "product_name": "チキンチップ10g"},
    
    # 追加のサンプル
    {"choice_code": "R02", "common_code": "S10", "product_name": "エゾ鹿バーグ100g"},
    {"choice_code": "R03", "common_code": "S11", "product_name": "エゾ鹿プチ切りバー100g"},
    {"choice_code": "R04", "common_code": "S12", "product_name": "サーモン馬肉ス100g"},
    {"choice_code": "R06", "common_code": "S13", "product_name": "チキンチップ10g"},
    {"choice_code": "R07", "common_code": "S14", "product_name": "サーモンチップ10g"},
    {"choice_code": "R09", "common_code": "S15", "product_name": "スライスサーモン30g"},
    {"choice_code": "R10", "common_code": "S16", "product_name": "フレークサーモン30g"},
]

try:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    print(f"Creating {len(sample_mappings)} sample mappings...")
    
    success_count = 0
    error_count = 0
    
    for mapping in sample_mappings:
        try:
            # データの準備
            mapping_data = {
                "choice_code": mapping["choice_code"],
                "common_code": mapping["common_code"],
                "product_name": mapping["product_name"],
                "jan_code": None,
                "rakuten_sku": None,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            
            # 重複チェック
            existing = supabase.table("choice_code_mapping").select("id").eq("choice_code", mapping["choice_code"]).execute()
            
            if existing.data:
                # 更新
                result = supabase.table("choice_code_mapping").update(mapping_data).eq("choice_code", mapping["choice_code"]).execute()
                action = "UPDATED"
            else:
                # 新規挿入
                result = supabase.table("choice_code_mapping").insert(mapping_data).execute()
                action = "CREATED"
            
            if result.data:
                print(f"   ✓ {action}: {mapping['choice_code']} -> {mapping['common_code']} ({mapping['product_name']})")
                success_count += 1
            else:
                print(f"   ✗ FAILED: {mapping['choice_code']}")
                error_count += 1
                
        except Exception as e:
            print(f"   ✗ ERROR {mapping['choice_code']}: {str(e)}")
            error_count += 1
    
    print(f"\n=== RESULTS ===")
    print(f"Success: {success_count}")
    print(f"Errors: {error_count}")
    
    # 確認
    total = supabase.table("choice_code_mapping").select("*", count="exact").execute()
    print(f"Total mappings in database: {total.count}")
    
    print(f"\n=== READY FOR TESTING ===")
    print(f"選択肢コードマッピングが作成されました。")
    print(f"これで楽天注文データの在庫変動処理をテストできます。")
    
except Exception as e:
    print(f"ERROR: {str(e)}")
    import traceback
    traceback.print_exc()