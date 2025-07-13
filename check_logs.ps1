# ログファイルを確認するスクリプト

$logFile = "C:\temp\task_debug.log"

if (Test-Path $logFile) {
    Write-Host "=== ログファイルの内容 ===" -ForegroundColor Green
    Get-Content $logFile -Encoding UTF8
} else {
    Write-Host "ログファイルが見つかりません: $logFile" -ForegroundColor Red
    Write-Host "アプリケーションを実行してダッシュボードにアクセスしてください。" -ForegroundColor Yellow
} 