import json
import logging
import winrm
from datetime import datetime

# ログ設定
import os
log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'task_manager.log')
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

class TaskManager:
    """リモートPCのタスクスケジューラを操作するクラス。"""
    def __init__(self, config_manager, db_manager, user, password):
        """
        コンストラクタ。
        :param config_manager: ConfigManagerインスタンス
        :param db_manager: DBManagerインスタンス
        :param user: リモート接続に使用するユーザー名。
        :param password: リモート接続に使用するパスワード。
        """
        self.config_manager = config_manager
        self.db_manager = db_manager
        self.user = user
        self.password = password

    def _execute_ps_command(self, pc_ip, command):
        """
        指定されたPCでPowerShellコマンドをリモート実行する。
        【注意】このサンプルでは実際には実行せず、コマンドをログ出力するのみ。
        """
        logging.info(f"Executing on {pc_ip}: {command}")
        try:
            # 実際のwinrm接続
            session = winrm.Session(
                f'http://{pc_ip}:5985/wsman',
                auth=(self.user, self.password),
                transport='ntlm',
                server_cert_validation='ignore')
            result = session.run_ps(command)
            if result.status_code == 0:
                return True, result.std_out.decode('utf-8')
            else:
                return False, result.std_err.decode('utf-8')
        except Exception as e:
            logging.error(f"Failed to execute command on {pc_ip}: {e}")
            return False, str(e)

    def get_tasks_from_pc(self, pc_ip, folder_path='\\'):
        """指定されたPCから手動作成タスクを取得する。"""
        logging.info(f"=== タスク取得開始: {pc_ip} ===")
        logging.info(f"フォルダパス: {folder_path}")
        
        # 段階的コマンド実行
        logging.info(f"=== 段階的コマンド実行開始: {pc_ip} ===")
        
        # ステップ1: 基本的なタスク取得とデバッグ（Author絞り込みなし）
        step1_command = f"""
            [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
            $allTasks = Get-ScheduledTask
            $rootTasks = $allTasks | Where-Object {{ $_.TaskPath -eq '' }}
            "全タスク数: $($allTasks.Count)"
            "ルートタスク数: $($rootTasks.Count)"
            "ルートタスクの最初の3件:"
            $rootTasks | Select-Object -First 3 | ForEach-Object {{ "$($_.TaskName) - $($_.TaskPath)" }}
            "=== デバッグ: 最初の5件のタスクパス ==="
            $allTasks | Select-Object -First 5 | ForEach-Object {{ 
                "TaskName: $($_.TaskName), TaskPath: '$($_.TaskPath)', TaskPath長: $($_.TaskPath.Length)" 
            }}
            "=== デバッグ: 空文字列条件のテスト ==="
            $emptyPathCount = ($allTasks | Where-Object {{ $_.TaskPath -eq '' }}).Count
            $backslashCount = ($allTasks | Where-Object {{ $_.TaskPath -eq '\' }}).Count
            $nullCount = ($allTasks | Where-Object {{ $_.TaskPath -eq $null }}).Count
            "空文字列条件: $emptyPathCount件"
            "バックスラッシュ条件: $backslashCount件"
            "null条件: $nullCount件"
        """
        
        # ステップ1.5: Authorによる絞り込み（手動作成タスクのみ）
        step1_5_command = f"""
            [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
            $manualTasks = Get-ScheduledTask | Where-Object {{ 
                $_.Author -like '*\\*' -and 
                $_.Author -notlike '*NT AUTHORITY*' -and
                $_.Author -notlike '*$(@%SystemRoot%*' -and
                $_.Author -notlike '*$(@%systemroot%*'
            }}
            "手動作成タスク数: $($manualTasks.Count)"
            "手動作成タスクの最初の5件:"
            $manualTasks | Select-Object -First 5 | ForEach-Object {{ 
                "TaskName: $($_.TaskName), Author: $($_.Author), TaskPath: '$($_.TaskPath)'" 
            }}
            
            # 詳細情報を取得
            $result = @()
            foreach ($task in $manualTasks) {{
                $nextRun = $null
                $lastRun = $null
                $lastTaskResult = $null
                
                try {{
                    $taskInfo = Get-ScheduledTaskInfo -TaskName $task.TaskName -ErrorAction SilentlyContinue
                    if ($taskInfo) {{
                        if ($taskInfo.NextRunTime) {{
                            $nextRun = $taskInfo.NextRunTime.ToString("yyyy-MM-dd HH:mm:ss")
                        }}
                        if ($taskInfo.LastRunTime) {{
                            $lastRun = $taskInfo.LastRunTime.ToString("yyyy-MM-dd HH:mm:ss")
                        }}
                        if ($taskInfo.LastTaskResult -ne $null) {{
                            $lastTaskResult = $taskInfo.LastTaskResult
                        }}
                    }}
                }} catch {{
                    if ($task.NextRunTime) {{
                        $nextRun = $task.NextRunTime.ToString("yyyy-MM-dd HH:mm:ss")
                    }}
                    if ($task.LastRunTime) {{
                        $lastRun = $task.LastRunTime.ToString("yyyy-MM-dd HH:mm:ss")
                    }}
                }}
                
                $taskInfo = [PSCustomObject]@{{
                    TaskName = $task.TaskName
                    State = $task.State
                    NextRunTime = $nextRun
                    LastRunTime = $lastRun
                    LastTaskResult = if ($lastTaskResult -ne $null) {{ $lastTaskResult }} else {{ $task.LastTaskResult }}
                    Description = $task.Description
                    TaskPath = $task.TaskPath
                    Author = $task.Author
                    Trigger = (($task.Triggers | ForEach-Object {{
                        "Enabled: $($_.Enabled)`n" +
                        "StartBoundary: $($_.StartBoundary)`n" +
                        "EndBoundary: $($_.EndBoundary)`n" +
                        "ExecutionTimeLimit: $($_.ExecutionTimeLimit)`n" +
                        "Id: $($_.Id)`n" +
                        "Repetition: $($_.Repetition)"
                    }}) -join '; ')
                }}
                $result += $taskInfo
            }}
            
            $result | ConvertTo-Json -Compress -Depth 3
        """
        
        # 方法2: schtasksコマンドを使用
        step2_command = f"""
            [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
            "=== schtasksコマンドでルートタスクを取得 ==="
            $schtasksResult = schtasks /query /fo csv /tn "\\" 2>$null
            if ($LASTEXITCODE -eq 0) {{
                "schtasks成功: $($schtasksResult.Count)件"
                $schtasksResult | Select-Object -First 5
            }} else {{
                "schtasks失敗: $LASTEXITCODE"
            }}
            
            "=== schtasksで全タスクを取得 ==="
            $allSchTasks = schtasks /query /fo csv 2>$null
            if ($LASTEXITCODE -eq 0) {{
                "全schtasks数: $($allSchTasks.Count)"
                $allSchTasks | Select-Object -First 5
            }} else {{
                "schtasks全取得失敗: $LASTEXITCODE"
            }}
        """
        
        # 方法3: WMIを使用
        step3_command = f"""
            [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
            "=== WMIでタスクを取得 ==="
            try {{
                $wmiTasks = Get-WmiObject -Class MSFT_ScheduledTask -Namespace "root\\Microsoft\\Windows\\TaskScheduler" -ErrorAction Stop
                "WMIタスク数: $($wmiTasks.Count)"
                $wmiTasks | Select-Object -First 5 | ForEach-Object {{
                    "TaskName: $($_.TaskName), TaskPath: '$($_.TaskPath)'"
                }}
            }} catch {{
                "WMIエラー: $($_.Exception.Message)"
            }}
            
            "=== レジストリからタスク情報を取得 ==="
            try {{
                $registryTasks = Get-ChildItem "HKLM:\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Schedule\\TaskCache\\Tasks" -ErrorAction Stop
                "レジストリタスク数: $($registryTasks.Count)"
                $registryTasks | Select-Object -First 5 | ForEach-Object {{
                    "TaskName: $($_.Name)"
                }}
            }} catch {{
                "レジストリエラー: $($_.Exception.Message)"
            }}
        """
        
        success, debug_result = self._execute_ps_command(pc_ip, step1_command)
        if success:
            logging.info(f"方法1結果: {debug_result}")
        
        # ステップ1.5: Authorによる絞り込みを実行
        success1_5, debug_result1_5 = self._execute_ps_command(pc_ip, step1_5_command)
        if success1_5:
            logging.info(f"方法1.5結果: {debug_result1_5}")
            # Author絞り込みが成功した場合は、その結果を処理
            if "手動作成タスク数:" in debug_result1_5:
                return self._process_tasks_from_result(debug_result1_5, pc_ip)
        
        # 方法2を実行
        success2, debug_result2 = self._execute_ps_command(pc_ip, step2_command)
        if success2:
            logging.info(f"方法2結果: {debug_result2}")
        
        # 方法3を実行
        success3, debug_result3 = self._execute_ps_command(pc_ip, step3_command)
        if success3:
            logging.info(f"方法3結果: {debug_result3}")
        
        # 最も効果的な方法を選択（Author絞り込みを優先）
        if success1_5 and "手動作成タスク数:" in debug_result1_5:
            logging.info("方法1.5（Author絞り込み）が成功")
            return self._process_tasks_from_result(debug_result1_5, pc_ip)
        elif success and "ルートタスク数: 0" not in debug_result:
            logging.info("方法1（Get-ScheduledTask）が成功")
            return self._process_tasks_from_result(debug_result, pc_ip)
        elif success2 and "schtasks成功" in debug_result2:
            logging.info("方法2（schtasks）が成功")
            return self._process_tasks_from_schtasks(debug_result2, pc_ip)
        elif success3 and "WMIタスク数:" in debug_result3:
            logging.info("方法3（WMI）が成功")
            return self._process_tasks_from_wmi(debug_result3, pc_ip)
        else:
            logging.warning("すべての方法が失敗または0件")
            return []

    def _process_tasks_from_result(self, debug_result, pc_ip):
        """
        Get-ScheduledTaskの結果からタスク情報を抽出する。
        """
        logging.info(f"=== タスク情報抽出開始: {pc_ip} ===")
        tasks = []
        try:
            # 出力からJSON部分のみを抽出
            lines = debug_result.strip().split('\n')
            json_start = -1
            
            # JSONデータの開始位置を探す
            for i, line in enumerate(lines):
                if line.strip().startswith('[') or line.strip().startswith('{'):
                    json_start = i
                    break
            
            if json_start == -1:
                logging.error(f"JSONデータが見つかりません: {pc_ip}")
                logging.error(f"Raw result: {debug_result[:500]}...")
                return []
            
            # JSON部分のみを抽出
            json_lines = lines[json_start:]
            json_data = '\n'.join(json_lines)
            
            logging.info(f"JSON解析開始: {pc_ip}")
            tasks = json.loads(json_data)
            # 単一のタスクの場合、リストに変換
            if isinstance(tasks, dict):
                tasks = [tasks]
            logging.info(f"取得されたタスク数: {len(tasks)}")
            # 日付文字列をdatetimeオブジェクトに変換
            for task in tasks:
                for key in ['NextRunTime', 'LastRunTime']:
                    if task.get(key):
                        try:
                            task[key] = datetime.fromisoformat(task[key].split('.')[0])
                        except:
                            task[key] = None
            return tasks
        except json.JSONDecodeError as e:
            logging.error(f"Failed to parse JSON from {pc_ip}: {e}")
            logging.error(f"Raw result: {debug_result[:500]}...")  # 最初の500文字をログ出力
            return []

    def _process_tasks_from_schtasks(self, debug_result, pc_ip):
        """
        schtasksコマンドの結果からタスク情報を抽出する。
        """
        logging.info(f"=== タスク情報抽出開始: {pc_ip} ===")
        tasks = []
        try:
            # schtasksコマンドの結果はCSV形式なので、ヘッダーを含めて解析
            lines = debug_result.strip().split('\n')
            header = lines[0].split(',')
            data_lines = lines[1:]

            for line in data_lines:
                if not line.strip():
                    continue
                values = line.split(',')
                if len(values) < len(header):
                    continue

                task_info = {}
                for i, key in enumerate(header):
                    task_info[key.strip()] = values[i].strip()

                # タスク名とパスを抽出
                task_name = task_info.get('TaskName')
                task_path = task_info.get('TaskPath')

                if not task_name or not task_path:
                    continue

                # タスク情報をPSCustomObjectに変換
                task_ps_object = {
                    'TaskName': task_name,
                    'State': task_info.get('State'),
                    'NextRunTime': task_info.get('NextRunTime'),
                    'LastRunTime': task_info.get('LastRunTime'),
                    'LastTaskResult': task_info.get('LastTaskResult'),
                    'Description': task_info.get('Description'),
                    'TaskPath': task_path,
                    'Author': task_info.get('Author'),
                    'Trigger': task_info.get('Trigger') # schtasksではTriggerがない場合が多い
                }

                # 日付文字列をdatetimeオブジェクトに変換
                for key in ['NextRunTime', 'LastRunTime']:
                    if task_ps_object.get(key):
                        try:
                            task_ps_object[key] = datetime.fromisoformat(task_ps_object[key].split('.')[0])
                        except:
                            task_ps_object[key] = None

                tasks.append(task_ps_object)
            return tasks
        except Exception as e:
            logging.error(f"Failed to process schtasks result from {pc_ip}: {e}")
            logging.error(f"Raw result: {debug_result}")
            return []

    def _process_tasks_from_wmi(self, debug_result, pc_ip):
        """
        WMIの結果からタスク情報を抽出する。
        """
        logging.info(f"=== タスク情報抽出開始: {pc_ip} ===")
        tasks = []
        try:
            # 出力からJSON部分のみを抽出
            lines = debug_result.strip().split('\n')
            json_start = -1
            
            # JSONデータの開始位置を探す
            for i, line in enumerate(lines):
                if line.strip().startswith('[') or line.strip().startswith('{'):
                    json_start = i
                    break
            
            if json_start == -1:
                logging.error(f"JSONデータが見つかりません: {pc_ip}")
                logging.error(f"Raw result: {debug_result[:500]}...")
                return []
            
            # JSON部分のみを抽出
            json_lines = lines[json_start:]
            json_data = '\n'.join(json_lines)
            
            logging.info(f"JSON解析開始: {pc_ip}")
            tasks = json.loads(json_data)
            # 単一のタスクの場合、リストに変換
            if isinstance(tasks, dict):
                tasks = [tasks]
            logging.info(f"取得されたタスク数: {len(tasks)}")
            # 日付文字列をdatetimeオブジェクトに変換
            for task in tasks:
                for key in ['NextRunTime', 'LastRunTime']:
                    if task.get(key):
                        try:
                            task[key] = datetime.fromisoformat(task[key].split('.')[0])
                        except:
                            task[key] = None
            return tasks
        except json.JSONDecodeError as e:
            logging.error(f"Failed to parse JSON from {pc_ip}: {e}")
            logging.error(f"Raw result: {debug_result[:500]}...")  # 最初の500文字をログ出力
            return []

    def get_task_author(self, pc_ip, task_name):
        """指定されたタスクの作成者情報を取得する。"""
        command = f"""
        [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
        Get-ScheduledTask -TaskName '{task_name}' | 
        Select-Object -Property TaskName, Author, @{{Name='TaskPath';Expression={{$_.TaskPath}}}} |
        ConvertTo-Json -Compress
        """
        success, result = self._execute_ps_command(pc_ip, command)
        if success and result:
            try:
                cleaned_result = result.strip().replace('\r', '').replace('\n', '')
                task_info = json.loads(cleaned_result)
                return task_info.get('Author', '')
            except json.JSONDecodeError:
                return ''
        return ''

    def delete_task(self, pc_ip, task_name, user_identifier='system'):
        """指定されたタスクを削除する。"""
        command = f"Unregister-ScheduledTask -TaskName '{task_name}' -Confirm:$false"
        success, message = self._execute_ps_command(pc_ip, command)
        if success:
            # 監査ログを記録
            self.db_manager.add_audit_log({
                "user_identifier": user_identifier,
                "action_type": "DELETE_TASK",
                "target_pc": pc_ip,
                "target_task": task_name,
                "details": "Task deleted"
            })
        return success, message
        
    def create_task(self, pc_ip, task_details, user_identifier='system'):
        """
        新しいタスクを作成する。実行タイプに応じてコマンドを組み立てる。
        task_details = {
            "task_name": "MyNewTask", "description": "...", "user": "SYSTEM",
            "execution_type": "python", # "standard", "python", "python_venv"
            "program_path": "C:\\Python311\\python.exe", # or "C:\\path\\to\\program.exe"
            "script_path": "C:\\scripts\\my_script.py", # for python types
            "arguments": "--arg1 value1",
            "trigger": {"type": "daily", "at": "03:00"}
        }
        """
        # アクション部分の組み立て
        exec_type = task_details.get("execution_type", "standard")
        if exec_type in ["python", "python_venv"]:
            action = f"New-ScheduledTaskAction -Execute '{task_details['program_path']}' -Argument '\"{task_details['script_path']}\" {task_details.get('arguments', '')}'"
        else: # standard
            action = f"New-ScheduledTaskAction -Execute '\"{task_details['program_path']}\"' -Argument '{task_details.get('arguments', '')}'"
        
        # トリガー部分の組み立て (簡易版)
        trigger_info = task_details.get("trigger", {})
        if trigger_info.get("type") == "daily":
            trigger = f"New-ScheduledTaskTrigger -Daily -At {trigger_info.get('at', '03:00')}"
        else: # デフォルト
            trigger = f"New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1)" # 1分後に一度だけ実行

        # プリンシパル（実行ユーザー）
        principal = f"New-ScheduledTaskPrincipal -UserId {task_details.get('user', 'SYSTEM')} -RunLevel Highest"
        
        # 最終的なコマンド
        command = f"$action = {action}; $trigger = {trigger}; $principal = {principal}; Register-ScheduledTask -TaskName '{task_details['task_name']}' -Description '{task_details.get('description', '')}' -Action $action -Trigger $trigger -Principal $principal"
        
        success, message = self._execute_ps_command(pc_ip, command)
        if success:
            self.db_manager.add_audit_log({
                "user_identifier": user_identifier, "action_type": "CREATE_TASK",
                "target_pc": pc_ip, "target_task": task_details['task_name'],
                "details": json.dumps(task_details)
            })
        return success, message

    def run_task_now(self, pc_ip, task_name, user_identifier='system'):
        """指定されたタスクを即時実行する。"""
        command = f"Start-ScheduledTask -TaskName '{task_name}'"
        success, message = self._execute_ps_command(pc_ip, command)
        if success:
            self.db_manager.add_audit_log({
                "user_identifier": user_identifier,
                "action_type": "RUN_TASK",
                "target_pc": pc_ip,
                "target_task": task_name,
                "details": "Task executed manually"
            })
        return success, message

    def enable_task(self, pc_ip, task_name, user_identifier='system'):
        """指定されたタスクを有効化する。"""
        command = f"Enable-ScheduledTask -TaskName '{task_name}'"
        success, message = self._execute_ps_command(pc_ip, command)
        if success:
            self.db_manager.add_audit_log({
                "user_identifier": user_identifier,
                "action_type": "ENABLE_TASK",
                "target_pc": pc_ip,
                "target_task": task_name,
                "details": "Task enabled"
            })
        return success, message

    def disable_task(self, pc_ip, task_name, user_identifier='system'):
        """指定されたタスクを無効化する。"""
        command = f"Disable-ScheduledTask -TaskName '{task_name}'"
        success, message = self._execute_ps_command(pc_ip, command)
        if success:
            self.db_manager.add_audit_log({
                "user_identifier": user_identifier,
                "action_type": "DISABLE_TASK",
                "target_pc": pc_ip,
                "target_task": task_name,
                "details": "Task disabled"
            })
        return success, message
