# CustomTasksフォルダを作成し、テストタスクを追加するスクリプト
# 管理者権限で実行してください

Write-Host "=== CustomTasksフォルダの作成とテストタスクの追加 ===" -ForegroundColor Green

# 1. CustomTasksフォルダを作成（存在しない場合）
Write-Host "1. CustomTasksフォルダを作成中..." -ForegroundColor Yellow
try {
    # フォルダが存在するかチェック
    $folderExists = Get-ScheduledTask -TaskPath "\CustomTasks\" -ErrorAction SilentlyContinue
    if (-not $folderExists) {
        # フォルダを作成するためにダミータスクを作成
        $action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c echo CustomTasks folder created"
        $trigger = New-ScheduledTaskTrigger -AtStartup
        $principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -RunLevel Highest
        Register-ScheduledTask -TaskName "CustomTasksFolderCreator" -Action $action -Trigger $trigger -Principal $principal -TaskPath "\CustomTasks\" -Description "Creates CustomTasks folder"
        
        # ダミータスクを削除
        Unregister-ScheduledTask -TaskName "CustomTasksFolderCreator" -TaskPath "\CustomTasks\" -Confirm:$false
        Write-Host "CustomTasksフォルダを作成しました" -ForegroundColor Green
    } else {
        Write-Host "CustomTasksフォルダは既に存在します" -ForegroundColor Green
    }
} catch {
    Write-Host "エラー: $($_.Exception.Message)" -ForegroundColor Red
}

# 2. テストタスクを作成
Write-Host "2. テストタスクを作成中..." -ForegroundColor Yellow
try {
    $action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c echo Test task executed at $(Get-Date) > C:\temp\test_task_log.txt"
    $trigger = New-ScheduledTaskTrigger -Daily -At "03:00"
    $principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -RunLevel Highest
    Register-ScheduledTask -TaskName "TestTask" -Action $action -Trigger $trigger -Principal $principal -TaskPath "\CustomTasks\" -Description "テスト用タスク"
    Write-Host "TestTaskを作成しました" -ForegroundColor Green
} catch {
    Write-Host "エラー: $($_.Exception.Message)" -ForegroundColor Red
}

# 3. 作成されたタスクを確認
Write-Host "3. 作成されたタスクを確認中..." -ForegroundColor Yellow
try {
    $tasks = Get-ScheduledTask -TaskPath "\CustomTasks\"
    Write-Host "CustomTasksフォルダ内のタスク:" -ForegroundColor Cyan
    $tasks | Format-Table TaskName, State, TaskPath
} catch {
    Write-Host "エラー: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "=== 完了 ===" -ForegroundColor Green 