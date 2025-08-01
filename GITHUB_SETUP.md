# GitHub Auto Deploy セットアップ手順

## 1. GitHubリポジトリでのSecrets設定

GitHub リポジトリの Settings → Secrets and variables → Actions で以下のSecretsを追加:

### 必須のSecrets

#### GCP_SA_KEY
Google Cloud サービスアカウントキーのJSON内容
- Google Cloud Console → IAM → Service Accounts で作成
- 権限: Cloud Run Admin, Storage Admin, Cloud Build Editor
- JSONキーをダウンロードしてその内容をコピー

#### SUPABASE_URL
```
https://equrcpeifogdrxoldkpe.supabase.co
```

#### SUPABASE_KEY
```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ
```

#### RAKUTEN_SERVICE_SECRET
```
SP338531_d1NJjF2R5OwZpWH6
```

#### RAKUTEN_LICENSE_KEY
```
SL338531_kUvqO4kIHaMbr9ik
```

#### COLORME_CLIENT_ID
```
d184a84b949f7ce84c5ffae58895deb5fa7f4d2394f72060abcb21cce7217c69
```

#### COLORME_CLIENT_SECRET
```
c5b7f6fce2694674068a2f4d4c09361e289bd556f391bc28aa2123bf0b55e968
```

#### COLORME_REDIRECT_URI
```
http://localhost:8000/callback
```

#### COLORME_ACCESS_TOKEN
```
6b24fdf4ae7cebc761e5514cc418f79e69eb9b346fe4013268277cf6b5dd5c24
```

## 2. Google Cloud サービスアカウントの作成

### 2.1 サービスアカウント作成
```bash
gcloud iam service-accounts create github-actions \
  --description="GitHub Actions service account" \
  --display-name="GitHub Actions"
```

### 2.2 必要な権限を付与
```bash
gcloud projects add-iam-policy-binding sizuka-inventory-system \
  --member="serviceAccount:github-actions@sizuka-inventory-system.iam.gserviceaccount.com" \
  --role="roles/run.admin"

gcloud projects add-iam-policy-binding sizuka-inventory-system \
  --member="serviceAccount:github-actions@sizuka-inventory-system.iam.gserviceaccount.com" \
  --role="roles/storage.admin"

gcloud projects add-iam-policy-binding sizuka-inventory-system \
  --member="serviceAccount:github-actions@sizuka-inventory-system.iam.gserviceaccount.com" \
  --role="roles/cloudbuild.builds.editor"

gcloud projects add-iam-policy-binding sizuka-inventory-system \
  --member="serviceAccount:github-actions@sizuka-inventory-system.iam.gserviceaccount.com" \
  --role="roles/iam.serviceAccountUser"
```

### 2.3 サービスアカウントキーの作成
```bash
gcloud iam service-accounts keys create github-actions-key.json \
  --iam-account=github-actions@sizuka-inventory-system.iam.gserviceaccount.com
```

## 3. 必要なAPI有効化
```bash
gcloud services enable cloudbuild.googleapis.com run.googleapis.com containerregistry.googleapis.com
```

## 4. Git push でデプロイ
mainブランチにpushすると自動的にCloud Runにデプロイされます:

```bash
git add .
git commit -m "Setup GitHub Actions auto deploy"
git push origin main
```

## 5. デプロイ状況確認
- GitHub Actions タブでビルド状況確認
- デプロイ完了後、GitHub ActionsのログでサービスURLを確認
- サービスURL: https://sizuka-inventory-system-1025485420770.asia-northeast1.run.app

## 6. 自動デプロイフロー
1. `git push origin main` 実行
2. GitHub Actions が自動起動（.github/workflows/deploy-cloud-run.yml）
3. Docker イメージビルド（Dockerfile.cloudrun使用）
4. Google Container Registry にプッシュ  
5. Cloud Run にデプロイ（環境変数も自動設定）
6. ヘルスチェック実行
7. 完了

## 7. トラブルシューティング
- GitHub Actions が失敗する場合: Secretsの設定を確認
- デプロイが成功してもアクセスできない場合: IAMポリシーを確認
- データベース接続エラー: SUPABASE_URLとSUPABASE_KEYを確認