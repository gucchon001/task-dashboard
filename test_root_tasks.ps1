# ルート直下タスクのテスト用スクリプト
Write-Host "=== ルート直下タスクのテスト ===" -ForegroundColor Green

# ルート直下のタスクを取得
$rootTasks = Get-ScheduledTask | Where-Object { $_.TaskPath -eq '\' }

Write-Host "取得されたタスク数: $($rootTasks.Count)" -ForegroundColor Yellow

# 最初の3つのタスクの詳細を表示
Write-Host ""
Write-Host "最初の3つのタスク:" -ForegroundColor Yellow
$rootTasks | Select-Object -First 3 | Select-Object TaskName, TaskPath, Author, State | Format-Table -AutoSize

# Author情報の確認
Write-Host ""
Write-Host "作成者情報の確認:" -ForegroundColor Yellow
$rootTasks | Select-Object Author | Group-Object Author | Format-Table -AutoSize

# JSON形式での出力テスト（最初の2つのタスクのみ）
Write-Host ""
Write-Host "JSON形式での出力テスト:" -ForegroundColor Yellow
$testResult = @()
foreach ($task in ($rootTasks | Select-Object -First 2)) {
    $taskInfo = [PSCustomObject]@{
        TaskName = $task.TaskName
        State = $task.State
        NextRunTime = $task.NextRunTime
        LastRunTime = $task.LastRunTime
        LastTaskResult = $task.LastTaskResult
        Description = $task.Description
        TaskPath = $task.TaskPath
        Author = $task.Author
        Trigger = (($task.Triggers | ForEach-Object { $_ | Out-String }) -join '; ')
    }
    $testResult += $taskInfo
}

$testResult | ConvertTo-Json -Compress -Depth 3 