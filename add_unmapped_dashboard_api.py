#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
main_cloudrun.pyに未マッピング商品ダッシュボード機能を追加
1. 未マッピング商品表示API
2. 再マッピング実行API
3. ダッシュボードHTML
"""

import sys
import os

def add_unmapped_apis_to_main():
    """main_cloudrun.pyに未マッピング機能を追加"""
    
    # 追加するAPIコード
    api_code = '''
# ===== 未マッピング商品管理API =====

@app.get("/api/unmapped_products")
async def get_unmapped_products():
    """未マッピング商品の取得"""
    try:
        # マッピングテーブル取得
        pm_data = supabase.table('product_master').select('rakuten_sku, common_code, product_name').execute()
        sku_mapping = {}
        for item in pm_data.data:
            sku = item.get('rakuten_sku')
            if sku:
                sku_mapping[str(sku)] = item
        
        ccm_data = supabase.table('choice_code_mapping').select('choice_info, common_code, product_name').execute()
        choice_mapping = {}
        for item in ccm_data.data:
            choice_info = item.get('choice_info', {})
            if isinstance(choice_info, dict) and 'choice_code' in choice_info:
                choice_mapping[choice_info['choice_code']] = item
        
        # 楽天データから未マッピング商品を検出（サンプリング）
        unmapped_products = {}
        
        # 最新1000件をサンプリング
        result = supabase.table('order_items').select(
            'id, quantity, choice_code, rakuten_item_number, product_code, product_name, orders!inner(platform_id, order_date)'
        ).eq('orders.platform_id', 1).order('id', desc=True).limit(1000).execute()
        
        for item in result.data:
            quantity = int(item.get('quantity', 0))
            if quantity <= 0:
                continue
            
            choice_code = item.get('choice_code', '') or ''
            rakuten_item_number = item.get('rakuten_item_number', '') or ''
            
            # マッピング確認
            mapped = False
            if choice_code and choice_code in choice_mapping:
                mapped = True
            elif rakuten_item_number and str(rakuten_item_number) in sku_mapping:
                mapped = True
            
            if not mapped:
                # キーの決定
                key = choice_code if choice_code else f"sku_{rakuten_item_number}"
                
                if key not in unmapped_products:
                    unmapped_products[key] = {
                        'choice_code': choice_code,
                        'rakuten_item_number': rakuten_item_number,
                        'product_code': item.get('product_code', ''),
                        'product_name': item.get('product_name', ''),
                        'total_quantity': 0,
                        'order_count': 0,
                        'latest_order_date': item.get('orders', {}).get('order_date', '')
                    }
                
                unmapped_products[key]['total_quantity'] += quantity
                unmapped_products[key]['order_count'] += 1
        
        # 結果を数量順でソート
        sorted_unmapped = sorted(
            unmapped_products.values(),
            key=lambda x: x['total_quantity'],
            reverse=True
        )
        
        return {
            "status": "success",
            "unmapped_count": len(sorted_unmapped),
            "sample_size": len(result.data) if result.data else 0,
            "unmapped_products": sorted_unmapped[:10]  # 上位10件のみ
        }
        
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/remapping")
async def execute_remapping():
    """再マッピング実行（Google Sheets同期 + マッピング更新）"""
    try:
        from google_sheets_sync import daily_sync
        import asyncio
        
        # Step 1: Google Sheets同期
        sync_success = daily_sync()
        
        if not sync_success:
            return {
                "status": "error", 
                "message": "Google Sheets同期に失敗しました"
            }
        
        # Step 2: マッピング成功率確認
        # マッピングテーブル再取得
        pm_data = supabase.table('product_master').select('rakuten_sku, common_code').execute()
        sku_mapping = {str(item['rakuten_sku']): item['common_code'] 
                      for item in pm_data.data if item.get('rakuten_sku')}
        
        ccm_data = supabase.table('choice_code_mapping').select('choice_info, common_code').execute()
        choice_mapping = {}
        for item in ccm_data.data:
            choice_info = item.get('choice_info', {})
            if isinstance(choice_info, dict) and 'choice_code' in choice_info:
                choice_mapping[choice_info['choice_code']] = item['common_code']
        
        # サンプリングでマッピング率確認
        result = supabase.table('order_items').select(
            'quantity, choice_code, rakuten_item_number, orders!inner(platform_id)'
        ).eq('orders.platform_id', 1).limit(1000).execute()
        
        total_items = 0
        mapped_items = 0
        
        for item in result.data:
            quantity = int(item.get('quantity', 0))
            if quantity <= 0:
                continue
            
            total_items += 1
            choice_code = item.get('choice_code', '') or ''
            rakuten_item_number = item.get('rakuten_item_number', '') or ''
            
            if choice_code and choice_code in choice_mapping:
                mapped_items += 1
            elif rakuten_item_number and str(rakuten_item_number) in sku_mapping:
                mapped_items += 1
        
        success_rate = (mapped_items / total_items * 100) if total_items > 0 else 0
        
        return {
            "status": "success",
            "sync_success": True,
            "mapping_stats": {
                "total_items": total_items,
                "mapped_items": mapped_items,
                "success_rate": round(success_rate, 2)
            },
            "message": f"再マッピング完了。成功率: {success_rate:.1f}%"
        }
        
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/unmapped-dashboard")
async def unmapped_dashboard():
    """未マッピング商品ダッシュボード"""
    html_content = """
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>未マッピング商品管理</title>
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                margin: 0;
                padding: 20px;
                background-color: #f5f5f5;
                color: #333;
            }
            
            .container {
                max-width: 1200px;
                margin: 0 auto;
                background: white;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                padding: 30px;
            }
            
            .header {
                text-align: center;
                margin-bottom: 30px;
                padding-bottom: 20px;
                border-bottom: 2px solid #e0e0e0;
            }
            
            .header h1 {
                color: #2c3e50;
                margin: 0;
                font-size: 2.5em;
            }
            
            .status-bar {
                display: flex;
                justify-content: space-between;
                align-items: center;
                background: #ecf0f1;
                padding: 15px 20px;
                border-radius: 8px;
                margin-bottom: 20px;
            }
            
            .status-info {
                font-size: 1.1em;
                font-weight: bold;
            }
            
            .remapping-btn {
                background: #3498db;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 6px;
                cursor: pointer;
                font-size: 1em;
                font-weight: bold;
                transition: background-color 0.3s;
            }
            
            .remapping-btn:hover {
                background: #2980b9;
            }
            
            .remapping-btn:disabled {
                background: #bdc3c7;
                cursor: not-allowed;
            }
            
            .alert {
                padding: 15px;
                border-radius: 6px;
                margin-bottom: 20px;
                border-left: 4px solid;
            }
            
            .alert-warning {
                background: #fff3cd;
                border-color: #ffc107;
                color: #856404;
            }
            
            .alert-success {
                background: #d4edda;
                border-color: #28a745;
                color: #155724;
            }
            
            .alert-info {
                background: #d1ecf1;
                border-color: #17a2b8;
                color: #0c5460;
            }
            
            .unmapped-table {
                width: 100%;
                border-collapse: collapse;
                margin-top: 20px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            }
            
            .unmapped-table th,
            .unmapped-table td {
                padding: 12px 15px;
                text-align: left;
                border-bottom: 1px solid #e0e0e0;
            }
            
            .unmapped-table th {
                background: #34495e;
                color: white;
                font-weight: 600;
                position: sticky;
                top: 0;
            }
            
            .unmapped-table tr:hover {
                background: #f8f9fa;
            }
            
            .quantity-badge {
                background: #e74c3c;
                color: white;
                padding: 4px 8px;
                border-radius: 12px;
                font-size: 0.9em;
                font-weight: bold;
            }
            
            .code-tag {
                background: #f1c40f;
                color: #2c3e50;
                padding: 2px 6px;
                border-radius: 4px;
                font-family: monospace;
                font-size: 0.9em;
            }
            
            .loading {
                text-align: center;
                padding: 20px;
                color: #7f8c8d;
            }
            
            .instructions {
                background: #e8f4f8;
                border: 1px solid #bee5eb;
                border-radius: 6px;
                padding: 20px;
                margin-bottom: 20px;
            }
            
            .instructions h3 {
                margin-top: 0;
                color: #0c5460;
            }
            
            .instructions ol {
                margin: 10px 0;
                padding-left: 20px;
            }
            
            .instructions li {
                margin: 8px 0;
            }
            
            .google-sheets-link {
                display: inline-block;
                background: #27ae60;
                color: white;
                text-decoration: none;
                padding: 10px 20px;
                border-radius: 6px;
                margin: 10px 5px;
                font-weight: bold;
            }
            
            .google-sheets-link:hover {
                background: #229954;
                text-decoration: none;
                color: white;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🔍 未マッピング商品管理</h1>
                <p>楽天商品のマッピング状況確認と修正</p>
            </div>
            
            <div class="instructions">
                <h3>📋 マッピング修正手順</h3>
                <ol>
                    <li><strong>未マッピング商品を確認</strong> - 下記の表で未マッピング商品を確認</li>
                    <li><strong>Google Sheetsで追加</strong> - 対応するシートにマッピング情報を追加</li>
                    <li><strong>再マッピング実行</strong> - 「再マッピング実行」ボタンで自動同期</li>
                </ol>
                
                <div style="margin-top: 15px;">
                    <strong>Google Sheets:</strong>
                    <a href="https://docs.google.com/spreadsheets/d/1mLg1N0a1wubEIdKSouiW_jDaWUnuFLBxj8greczuS3E/edit#gid=1290908701" 
                       target="_blank" class="google-sheets-link">📊 商品番号マッピング基本表</a>
                    <a href="https://docs.google.com/spreadsheets/d/1mLg1N0a1wubEIdKSouiW_jDaWUnuFLBxj8greczuS3E/edit#gid=1695475455" 
                       target="_blank" class="google-sheets-link">🔤 選択肢コード対応表</a>
                </div>
            </div>
            
            <div class="status-bar">
                <div class="status-info">
                    <span id="unmapped-status">未マッピング商品を確認中...</span>
                </div>
                <button id="remapping-btn" class="remapping-btn" onclick="executeRemapping()" disabled>
                    🔄 再マッピング実行
                </button>
            </div>
            
            <div id="alert-container"></div>
            
            <div id="unmapped-content">
                <div class="loading">
                    <p>🔍 未マッピング商品を確認しています...</p>
                </div>
            </div>
        </div>
        
        <script>
            let unmappedData = null;
            
            async function loadUnmappedProducts() {
                try {
                    const response = await fetch('/api/unmapped_products');
                    const data = await response.json();
                    
                    if (data.status === 'success') {
                        unmappedData = data;
                        displayUnmappedProducts(data);
                        updateStatus(data);
                    } else {
                        showAlert('error', 'データ取得エラー: ' + data.message);
                    }
                } catch (error) {
                    showAlert('error', 'ネットワークエラー: ' + error.message);
                }
            }
            
            function displayUnmappedProducts(data) {
                const container = document.getElementById('unmapped-content');
                
                if (data.unmapped_count === 0) {
                    container.innerHTML = `
                        <div class="alert alert-success">
                            <h3>✅ 未マッピング商品はありません</h3>
                            <p>全ての商品が正しくマッピングされています。</p>
                        </div>
                    `;
                    return;
                }
                
                let tableHTML = `
                    <div class="alert alert-warning">
                        <h3>⚠️ ${data.unmapped_count}種類の未マッピング商品が見つかりました</h3>
                        <p>サンプル ${data.sample_size}件中の検出結果です。Google Sheetsでマッピングを追加してください。</p>
                    </div>
                    
                    <table class="unmapped-table">
                        <thead>
                            <tr>
                                <th>商品名</th>
                                <th>Choice Code</th>
                                <th>楽天商品番号</th>
                                <th>数量</th>
                                <th>注文回数</th>
                                <th>最新注文日</th>
                            </tr>
                        </thead>
                        <tbody>
                `;
                
                data.unmapped_products.forEach(product => {
                    tableHTML += `
                        <tr>
                            <td><strong>${product.product_name || '商品名なし'}</strong></td>
                            <td>${product.choice_code ? `<span class="code-tag">${product.choice_code}</span>` : '-'}</td>
                            <td>${product.rakuten_item_number ? `<span class="code-tag">${product.rakuten_item_number}</span>` : '-'}</td>
                            <td><span class="quantity-badge">${product.total_quantity}個</span></td>
                            <td>${product.order_count}回</td>
                            <td>${product.latest_order_date ? new Date(product.latest_order_date).toLocaleDateString('ja-JP') : '-'}</td>
                        </tr>
                    `;
                });
                
                tableHTML += `
                        </tbody>
                    </table>
                `;
                
                container.innerHTML = tableHTML;
            }
            
            function updateStatus(data) {
                const statusElement = document.getElementById('unmapped-status');
                const remappingBtn = document.getElementById('remapping-btn');
                
                if (data.unmapped_count === 0) {
                    statusElement.textContent = '✅ 未マッピング商品なし';
                    remappingBtn.disabled = true;
                    remappingBtn.textContent = '✅ マッピング完了';
                } else {
                    statusElement.textContent = `⚠️ ${data.unmapped_count}種類の未マッピング商品`;
                    remappingBtn.disabled = false;
                    remappingBtn.textContent = '🔄 再マッピング実行';
                }
            }
            
            async function executeRemapping() {
                const btn = document.getElementById('remapping-btn');
                const originalText = btn.textContent;
                
                // ボタン無効化
                btn.disabled = true;
                btn.textContent = '🔄 処理中...';
                
                try {
                    showAlert('info', '🔄 Google Sheets同期とマッピング更新を実行中...');
                    
                    const response = await fetch('/api/remapping', {
                        method: 'POST'
                    });
                    const data = await response.json();
                    
                    if (data.status === 'success') {
                        showAlert('success', 
                            `✅ ${data.message}\\n` +
                            `📊 処理結果: ${data.mapping_stats.mapped_items}/${data.mapping_stats.total_items}件 ` +
                            `(成功率: ${data.mapping_stats.success_rate}%)`
                        );
                        
                        // 再読み込み
                        setTimeout(() => {
                            loadUnmappedProducts();
                        }, 2000);
                    } else {
                        showAlert('error', '❌ 再マッピング失敗: ' + data.message);
                    }
                } catch (error) {
                    showAlert('error', '❌ エラー: ' + error.message);
                } finally {
                    // ボタン復活
                    setTimeout(() => {
                        btn.disabled = false;
                        btn.textContent = originalText;
                    }, 3000);
                }
            }
            
            function showAlert(type, message) {
                const container = document.getElementById('alert-container');
                const alertClass = type === 'error' ? 'alert-warning' : 
                                 type === 'success' ? 'alert-success' : 'alert-info';
                
                container.innerHTML = `
                    <div class="alert ${alertClass}">
                        ${message.replace(/\\n/g, '<br>')}
                    </div>
                `;
                
                // 5秒後に自動削除
                setTimeout(() => {
                    container.innerHTML = '';
                }, 5000);
            }
            
            // ページ読み込み時に実行
            window.addEventListener('load', loadUnmappedProducts);
            
            // 30秒ごとに自動更新
            setInterval(loadUnmappedProducts, 30000);
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)
'''

    try:
        # main_cloudrun.pyを読み込み
        with open('main_cloudrun.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # APIを追加する位置を見つける
        # 最後のAPIの後に追加
        insert_position = content.rfind('if __name__ == "__main__":')
        
        if insert_position == -1:
            print("main_cloudrun.pyの構造が予期と異なります。")
            return False
        
        # APIコードを挿入
        new_content = content[:insert_position] + api_code + '\n\n' + content[insert_position:]
        
        # ファイルに書き込み
        with open('main_cloudrun.py', 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print("✅ main_cloudrun.pyに未マッピング商品管理機能を追加しました。")
        print("\n追加された機能:")
        print("  - GET /api/unmapped_products - 未マッピング商品取得")
        print("  - POST /api/remapping - 再マッピング実行")
        print("  - GET /unmapped-dashboard - 未マッピング商品ダッシュボード")
        
        return True
        
    except Exception as e:
        print(f"エラー: {str(e)}")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "execute":
        add_unmapped_apis_to_main()
    else:
        print("main_cloudrun.pyに未マッピング商品管理機能を追加するスクリプトです。")
        print("\n実行方法:")
        print("  python add_unmapped_dashboard_api.py execute")
        print("\n追加される機能:")
        print("  1. 未マッピング商品表示API")
        print("  2. 再マッピング実行API（Google Sheets同期込み）")
        print("  3. 管理ダッシュボード画面")