import json
from core.task_manager import TaskManager
from core.config_manager import ConfigManager
from core.db_manager import DBManager

# 設定を読み込み
cm = ConfigManager('data/config.json')
db = DBManager('data/logs.db')

# 認証情報を読み込み
with open('data/credentials.json', 'r', encoding='utf-8') as f:
    credentials = json.load(f)

# EPS50の認証情報を取得
username, password = credentials.get('EPS50', {}).get('username'), credentials.get('EPS50', {}).get('password')

if not username or not password:
    print("EPS50の認証情報が見つかりません")
    exit(1)

# TaskManagerを初期化
tm = TaskManager(cm, db, username, password)

print("=== 作成者情報を含む手動タスクの作成 ===")

# 1. 管理者作成のタスク
print("\n1. 管理者作成のタスク:")
command1 = '''
$action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c echo Admin task executed at $(Get-Date) > C:\\temp\\admin_task_log.txt"
$trigger = New-ScheduledTaskTrigger -Daily -At "02:00"
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -RunLevel Highest
Register-ScheduledTask -TaskName "AdminTask" -Action $action -Trigger $trigger -Principal $principal -TaskPath "\\\\CustomTasks\\\\" -Description "手動作成 - 管理者 - 日次バックアップタスク"
'''
success1, result1 = tm._execute_ps_command('192.168.1.57', command1)
print(f"Success: {success1}")
print(f"Result: {result1}")

# 2. ユーザー作成のタスク
print("\n2. ユーザー作成のタスク:")
command2 = '''
$action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c echo User task executed at $(Get-Date) > C:\\temp\\user_task_log.txt"
$trigger = New-ScheduledTaskTrigger -Daily -At "04:00"
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -RunLevel Highest
Register-ScheduledTask -TaskName "UserTask" -Action $action -Trigger $trigger -Principal $principal -TaskPath "\\\\CustomTasks\\\\" -Description "手動作成 - ユーザー - データ整理タスク"
'''
success2, result2 = tm._execute_ps_command('192.168.1.57', command2)
print(f"Success: {success2}")
print(f"Result: {result2}")

# 3. システム作成のタスク（自動生成）
print("\n3. システム作成のタスク（自動生成）:")
command3 = '''
$action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c echo System task executed at $(Get-Date) > C:\\temp\\system_task_log.txt"
$trigger = New-ScheduledTaskTrigger -AtStartup
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -RunLevel Highest
Register-ScheduledTask -TaskName "SystemTask" -Action $action -Trigger $trigger -Principal $principal -TaskPath "\\\\CustomTasks\\\\" -Description "自動生成 - システム - 起動時タスク"
'''
success3, result3 = tm._execute_ps_command('192.168.1.57', command3)
print(f"Success: {success3}")
print(f"Result: {result3}")

# 4. 作成されたタスクを確認
print("\n4. 作成されたタスクを確認:")
command4 = 'Get-ScheduledTask -TaskPath "\\\\CustomTasks\\\\" | Format-Table TaskName, State, Description'
success4, result4 = tm._execute_ps_command('192.168.1.57', command4)
print(f"Success: {success4}")
print(f"Result: {result4}")

print("\n=== 完了 ===") 