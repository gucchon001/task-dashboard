# ルート直下のタスク一覧を取得するテストスクリプト
# 現在の実装と同じ条件でテスト

Write-Host "=== ルート直下のタスク一覧取得テスト ===" -ForegroundColor Green

# 1. 基本的なルート直下タスクの取得
Write-Host "`n1. 基本的なルート直下タスクの取得:" -ForegroundColor Yellow
$rootTasks = Get-ScheduledTask | Where-Object { $_.TaskPath -eq '\' }
Write-Host "取得件数: $($rootTasks.Count)"
$rootTasks | Select-Object TaskName, TaskPath, State | Format-Table -AutoSize

# 2. 現在の実装と同じコマンド（JSON形式）
Write-Host "`n2. 現在の実装と同じコマンド（JSON形式）:" -ForegroundColor Yellow
$jsonCommand = @"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
`$rootTasks = Get-ScheduledTask | Where-Object { `$_.TaskPath -eq '\' }
`$result = @()
foreach (`$task in `$rootTasks) {
    `$taskInfo = [PSCustomObject]@{
        TaskName = `$task.TaskName
        State = `$task.State
        NextRunTime = `$task.NextRunTime
        LastRunTime = `$task.LastRunTime
        LastTaskResult = `$task.LastTaskResult
        Description = `$task.Description
        TaskPath = `$task.TaskPath
        Author = `$task.Author
        Trigger = ((`$task.Triggers | ForEach-Object { `$_ | Out-String }) -join '; ')
    }
    `$result += `$taskInfo
}
`$result | ConvertTo-Json -Compress -Depth 3
"@

Write-Host "実行するコマンド:"
Write-Host $jsonCommand -ForegroundColor Cyan

# 3. アクティブなタスクのみのフィルター
Write-Host "`n3. アクティブなタスクのみ（State = 1 or 3）:" -ForegroundColor Yellow
$activeTasks = $rootTasks | Where-Object { $_.State -in @(1, 3) }
Write-Host "アクティブなタスク件数: $($activeTasks.Count)"
$activeTasks | Select-Object TaskName, State, NextRunTime | Format-Table -AutoSize

# 4. 作成者情報を含む詳細情報
Write-Host "`n4. 作成者情報を含む詳細情報:" -ForegroundColor Yellow
$detailedTasks = $rootTasks | ForEach-Object {
    [PSCustomObject]@{
        TaskName = $_.TaskName
        State = $_.State
        NextRunTime = $_.NextRunTime
        LastRunTime = $_.LastRunTime
        LastTaskResult = $_.LastTaskResult
        Description = $_.Description
        TaskPath = $_.TaskPath
        Author = $_.Author
        Trigger = (($_.Triggers | ForEach-Object { $_ | Out-String }) -join '; ')
    }
}

Write-Host "詳細情報の最初の5件:"
$detailedTasks | Select-Object TaskName, State, Author | Select-Object -First 5 | Format-Table -AutoSize

# 5. 手動作成タスクの識別（作成者にバックスラッシュが含まれるもの）
Write-Host "`n5. 手動作成タスクの識別（作成者にバックスラッシュが含まれるもの）:" -ForegroundColor Yellow
$manualTasks = $rootTasks | Where-Object { $_.Author -match '\\' }
Write-Host "手動作成タスク件数: $($manualTasks.Count)"
$manualTasks | Select-Object TaskName, Author | Format-Table -AutoSize

# 6. システムタスクの除外（作成者にバックスラッシュが含まれないもの）
Write-Host "`n6. システムタスクの除外（作成者にバックスラッシュが含まれないもの）:" -ForegroundColor Yellow
$systemTasks = $rootTasks | Where-Object { $_.Author -notmatch '\\' }
Write-Host "システムタスク件数: $($systemTasks.Count)"
$systemTasks | Select-Object TaskName, Author | Select-Object -First 5 | Format-Table -AutoSize

# 7. 最終的な推奨フィルター（手動作成タスクのみ）
Write-Host "`n7. 最終的な推奨フィルター（手動作成タスクのみ）:" -ForegroundColor Yellow
$recommendedTasks = $rootTasks | Where-Object { $_.Author -match '\\' } | ForEach-Object {
    [PSCustomObject]@{
        TaskName = $_.TaskName
        State = $_.State
        NextRunTime = $_.NextRunTime
        LastRunTime = $_.LastRunTime
        LastTaskResult = $_.LastTaskResult
        Description = $_.Description
        TaskPath = $_.TaskPath
        Author = $_.Author
        Trigger = (($_.Triggers | ForEach-Object { $_ | Out-String }) -join '; ')
    }
}

Write-Host "推奨フィルター適用後の件数: $($recommendedTasks.Count)"
$recommendedTasks | Select-Object TaskName, State, Author | Format-Table -AutoSize

Write-Host "`n=== テスト完了 ===" -ForegroundColor Green 