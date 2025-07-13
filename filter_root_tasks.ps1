# TaskPathが直下ディレクトリ（\）のタスクのみを絞り込むスクリプト
# 作成者: Task Dashboard System
# 用途: ルート直下のタスクのみを表示・管理

Write-Host "=== ルート直下のタスク一覧 ===" -ForegroundColor Green
Write-Host ""

# 方法1: TaskPathで絞り込み
Write-Host "【方法1】TaskPath = '\' で絞り込み" -ForegroundColor Yellow
$rootTasks1 = Get-ScheduledTask | Where-Object { $_.TaskPath -eq '\' }
$rootTasks1 | Select-Object TaskName, TaskPath, Author, State | Format-Table -AutoSize

Write-Host ""
Write-Host "=== 詳細情報 ===" -ForegroundColor Green

# 方法2: より詳細な情報を表示
Write-Host "【方法2】詳細情報付きで表示" -ForegroundColor Yellow
$rootTasks2 = Get-ScheduledTask | Where-Object { $_.TaskPath -eq '\' }
$rootTasks2 | Select-Object TaskName, TaskPath, Author, State, NextRunTime, LastRunTime, Description | Format-Table -AutoSize

Write-Host ""
Write-Host "=== 統計情報 ===" -ForegroundColor Green

# 統計情報
$totalTasks = (Get-ScheduledTask).Count
$rootTasks = (Get-ScheduledTask | Where-Object { $_.TaskPath -eq '\' }).Count
$otherTasks = $totalTasks - $rootTasks

Write-Host "総タスク数: $totalTasks" -ForegroundColor Cyan
Write-Host "ルート直下タスク数: $rootTasks" -ForegroundColor Cyan
Write-Host "その他タスク数: $otherTasks" -ForegroundColor Cyan
Write-Host "ルート直下の割合: $([math]::Round(($rootTasks / $totalTasks) * 100, 2))%" -ForegroundColor Cyan

Write-Host ""
Write-Host "=== 作成者別統計 ===" -ForegroundColor Green

# 作成者別統計
$rootTasksByAuthor = Get-ScheduledTask | Where-Object { $_.TaskPath -eq '\' } | Group-Object Author | Sort-Object Count -Descending
$rootTasksByAuthor | Select-Object Name, Count | Format-Table -AutoSize

Write-Host ""
Write-Host "=== 状態別統計 ===" -ForegroundColor Green

# 状態別統計
$rootTasksByState = Get-ScheduledTask | Where-Object { $_.TaskPath -eq '\' } | Group-Object State | Sort-Object Count -Descending
$rootTasksByState | Select-Object Name, Count | Format-Table -AutoSize

Write-Host ""
Write-Host "=== エクスポート機能 ===" -ForegroundColor Green

# CSVエクスポート機能
$exportPath = ".\root_tasks_$(Get-Date -Format 'yyyyMMdd_HHmmss').csv"
$rootTasksForExport = Get-ScheduledTask | Where-Object { $_.TaskPath -eq '\' } | Select-Object TaskName, TaskPath, Author, State, NextRunTime, LastRunTime, Description
$rootTasksForExport | Export-Csv -Path $exportPath -NoTypeInformation -Encoding UTF8

Write-Host "CSVファイルにエクスポートしました: $exportPath" -ForegroundColor Green

Write-Host ""
Write-Host "=== 使用方法 ===" -ForegroundColor Green
Write-Host "1. このスクリプトを実行すると、ルート直下のタスクのみが表示されます" -ForegroundColor White
Write-Host "2. 統計情報も表示されます" -ForegroundColor White
Write-Host "3. CSVファイルにエクスポートされます" -ForegroundColor White
Write-Host "4. 管理者権限で実行することを推奨します" -ForegroundColor White 