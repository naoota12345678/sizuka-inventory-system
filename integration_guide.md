# 楽天システム Supabaseクエリ統合ガイド

## 実装完了したコンポーネント

### 1. Supabaseデータベース構造
- **テーブル**: `01_create_tables.sql`
- **ビュー**: `02_create_views.sql`
- **RPC関数**: `03_create_functions.sql`

### 2. Pythonクライアント
- **拡張クライアント**: `enhanced_client.py`
- **分析モジュール**: `enhanced_analytics.py`

## 統合手順

### Step 1: Supabaseの設定

```bash
# 1. SupabaseプロジェクトでSQL実行
# 以下の順序で実行してください：
# 01_create_tables.sql
# 02_create_views.sql  
# 03_create_functions.sql
```

### Step 2: 既存システムの更新

```python
# main.pyに以下を追加

from enhanced_analytics import RakutenAnalytics, create_analytics_endpoints

# 初期化
analytics = RakutenAnalytics(
    supabase_url=Config.SUPABASE_URL,
    supabase_key=Config.SUPABASE_KEY
)

# アナリティクスエンドポイントを追加
create_analytics_endpoints(app, analytics)
```

### Step 3: 注文同期の改善

```python
# 既存のsync-ordersエンドポイントを拡張

@app.get("/sync-orders")
async def sync_orders(days: int = 1):
    try:
        rakuten_api = RakutenAPI()
        end_date = datetime.now(pytz.UTC)
        start_date = end_date - timedelta(days=days)

        # 注文データの取得
        orders = rakuten_api.get_orders(start_date, end_date)
        
        if orders:
            # Supabaseへの保存
            result = rakuten_api.save_to_supabase(orders)
            
            # 🔥 新機能: 分析処理を追加
            analytics_result = analytics.process_order_analytics(orders)
            
            return {
                "status": "success",
                "message": f"{start_date} から {end_date} の注文を同期しました",
                "order_count": len(orders),
                "sync_result": result,
                "analytics_result": analytics_result  # 追加
            }
```

## 新しく利用可能なエンドポイント

### 分析ダッシュボード
```
GET /analytics/dashboard?days_back=7

レスポンス例:
{
  "status": "success",
  "period": "2024-01-24 to 2024-01-31",
  "dashboard": {
    "sales_summary": [...],
    "critical_inventory": [...],
    "top_products": [...]
  },
  "trend": {...},
  "restock_suggestions": {...}
}
```

### 商品別分析
```
GET /analytics/product/{sku}

レスポンス例:
{
  "status": "success",
  "sku": "ABC123",
  "product_info": {...},
  "inventory_history": {...},
  "sales_trend": {...}
}
```

### 在庫補充提案
```
GET /analytics/dashboard から取得可能

または直接:
result = analytics.client.get_restock_suggestions(
    days_to_analyze=14,
    safety_stock_days=5
)
```

### アラート通知
```
GET /analytics/alerts

レスポンス例:
{
  "status": "success",
  "alert_count": 2,
  "alerts": [
    {
      "type": "inventory_critical",
      "message": "3 products need immediate restocking",
      "priority": "high"
    }
  ]
}
```

## 使用例とテスト

### 1. 基本的な動作確認

```python
# enhanced_analytics.pyの最下部で実行
python enhanced_analytics.py
```

### 2. FastAPIでのテスト

```bash
# サーバー起動後
curl http://localhost:8080/analytics/dashboard?days_back=7
curl http://localhost:8080/analytics/alerts
```

### 3. カスタム分析

```python
from enhanced_analytics import RakutenAnalytics

analytics = RakutenAnalytics(supabase_url, supabase_key)

# 週次レポート
report = analytics.generate_weekly_report()

# 商品分析
product_analysis = analytics.analyze_product_performance("YOUR_SKU")

# データエクスポート
export_result = analytics.export_analytics_data("sales", days_back=30)
```

## 主要な改善点

### 1. データの可視化
- 日次売上集計
- 在庫状況のリアルタイム表示
- 商品パフォーマンスランキング

### 2. 在庫管理
- 自動在庫補充提案
- 在庫回転率分析
- 在庫移動履歴トラッキング

### 3. 売上分析
- トレンド分析（移動平均、成長率）
- 商品別パフォーマンス評価
- クロスプラットフォーム比較

### 4. アラート機能
- 在庫不足の自動検知
- 売上下降トレンドの警告
- 緊急度別のアラート分類

## 次のステップ

1. **テスト実行**: 各SQLファイルをSupabaseで実行
2. **システム統合**: main.pyに分析機能を組み込み
3. **UI開発**: ダッシュボード用のフロントエンド作成
4. **他プラットフォーム**: Amazon、カラーミーへの拡張

この実装により、楽天システムは単なる注文同期から、包括的な販売分析プラットフォームに進化します。