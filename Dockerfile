# Python 3.9 slim版を使用
FROM python:3.9-slim

# 作業ディレクトリの設定
WORKDIR /app

# pipのアップグレード
RUN pip install --upgrade pip

# 依存関係のコピーとインストール
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir click==8.1.7

# アプリケーションコードのコピー
COPY . .

# Google認証ファイルのコピー（存在する場合のみ）
RUN if [ -f "google-credentials.json" ]; then cp google-credentials.json /app/credentials.json; fi

# 環境変数の設定
ENV GOOGLE_APPLICATION_CREDENTIALS=/app/credentials.json
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Cloud Runは8080ポートを使用
EXPOSE 8080

# アプリケーションの起動
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
