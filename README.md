# 牧場 作業記録ボード

スタッフがスマホでこのページを開き、🎤を押して「朝のエサ終わった。23番ちょっと食いが悪い」と話すと、**誰が・何時に・何をしたか** が時系列で積まれていくアプリです。
データは Google スプレッドシートに貯まります。

- ボード兼入力画面：`/`（スマホでもタブレット・PCでも。ホーム画面に追加するとアプリのように開く）
- 閲覧・入力にはパスコード（`BOARD_PASSCODE`）が要る。一度入れればその端末は1年間覚える
- 名前は最初に1回入れれば、その端末が覚える
- 🎤が使えないブラウザでは、入力欄をタップしてキーボードのマイクで話す
- 仕様の詳細：`SPEC.md`（※チェック表方式だった初版の仕様。2026-09-29 に時系列の記録方式へ変更済み）

---

## まず手元で動かす（デモモード）

```bash
npm install
npm run dev
```

http://localhost:3000 を開くと、仮データで動くボードが出ます（`SHEET_ID` が空のあいだはデモモード。データはメモリ上だけで、再起動すると消えます）。
上の欄に「朝のエサ終わった。23番の食いが悪い」のように入れると、記録に積まれます。
`ANTHROPIC_API_KEY` が無いときは、話した文をそのまま記録し、牛番号だけ拾います（あるときは誤変換を直して読みやすい文に整えます）。

---

## 本番のセットアップ

### 1. スプレッドシートを用意
1. Google ドライブで空のスプレッドシートを作る（名前は自由。例：「牧場 作業記録」）
2. URL の `https://docs.google.com/spreadsheets/d/【ここ】/edit` の部分が `SHEET_ID`

シート「記録」は、アプリが初めてアクセスしたときに自動で作ります（旧版が作った「作業リスト」タブは使っていないので消してかまいません）。
「記録」シートの「取消」列を TRUE にすると、その記録はボードから外れます（ボードの「取消」ボタンと同じ）。

### 2. Google サービスアカウント
1. [Google Cloud コンソール](https://console.cloud.google.com/) でプロジェクトを作成
2. 「APIとサービス」→「ライブラリ」→ **Google Sheets API** を有効化
3. 「IAMと管理」→「サービスアカウント」→ 作成 →「鍵」→「新しい鍵を作成（JSON）」
4. JSON の `client_email` が `GOOGLE_SERVICE_ACCOUNT_EMAIL`、`private_key` が `GOOGLE_PRIVATE_KEY`
5. スプレッドシートの「共有」で、その `client_email` を **編集者** として追加
6. サービスアカウントに **IAMロールは付けない**（シートへの権限は「共有」だけで足りる。デフォルトの `-compute@developer.gserviceaccount.com` は編集者ロール付きなので使わない）
7. `.env.local` に鍵を貼るとき、JSON の行末の `,` まで一緒にコピーしない（鍵が読めなくなる）

### 3. Claude API キー
[Anthropic Console](https://console.anthropic.com/) で API キーを発行し `ANTHROPIC_API_KEY` に。
既定モデルは `claude-haiku-4-5-20251001`（速くて安い。1回の日報で数円未満の想定）。変えたいときは `ANTHROPIC_MODEL`。

### 4. Vercel にデプロイ（この案件の実際の構成）
- **GitHub**：`naoota12345678/sizuka-inventory-system` の `main`（⚠️ **公開リポジトリ**。秘密はコミットしない）
  - 旧・在庫システムのリポジトリを再利用している。2026-09-29 に中身を牧場アプリに入れ替えた（旧コードは履歴に残っている）
- **Vercel**：チーム `naoota12345678's projects` のプロジェクト `sizuka-inventory-system`（Pro プラン）
  - `main` への push で本番に自動デプロイされる
  - Root Directory は `.`（リポジトリ直下＝このフォルダの中身がそのまま直下に来る）
  - Framework は `vercel.json` で Next.js を指定（プロジェクト設定側は旧アプリの「Other」のまま）
- **本番URL**：https://sizuka-inventory-system.vercel.app
- **Google Cloud**：プロジェクト `sizuka-inventory-system` のサービスアカウント `farm-board@…`（IAMロールなし）
- 環境変数は Vercel の Settings → Environment Variables（Production）に `.env.example` の全項目を登録
  - `GOOGLE_PRIVATE_KEY`：JSON の値をそのまま貼る（`
` 入りのままでOK）
  - `SHORTCUT_TOKEN`：長めのランダム文字列（iPhoneショートカットに埋め込む合言葉）
  - `BOARD_PASSCODE`：ボードを見るときの数字
- デプロイ後は本番URLを開いて、ログイン画面とボードが出ること・`/api/report` が 401（Vercelのログイン画面ではない）を返すことまで確認する

> Vercel の Hobby（無料）プランは非商用利用が条件です。この案件は Pro プランで運用しています。

---

## スタッフへの配り方
1. 本番のURLとパスコードを伝える（LINE等）
2. スマホでURLを開き、パスコードを入れる
3. 共有ボタン →「ホーム画面に追加」
4. 初回だけ名前を入れる。以後は🎤を押して話し、「記録」を押すだけ

（任意）Siriから話したい人向けに、`POST /api/report`（`name` / `text` / `token`＝`SHORTCUT_TOKEN`）で受け付ける口も残してある。返ってくる `speech` を読み上げれば「記録しました。〜」と確認できる。

---

## 話し方のコツ（スタッフ向けに伝える）
- 牛のことは **番号＋様子**：「23番、食いが悪い」（番号がボタンになり、その牛の7日分の記録が引ける）
- 一度に複数OK：「朝のエサと掃除終わった」
- 記録されたら「記録しました：〜」と整えた文が出るので、聞き間違いがないか目で確かめる

---

## ファイル構成

```
app/
  page.tsx            ボード兼入力画面（パスコード確認）
  login/page.tsx      パスコード入力
  api/report/route.ts 記録の受け口（Claudeで整文・牛番号抽出 → スプシ追記）
  api/board/route.ts  ボード用データ（?date= / ?cow=）
  api/undo/route.ts   取消
  api/login/route.ts  パスコード
components/Board.tsx  ボード画面（上に🎤入力欄、下に時系列）
lib/store.ts          スプシ読み書き（SHEET_ID 未設定ならデモ用メモリ）
lib/classify.ts       Claude で整文・牛番号抽出（失敗時は原文のまま保存）
lib/board.ts          ボードの集計（日ごとの時系列・人ごとの件数・牛ごとの履歴）
lib/time.ts           日本時間の処理
```
