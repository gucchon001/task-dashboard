# ローカルのlogsフォルダのログファイルを確認するスクリプト

$localLogFile = "C:\dev\task-dashboard\logs\task_debug.log"

if (Test-Path $localLogFile) {
    Write-Host "=== ローカルログファイルの内容 ===" -ForegroundColor Green
    Get-Content $localLogFile -Encoding UTF8
} else {
    Write-Host "ローカルログファイルが見つかりません: $localLogFile" -ForegroundColor Red
    Write-Host "アプリケーションを実行してダッシュボードにアクセスしてください。" -ForegroundColor Yellow
}

# 他のログファイルも確認
$appLogFile = "C:\dev\task-dashboard\logs\app.log"
$taskManagerLogFile = "C:\dev\task-dashboard\logs\task_manager.log"

Write-Host "`n=== アプリケーションログ ===" -ForegroundColor Cyan
if (Test-Path $appLogFile) {
    Get-Content $appLogFile -Tail 20 -Encoding UTF8
} else {
    Write-Host "アプリケーションログファイルが見つかりません" -ForegroundColor Yellow
}

Write-Host "`n=== タスクマネージャーログ ===" -ForegroundColor Cyan
if (Test-Path $taskManagerLogFile) {
    Get-Content $taskManagerLogFile -Tail 20 -Encoding UTF8
} else {
    Write-Host "タスクマネージャーログファイルが見つかりません" -ForegroundColor Yellow
} 