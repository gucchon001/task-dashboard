# テスト用タスクを作成するPowerShellスクリプト

# アクション、トリガー、プリンシパルを作成
$action = New-ScheduledTaskAction -Execute "C:\dev\task-dashboard\test_task.bat"
$trigger = New-ScheduledTaskTrigger -Daily -At "12:00"
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -RunLevel Highest

# タスクを登録
Register-ScheduledTask -TaskName "TestTask" -Description "テスト用タスク" -Action $action -Trigger $trigger -Principal $principal -TaskPath "\CustomTasks\"

Write-Host "Test task created successfully." 