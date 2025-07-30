# SIZUKA- 楽天注文同期システム

楽天の販売サイトとAPIでデータベースをつないで、毎日売り上げ情報を抽出し、売り上げと在庫の管理を行うシステムです。

## 機能

- 楽天APIを使用した注文データの自動取得
- Googleスプレッドシートとの商品マスタ同期
- 在庫管理機能
- 複数商品の名寄せ管理（共通コード体系）
- セット商品・まとめ商品の在庫計算

## システム構成

- **Backend**: FastAPI (Python)
- **Database**: Supabase (PostgreSQL)
- **認証**: 楽天API、Google Sheets API
- **デプロイ**: Google App Engine対応

## セットアップ

1. 環境変数の設定（`.env`ファイル）
```
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
RAKUTEN_SERVICE_SECRET=your_rakuten_secret
RAKUTEN_LICENSE_KEY=your_rakuten_key
PRODUCT_MASTER_SPREADSHEET_ID=your_spreadsheet_id
```

2. 依存関係のインストール
```bash
pip install -r requirements.txt
```

3. データベースの初期化
```bash
# Supabaseダッシュボードでproduct_master/create_tables.sqlを実行
```

4. 起動
```bash
python main.py
```

## 共通コード体系

- **CM**: 単品商品
- **BC**: セット商品（固定/選択）
- **PC**: まとめ商品（固定/複合）

## 今後の拡張予定

- Amazon、Yahoo!ショッピング等の他プラットフォーム対応
- マルチプラットフォーム統合在庫管理
- 売上分析・レポート機能

## ライセンス

プライベートプロジェクト