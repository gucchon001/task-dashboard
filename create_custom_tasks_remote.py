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

print("=== CustomTasksフォルダとテストタスクの作成 ===")

# 1. CustomTasksフォルダの存在確認
print("\n1. CustomTasksフォルダの存在確認:")
command1 = 'Get-ScheduledTask -TaskPath "\\CustomTasks\\" -ErrorAction SilentlyContinue'
success1, result1 = tm._execute_ps_command('192.168.1.57', command1)
print(f"Success: {success1}")
print(f"Result: {result1}")

# 2. CustomTasksフォルダを作成（ダミータスクを作成して削除）
print("\n2. CustomTasksフォルダを作成:")
command2 = '''
$action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c echo CustomTasks folder created"
$trigger = New-ScheduledTaskTrigger -AtStartup
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -RunLevel Highest
Register-ScheduledTask -TaskName "CustomTasksFolderCreator" -Action $action -Trigger $trigger -Principal $principal -TaskPath "\\CustomTasks\\" -Description "Creates CustomTasks folder"
'''
success2, result2 = tm._execute_ps_command('192.168.1.57', command2)
print(f"Success: {success2}")
print(f"Result: {result2}")

if success2:
    # ダミータスクを削除
    print("\n3. ダミータスクを削除:")
    command3 = 'Unregister-ScheduledTask -TaskName "CustomTasksFolderCreator" -TaskPath "\\CustomTasks\\" -Confirm:$false'
    success3, result3 = tm._execute_ps_command('192.168.1.57', command3)
    print(f"Success: {success3}")
    print(f"Result: {result3}")

# 4. テストタスクを作成
print("\n4. テストタスクを作成:")
command4 = '''
$action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c echo Test task executed at $(Get-Date) > C:\temp\test_task_log.txt"
$trigger = New-ScheduledTaskTrigger -Daily -At "03:00"
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -RunLevel Highest
Register-ScheduledTask -TaskName "TestTask" -Action $action -Trigger $trigger -Principal $principal -TaskPath "\\CustomTasks\\" -Description "テスト用タスク"
'''
success4, result4 = tm._execute_ps_command('192.168.1.57', command4)
print(f"Success: {success4}")
print(f"Result: {result4}")

# 5. 作成されたタスクを確認
print("\n5. 作成されたタスクを確認:")
command5 = 'Get-ScheduledTask -TaskPath "\\CustomTasks\\" | Format-Table TaskName, State, TaskPath'
success5, result5 = tm._execute_ps_command('192.168.1.57', command5)
print(f"Success: {success5}")
print(f"Result: {result5}")

print("\n=== 完了 ===") 