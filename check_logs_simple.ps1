# シンプルなログ確認スクリプト

Write-Host "=== ログファイルの確認 ===" -ForegroundColor Green

# ローカルログファイル
$localLogFile = "C:\dev\task-dashboard\logs\task_debug.log"
if (Test-Path $localLogFile) {
    Write-Host "ローカルログファイルが見つかりました: $localLogFile" -ForegroundColor Green
    Write-Host "内容:" -ForegroundColor Cyan
    Get-Content $localLogFile -Encoding UTF8
} else {
    Write-Host "ローカルログファイルが見つかりません: $localLogFile" -ForegroundColor Red
}

# アプリケーションログ
$appLogFile = "C:\dev\task-dashboard\logs\app.log"
if (Test-Path $appLogFile) {
    Write-Host "`nアプリケーションログファイルが見つかりました: $appLogFile" -ForegroundColor Green
    Write-Host "内容:" -ForegroundColor Cyan
    Get-Content $appLogFile -Tail 10 -Encoding UTF8
} else {
    Write-Host "`nアプリケーションログファイルが見つかりません" -ForegroundColor Yellow
}

# タスクマネージャーログ
$taskManagerLogFile = "C:\dev\task-dashboard\logs\task_manager.log"
if (Test-Path $taskManagerLogFile) {
    Write-Host "`nタスクマネージャーログファイルが見つかりました: $taskManagerLogFile" -ForegroundColor Green
    Write-Host "内容:" -ForegroundColor Cyan
    Get-Content $taskManagerLogFile -Tail 10 -Encoding UTF8
} else {
    Write-Host "`nタスクマネージャーログファイルが見つかりません" -ForegroundColor Yellow
} 