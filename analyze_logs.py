import subprocess
import os
import json
from datetime import datetime

# ディレクトリを変更
os.chdir(r"C:\Users\naoot\Desktop\ｐ\sizukatest\rakuten-order-sync")

print("=== Cloud Buildログ分析スクリプト ===")
print(f"実行時刻: {datetime.now()}")
print()

# 最新のビルドを取得
print("1. 最新のビルド情報を取得中...")
result = subprocess.run(
    ["gcloud", "builds", "list", "--limit=5", "--format=json"],
    capture_output=True,
    text=True,
    encoding='utf-8',
    shell=True
)

if result.returncode == 0 and result.stdout:
    try:
        builds = json.loads(result.stdout)
        if builds:
            latest_build = builds[0]
            build_id = latest_build['id']
            
            print(f"\n最新のビルドID: {build_id}")
            print(f"ステータス: {latest_build['status']}")
            print(f"開始時刻: {latest_build.get('startTime', 'N/A')}")
            
            # ビルドログを取得
            print("\n2. ビルドログを取得中...")
            log_result = subprocess.run(
                ["gcloud", "builds", "log", build_id],
                capture_output=True,
                text=True,
                encoding='utf-8',
                shell=True
            )
            
            if log_result.returncode == 0:
                with open("build_log_analysis.txt", "w", encoding='utf-8') as f:
                    f.write("=== Cloud Build ログ分析 ===\n")
                    f.write(f"ビルドID: {build_id}\n")
                    f.write(f"ステータス: {latest_build['status']}\n")
                    f.write("\n")
                    
                    # 重要な行を抽出
                    lines = log_result.stdout.split('\n')
                    
                    f.write("=== requirements.txt 関連 ===\n")
                    for line in lines:
                        if 'requirements' in line.lower():
                            f.write(line + "\n")
                    
                    f.write("\n=== Google API 関連 ===\n")
                    for line in lines:
                        if 'google' in line.lower() and ('api' in line.lower() or 'sheets' in line.lower()):
                            f.write(line + "\n")
                    
                    f.write("\n=== エラーとWarning ===\n")
                    for line in lines:
                        if 'error' in line.lower() or 'warning' in line.lower():
                            f.write(line + "\n")
                    
                    f.write("\n=== 全ログ (最後の100行) ===\n")
                    for line in lines[-100:]:
                        f.write(line + "\n")
                
                print("ログ分析完了: build_log_analysis.txt")
            else:
                print(f"ログ取得エラー: {log_result.stderr}")
                
    except json.JSONDecodeError as e:
        print(f"JSONパースエラー: {e}")
        print(f"出力: {result.stdout[:500]}")
else:
    print(f"ビルド一覧取得エラー: {result.stderr}")

# Cloud Runのログも取得
print("\n3. Cloud Runサービスログを取得中...")
run_result = subprocess.run(
    ["gcloud", "run", "services", "logs", "read", "rakuten-order-sync", 
     "--region", "asia-northeast1", "--limit", "50", "--format=json"],
    capture_output=True,
    text=True,
    encoding='utf-8',
    shell=True
)

if run_result.returncode == 0 and run_result.stdout:
    with open("service_log_analysis.txt", "w", encoding='utf-8') as f:
        f.write("=== Cloud Run サービスログ分析 ===\n")
        f.write(f"取得時刻: {datetime.now()}\n\n")
        
        try:
            logs = json.loads(run_result.stdout)
            
            f.write("=== Sheets同期関連のログ ===\n")
            for log in logs:
                text = log.get('textPayload', '')
                if 'sheets' in text.lower() or 'google' in text.lower():
                    f.write(f"{log.get('timestamp', '')}: {text}\n")
            
            f.write("\n=== エラーログ ===\n")
            for log in logs:
                text = log.get('textPayload', '')
                if 'error' in text.lower():
                    f.write(f"{log.get('timestamp', '')}: {text}\n")
                    
        except json.JSONDecodeError:
            # JSON形式でない場合はテキストとして処理
            f.write("=== 生ログ ===\n")
            f.write(run_result.stdout)
    
    print("サービスログ分析完了: service_log_analysis.txt")
else:
    print(f"サービスログ取得エラー: {run_result.stderr}")

print("\n分析完了！")
print("生成されたファイル:")
print("- build_log_analysis.txt")
print("- service_log_analysis.txt")