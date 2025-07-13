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

# テスト1: CustomTasksフォルダのタスク数を確認
print("=== テスト1: CustomTasksフォルダのタスク数確認 ===")
command1 = 'Get-ScheduledTask -TaskPath "\\CustomTasks\\*" | Measure-Object | Select-Object Count'
success1, result1 = tm._execute_ps_command('192.168.1.57', command1)
print(f"Success: {success1}")
print(f"Result: {result1}")

# テスト2: 全タスク数を確認
print("\n=== テスト2: 全タスク数確認 ===")
command2 = 'Get-ScheduledTask | Measure-Object | Select-Object Count'
success2, result2 = tm._execute_ps_command('192.168.1.57', command2)
print(f"Success: {success2}")
print(f"Result: {result2}")

# テスト3: CustomTasksフォルダの存在確認
print("\n=== テスト3: CustomTasksフォルダの存在確認 ===")
command3 = 'Get-ScheduledTask -TaskPath "\\CustomTasks\\"'
success3, result3 = tm._execute_ps_command('192.168.1.57', command3)
print(f"Success: {success3}")
print(f"Result: {result3}")

# テスト4: ルートフォルダのタスク確認
print("\n=== テスト4: ルートフォルダのタスク確認 ===")
command4 = 'Get-ScheduledTask -TaskPath "\\" | Select-Object -First 5 TaskName, TaskPath'
success4, result4 = tm._execute_ps_command('192.168.1.57', command4)
print(f"Success: {success4}")
print(f"Result: {result4}") 