# リモートPCでのタスク取得テスト
param(
    [string]$ComputerName = "WIN-ND0QPM2D7G1",
    [string]$Username = "Administrator",
    [string]$Password = ""
)

Write-Host "=== リモートPCでのタスク取得テスト ===" -ForegroundColor Green
Write-Host "対象PC: $ComputerName" -ForegroundColor Yellow

# リモートセッションを作成
try {
    $securePassword = ConvertTo-SecureString $Password -AsPlainText -Force
    $credential = New-Object System.Management.Automation.PSCredential($Username, $securePassword)
    
    Write-Host "リモートセッションを作成中..." -ForegroundColor Yellow
    $session = New-PSSession -ComputerName $ComputerName -Credential $credential
    
    Write-Host "リモートPCでタスクを取得中..." -ForegroundColor Yellow
    $remoteTasks = Invoke-Command -Session $session -ScriptBlock {
        Get-ScheduledTask | Where-Object { $_.TaskPath -eq '\' }
    }
    
    Write-Host "取得されたタスク数: $($remoteTasks.Count)" -ForegroundColor Green
    
    # 最初の5つのタスクを表示
    Write-Host ""
    Write-Host "最初の5つのタスク:" -ForegroundColor Yellow
    $remoteTasks | Select-Object -First 5 | Select-Object TaskName, TaskPath, Author, State | Format-Table -AutoSize
    
    # 作成者別統計
    Write-Host ""
    Write-Host "作成者別統計:" -ForegroundColor Yellow
    $remoteTasks | Group-Object Author | Sort-Object Count -Descending | Format-Table -AutoSize
    
    # JSON形式での出力テスト（最初の3つのタスクのみ）
    Write-Host ""
    Write-Host "JSON形式での出力テスト:" -ForegroundColor Yellow
    $testResult = @()
    foreach ($task in ($remoteTasks | Select-Object -First 3)) {
        $taskInfo = [PSCustomObject]@{
            TaskName = $task.TaskName
            State = $task.State
            NextRunTime = $task.NextRunTime
            LastRunTime = $task.LastRunTime
            LastTaskResult = $task.LastTaskResult
            Description = $task.Description
            TaskPath = $task.TaskPath
            Author = $task.Author
        }
        $testResult += $taskInfo
    }
    
    $testResult | ConvertTo-Json -Compress -Depth 3
    
    # セッションを閉じる
    Remove-PSSession $session
    
} catch {
    Write-Host "エラーが発生しました: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "手動でリモートPCに接続してタスクを確認してください。" -ForegroundColor Yellow
    Write-Host "例: Enter-PSSession -ComputerName $ComputerName -Credential \$credential" -ForegroundColor Yellow
} 