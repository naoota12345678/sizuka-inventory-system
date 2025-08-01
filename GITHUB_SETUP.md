# GitHub Auto Deploy セットアップ手順

## 1. GitHubリポジトリでのSecrets設定

GitHub リポジトリの Settings → Secrets and variables → Actions で以下を追加:

### GCP_SA_KEY
ローカルで生成した `github-actions-key.json` の内容をコピーして設定
(セキュリティのため、このファイルの内容は別途提供します)

### SUPABASE_URL
```
https://jvkkvhdqtotbotjzngcv.supabase.co
```

### SUPABASE_KEY
Supabaseのanon keyを設定 (別途提供)

## 2. 必要なAPI有効化
```bash
gcloud services enable cloudbuild.googleapis.com run.googleapis.com
```

## 3. Git push でデプロイ
mainブランチにpushすると自動的にCloud Runにデプロイされます:

```bash
git add .
git commit -m "Setup Cloud Run auto deploy"
git push origin main
```

## 4. デプロイ状況確認
- GitHub Actions タブでビルド状況確認
- デプロイ完了後、GitHub ActionsのログでサービスURLを確認

## 自動デプロイフロー
1. `git push origin main` 実行
2. GitHub Actions が自動起動
3. Docker イメージビルド
4. Google Container Registry にプッシュ  
5. Cloud Run にデプロイ
6. ヘルスチェック実行
7. 完了