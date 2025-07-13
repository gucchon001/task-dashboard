# TaskPathが直下（\）のタスクのみを取得するスクリプト
# 使用方法: .\get_root_tasks.ps1

# エンコーディング設定
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# ルート直下のタスクのみを取得
$rootTasks = Get-ScheduledTask | Where-Object { $_.TaskPath -eq '\' }

# 結果をJSON形式で出力
$result = @()
foreach ($task in $rootTasks) {
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
    $result += $taskInfo
}

# JSON形式で出力
$result | ConvertTo-Json -Compress -Depth 3 