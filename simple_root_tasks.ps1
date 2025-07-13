# シンプルなルート直下タスク絞り込みスクリプト
# 使用方法: .\simple_root_tasks.ps1

# ルート直下のタスクのみを取得
$rootTasks = Get-ScheduledTask | Where-Object { $_.TaskPath -eq '\' }

# 結果を表示
Write-Host "ルート直下のタスク一覧 ($($rootTasks.Count)件)" -ForegroundColor Green
Write-Host ""

$rootTasks | Select-Object TaskName, TaskPath, Author, State | Format-Table -AutoSize

# 統計情報
Write-Host ""
Write-Host "統計情報:" -ForegroundColor Yellow
Write-Host "総タスク数: $((Get-ScheduledTask).Count)"
Write-Host "ルート直下タスク数: $($rootTasks.Count)"
Write-Host "割合: $([math]::Round(($rootTasks.Count / (Get-ScheduledTask).Count) * 100, 1))%" 