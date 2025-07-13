# 実際の管理対象PC（EPS50）でのタスク一覧取得テスト
# 手動作成タスクのフィルターが正しく動作するか確認

Write-Host "=== 実際の管理対象PCでのタスク一覧取得テスト ===" -ForegroundColor Green

# 1. すべてのルート直下タスクを取得
Write-Host "`n1. すべてのルート直下タスク:" -ForegroundColor Yellow
$allRootTasks = Get-ScheduledTask | Where-Object { $_.TaskPath -eq '\' }
Write-Host "総件数: $($allRootTasks.Count)"

# 2. 作成者情報を確認
Write-Host "`n2. 作成者情報の確認（最初の10件）:" -ForegroundColor Yellow
$allRootTasks | Select-Object TaskName, Author | Select-Object -First 10 | Format-Table -AutoSize

# 3. 手動作成タスクの識別（作成者にバックスラッシュが含まれるもの）
Write-Host "`n3. 手動作成タスクの識別:" -ForegroundColor Yellow
$manualTasks = $allRootTasks | Where-Object { $_.Author -match '\\' }
Write-Host "手動作成タスク件数: $($manualTasks.Count)"
$manualTasks | Select-Object TaskName, Author | Format-Table -AutoSize

# 4. システムタスクの確認（作成者にバックスラッシュが含まれないもの）
Write-Host "`n4. システムタスクの確認:" -ForegroundColor Yellow
$systemTasks = $allRootTasks | Where-Object { $_.Author -notmatch '\\' }
Write-Host "システムタスク件数: $($systemTasks.Count)"
$systemTasks | Select-Object TaskName, Author | Format-Table -AutoSize

# 5. 現在の実装と同じコマンドでテスト
Write-Host "`n5. 現在の実装と同じコマンドでテスト:" -ForegroundColor Yellow
$testCommand = @"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
`$rootTasks = Get-ScheduledTask | Where-Object { `$_.TaskPath -eq '\' }
`$manualTasks = `$rootTasks | Where-Object { `$_.Author -match '\\\\' }
`$result = @()
foreach (`$task in `$manualTasks) {
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
Write-Host $testCommand -ForegroundColor Cyan

# 6. 実際にコマンドを実行して結果を確認
Write-Host "`n6. 実際のコマンド実行結果:" -ForegroundColor Yellow
try {
    $result = Invoke-Expression $testCommand
    Write-Host "JSON結果:"
    Write-Host $result -ForegroundColor Green
} catch {
    Write-Host "エラーが発生しました: $_" -ForegroundColor Red
}

# 7. 作成者パターンの詳細分析
Write-Host "`n7. 作成者パターンの詳細分析:" -ForegroundColor Yellow
$authorPatterns = $allRootTasks | Group-Object { 
    if ($_.Author -match '\\') { "手動作成" } else { "システム" }
} | Sort-Object Name

foreach ($pattern in $authorPatterns) {
    Write-Host "`n$($pattern.Name)タスク ($($pattern.Count)件):" -ForegroundColor Cyan
    $pattern.Group | Select-Object TaskName, Author | Format-Table -AutoSize
}

Write-Host "`n=== テスト完了 ===" -ForegroundColor Green 