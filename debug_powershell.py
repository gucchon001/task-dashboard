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

print("=== PowerShellコマンドのデバッグ ===")

# テスト1: 基本的なGet-ScheduledTaskコマンド
print("\n1. 基本的なGet-ScheduledTaskコマンド:")
command1 = 'Get-ScheduledTask | Select-Object -First 3 TaskName, State'
success1, result1 = tm._execute_ps_command('192.168.1.57', command1)
print(f"Success: {success1}")
print(f"Result: {result1}")

# テスト2: JSON変換を含むコマンド
print("\n2. JSON変換を含むコマンド:")
command2 = '''
Get-ScheduledTask | Select-Object -First 2 -Property TaskName, State | 
ConvertTo-Json -Compress
'''
success2, result2 = tm._execute_ps_command('192.168.1.57', command2)
print(f"Success: {success2}")
print(f"Result: {result2}")

# テスト3: 現在のapp.pyで使用しているコマンド
print("\n3. app.pyで使用しているコマンド:")
command3 = '''
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
Get-ScheduledTask -TaskPath '\\*' | 
Select-Object -Property TaskName, State, @{Name='NextRunTime';Expression={$_.NextRunTime}}, @{Name='LastRunTime';Expression={$_.LastRunTime}}, @{Name='LastTaskResult';Expression={$_.LastTaskResult}}, @{Name='Description';Expression={$_.Description}}, @{Name='Trigger';Expression={($_.Triggers | ForEach-Object { $_ | Out-String }) -join '; '}} | 
Select-Object -First 2 |
ConvertTo-Json -Compress -Depth 3
'''
success3, result3 = tm._execute_ps_command('192.168.1.57', command3)
print(f"Success: {success3}")
print(f"Result: {result3}")

# テスト4: シンプルなJSON変換
print("\n4. シンプルなJSON変換:")
command4 = '''
Get-ScheduledTask | Select-Object -First 1 TaskName, State | ConvertTo-Json
'''
success4, result4 = tm._execute_ps_command('192.168.1.57', command4)
print(f"Success: {success4}")
print(f"Result: {result4}") 