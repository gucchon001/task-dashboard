# ==============================================================================
# Streamlitアプリケーション本体 (app.py)
# ==============================================================================
# このファイルを実行することで、タスク管理ダッシュボードが起動します。
# 前提として、これまでに作成した各モジュールが`core`というサブフォルダ内に
# 格納されている必要があります。
#
# 起動コマンド:
# streamlit run app.py
# ==============================================================================

import streamlit as st
import pandas as pd
import os
import json
import plotly.express as px
import winrm # 実際のWinRM通信のために追加
import datetime

# --- バックエンドモジュールのインポート ---
# 実際には、これらのファイルは `core` フォルダに配置します。
# このサンプルでは、便宜上同一ファイル内に記述していますが、
# 構造を理解しやすくするため、あえてインポート文を記述しています。
from core.config_manager import ConfigManager
from core.db_manager import DBManager
from core.task_manager import TaskManager
from core.notification_manager import NotificationManager
from core.ai_analyzer import AIAnalyzer
from core.error_manager import ErrorManager

# --- 実際のモジュール定義 (本来は別ファイル) ---
# この部分は、前のステップで作成した `backend_modules_v4` の内容と同じです。
# Streamlitアプリの動作を理解するために、ここに含めています。
import sqlite3
import logging
import requests

# ログ設定
import os
log_dir = os.path.join(os.path.dirname(__file__), 'logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'app.log')
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

class ConfigManager:
    def __init__(self, path='data/config.json'):
        self.config_path = path
        self.config_data = {}
        self.load_config()
    def load_config(self):
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r', encoding='utf-8') as f: self.config_data = json.load(f)
        else:
            self.config_data = {"pcs": [], "pc_groups": [], "task_folders": ["\\"], "notification": {"enabled": False, "google_chat_webhook_url": ""}, "admin": {"password_hash": ""}, "api_keys": {"gemini": ""}}
            self.save_config()
    def save_config(self):
        with open(self.config_path, 'w', encoding='utf-8') as f: json.dump(self.config_data, f, indent=2, ensure_ascii=False)
    def get_config(self): return self.config_data
    def update_config(self, new_config_data):
        self.config_data = new_config_data
        self.save_config()

class DBManager:
    def __init__(self, path='data/logs.db'):
        self.db_path = path
        self._create_tables_if_not_exists()
    def _get_connection(self): return sqlite3.connect(self.db_path)
    def _create_tables_if_not_exists(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('CREATE TABLE IF NOT EXISTS execution_logs (log_id INTEGER PRIMARY KEY, recorded_at TEXT, pc_name TEXT, task_path TEXT, task_name TEXT, result_code INTEGER, result_message TEXT, ai_analysis TEXT)')
            cursor.execute('CREATE TABLE IF NOT EXISTS audit_logs (audit_id INTEGER PRIMARY KEY, timestamp TEXT, user_identifier TEXT, action_type TEXT, target_pc TEXT, target_task TEXT, details TEXT)')
            conn.commit()
    def add_execution_log(self, log_data):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            log_data['recorded_at'] = datetime.datetime.now().isoformat()
            keys, placeholders = ', '.join(log_data.keys()), ', '.join(['?'] * len(log_data))
            cursor.execute(f"INSERT INTO execution_logs ({keys}) VALUES ({placeholders})", list(log_data.values()))
            conn.commit()
            return cursor.lastrowid
    def search_execution_logs(self, **kwargs):
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            query, params = "SELECT * FROM execution_logs WHERE 1=1", []
            if kwargs.get('pc_name'): query += " AND pc_name LIKE ?"; params.append(f"%{kwargs['pc_name']}%")
            if kwargs.get('task_name'): query += " AND task_name LIKE ?"; params.append(f"%{kwargs['task_name']}%")
            if kwargs.get('start_date'): query += " AND date(recorded_at) >= ?"; params.append(str(kwargs['start_date']))
            if kwargs.get('end_date'): query += " AND date(recorded_at) <= ?"; params.append(str(kwargs['end_date']))
            query += " ORDER BY recorded_at DESC"
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    def add_audit_log(self, audit_data):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            audit_data['timestamp'] = datetime.datetime.now().isoformat()
            keys, placeholders = ', '.join(audit_data.keys()), ', '.join(['?'] * len(audit_data))
            cursor.execute(f"INSERT INTO audit_logs ({keys}) VALUES ({placeholders})", list(audit_data.values()))
            conn.commit()

class TaskManager:
    """リモートPCのタスクスケジューラを操作するクラス。"""
    def __init__(self, config_manager, db_manager, user, password):
        self.config_manager = config_manager
        self.db_manager = db_manager
        self.user = user
        self.password = password

    def _execute_ps_command(self, pc_ip, command):
        """指定されたPCでPowerShellコマンドをリモート実行する。"""
        logging.info(f"=== PowerShellコマンド実行開始: {pc_ip} ===")
        logging.info(f"コマンド:\n{command}")
        
        try:
            session = winrm.Session(
                f'http://{pc_ip}:5985/wsman',
                auth=(self.user, self.password),
                transport='ntlm',
                server_cert_validation='ignore',
                read_timeout_sec=30,
                operation_timeout_sec=20
            )
            result = session.run_ps(command)
            
            stdout = result.std_out.decode('utf-8', errors='replace') if result.std_out else ""
            stderr = result.std_err.decode('utf-8', errors='replace') if result.std_err else ""

            logging.info(f"実行結果 - Status: {result.status_code}, StdOut長: {len(stdout)}, StdErr長: {len(stderr)}")
            
            if stdout:
                logging.info(f"StdOut (最初の500文字): {stdout[:500]}")
            if stderr:
                logging.error(f"StdErr: {stderr}")

            if result.status_code == 0:
                logging.info(f"=== PowerShellコマンド実行成功: {pc_ip} ===")
                return True, stdout
            else:
                logging.error(f"Error on {pc_ip}. Status code: {result.status_code}. Error: {stderr}")
                return False, stderr
        except Exception as e:
            logging.error(f"Failed to execute command on {pc_ip}: {e}")
            return False, str(e)

    def get_tasks_from_pc(self, pc_ip):
        """指定されたPCから手動作成タスクを取得する。"""
        logging.info(f"=== タスク取得開始: {pc_ip} ===")
        
        # 分割されたPowerShellコマンド
        # ステップ1: 最も短いコマンド
        command1 = """
        [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
        Get-ScheduledTask | Where-Object { 
            $_.Author -like '*\\*' -and 
            $_.Author -notlike '*NT AUTHORITY*' -and
            $_.Author -notlike '*$(@%SystemRoot%*' -and
            $_.Author -notlike '*$(@%systemroot%*'
        } | ConvertTo-Json -Compress -Depth 2
        """
        
        # ステップ2: 詳細情報を取得（必要に応じて）
        command2 = """
        [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
        $tasks = Get-ScheduledTask | Where-Object { 
            $_.Author -like '*\\*' -and 
            $_.Author -notlike '*NT AUTHORITY*' -and
            $_.Author -notlike '*$(@%SystemRoot%*' -and
            $_.Author -notlike '*$(@%systemroot%*'
        }
        
        $result = @()
        foreach ($task in $tasks) {
            $nextRun = $null
            $lastRun = $null
            $lastTaskResult = $null
            
            try {
                $taskInfo = Get-ScheduledTaskInfo -TaskName $task.TaskName -ErrorAction SilentlyContinue
                if ($taskInfo) {
                    if ($taskInfo.NextRunTime) {
                        $nextRun = $taskInfo.NextRunTime.ToString("yyyy-MM-dd HH:mm:ss")
                    }
                    if ($taskInfo.LastRunTime) {
                        $lastRun = $taskInfo.LastRunTime.ToString("yyyy-MM-dd HH:mm:ss")
                    }
                    if ($taskInfo.LastTaskResult -ne $null) {
                        $lastTaskResult = $taskInfo.LastTaskResult
                    }
                }
            } catch {
                if ($task.NextRunTime) {
                    $nextRun = $task.NextRunTime.ToString("yyyy-MM-dd HH:mm:ss")
                }
                if ($task.LastRunTime) {
                    $lastRun = $task.LastRunTime.ToString("yyyy-MM-dd HH:mm:ss")
                }
            }
            
            $taskInfo = [PSCustomObject]@{
                TaskName = $task.TaskName
                State = $task.State
                NextRunTime = $nextRun
                LastRunTime = $lastRun
                LastTaskResult = if ($lastTaskResult -ne $null) { $lastTaskResult } else { $task.LastTaskResult }
                Description = $task.Description
                TaskPath = $task.TaskPath
                Author = $task.Author
                Trigger = (($task.Triggers | ForEach-Object {
                    "Enabled: $($_.Enabled)`n" +
                    "StartBoundary: $($_.StartBoundary)`n" +
                    "EndBoundary: $($_.EndBoundary)`n" +
                    "ExecutionTimeLimit: $($_.ExecutionTimeLimit)`n" +
                    "Id: $($_.Id)`n" +
                    "Repetition: $($_.Repetition)"
                }) -join '; ')
            }
            $result += $taskInfo
        }
        
        if ($result.Count -gt 0) {
            Write-Error "実行時間情報のサンプル（最初の3件）:"
            $result | Select-Object -First 3 | ForEach-Object {
                Write-Error "TaskName: $($_.TaskName), NextRun: $($_.NextRunTime), LastRun: $($_.LastRunTime)"
            }
        }
        
        $result | ConvertTo-Json -Compress -Depth 3
        """
        
        # コマンドを実行（まず短いコマンドを試す）
        logging.info(f"=== PowerShellコマンド実行開始: {pc_ip} ===")
        success, result = self._execute_ps_command(pc_ip, command1)
        
        # 短いコマンドが失敗した場合は長いコマンドを試す
        if not success or not result:
            logging.info(f"短いコマンドが失敗したため、詳細コマンドを試行: {pc_ip}")
            success, result = self._execute_ps_command(pc_ip, command2)
        
        if not success:
            logging.error(f"PowerShell実行失敗: {pc_ip} - {result}")
            return []
            
        if not result or len(result.strip()) == 0:
            logging.warning(f"PowerShell実行結果が空: {pc_ip}")
            return []
            
        logging.info(f"PowerShell実行結果 - 成功: {success}, 結果長: {len(result) if result else 0}")
        
        if success and result:
            try:
                logging.info(f"JSON解析開始: {pc_ip}")
                # 改行文字を除去してからJSON解析
                cleaned_result = result.strip().replace('\r', '').replace('\n', '')
                logging.info(f"クリーンアップ後の結果長: {len(cleaned_result)}")
                logging.info(f"結果の最初の200文字: {cleaned_result[:200]}")
                
                tasks = json.loads(cleaned_result)
                logging.info(f"JSON解析成功: {pc_ip}, 取得されたタスク数: {len(tasks) if isinstance(tasks, list) else 1}")
                
                # 単一のタスクの場合、リストに変換
                if isinstance(tasks, dict):
                    tasks = [tasks]
                
                # 短いコマンドの場合は基本的な情報のみなので、詳細情報を補完
                if len(tasks) > 0 and 'NextRunTime' not in tasks[0]:
                    logging.info(f"基本的なタスク情報のみ取得されたため、詳細情報を補完: {pc_ip}")
                    # 基本的な情報のみの場合は、詳細情報を取得
                    success2, result2 = self._execute_ps_command(pc_ip, command2)
                    if success2 and result2:
                        try:
                            cleaned_result2 = result2.strip().replace('\r', '').replace('\n', '')
                            detailed_tasks = json.loads(cleaned_result2)
                            if isinstance(detailed_tasks, dict):
                                detailed_tasks = [detailed_tasks]
                            tasks = detailed_tasks
                            logging.info(f"詳細情報取得成功: {pc_ip}, タスク数: {len(tasks)}")
                        except Exception as e:
                            logging.warning(f"詳細情報の取得に失敗: {pc_ip} - {e}")
                
                # 日付文字列をdatetimeオブジェクトに変換
                for task in tasks:
                    for key in ['NextRunTime', 'LastRunTime']:
                        if task.get(key) and task[key] != 'null':
                            try:
                                # 文字列形式の日付をdatetimeに変換
                                if isinstance(task[key], str):
                                    task[key] = datetime.datetime.fromisoformat(task[key].split('.')[0])
                                    logging.debug(f"日付変換成功: {task.get('TaskName', 'Unknown')} - {key}: {task[key]}")
                            except Exception as e:
                                logging.warning(f"Failed to parse date for {key} in task {task.get('TaskName', 'Unknown')}: {e}")
                                task[key] = None
                        else:
                            task[key] = None
                
                logging.info(f"タスク処理完了: {pc_ip}, 最終タスク数: {len(tasks)}")
                return tasks
                
            except json.JSONDecodeError as e:
                logging.error(f"Failed to parse JSON from {pc_ip}: {e}")
                logging.error(f"JSON解析エラーの詳細 - 結果の最初の500文字: {result[:500] if result else 'None'}")
                logging.error(f"JSON解析エラーの詳細 - 結果の最後の500文字: {result[-500:] if result and len(result) > 500 else 'None'}")
                
                # 結果にデバッグ情報が混入している可能性をチェック
                if result and "取得されたタスク数:" in result:
                    logging.error(f"デバッグ情報が混入しています: {pc_ip}")
                    # デバッグ情報を除去してJSON部分のみを抽出
                    lines = result.strip().split('\n')
                    json_lines = []
                    in_json = False
                    
                    for line in lines:
                        if line.strip().startswith('[') or line.strip().startswith('{'):
                            in_json = True
                        if in_json:
                            json_lines.append(line)
                        if line.strip().endswith(']') or line.strip().endswith('}'):
                            break
                    
                    if json_lines:
                        try:
                            json_str = '\n'.join(json_lines)
                            logging.info(f"JSON部分を抽出して再解析: {pc_ip}")
                            tasks = json.loads(json_str)
                            if isinstance(tasks, dict):
                                tasks = [tasks]
                            logging.info(f"再解析成功: {pc_ip}, タスク数: {len(tasks)}")
                            return tasks
                        except json.JSONDecodeError as e2:
                            logging.error(f"再解析も失敗: {pc_ip} - {e2}")
                
                return []
            except Exception as e:
                logging.error(f"予期しないエラーが発生しました: {pc_ip} - {e}")
                return []
        else:
            logging.error(f"PowerShell実行失敗: {pc_ip} - {result}")
        return []

    def _process_tasks_from_result(self, result, pc_ip):
        """PowerShellの結果を処理してタスクリストを返す"""
        try:
            # 結果からJSON部分を抽出（デバッグ情報を除く）
            lines = result.strip().split('\n')
            json_lines = []
            in_json = False
            
            for line in lines:
                # JSON配列の開始を検出
                if line.strip().startswith('[') and 'TaskName' in line:
                    in_json = True
                    json_lines.append(line)
                elif in_json:
                    json_lines.append(line)
                    # JSON配列の終了を検出
                    if line.strip().endswith(']'):
                        break
            
            if json_lines:
                json_str = '\n'.join(json_lines)
                tasks = json.loads(json_str)
                if isinstance(tasks, dict):
                    tasks = [tasks]
                return tasks
            else:
                # JSONが見つからない場合は、手動作成タスク数を取得して空のリストを返す
                logging.warning(f"JSONデータが見つかりません: {pc_ip}")
                # 手動作成タスク数が0でない場合は、実際にタスクが存在することを示す
                if "手動作成タスク数:" in result:
                    manual_count_line = [line for line in lines if "手動作成タスク数:" in line]
                    if manual_count_line:
                        count_str = manual_count_line[0].split(":")[1].strip()
                        try:
                            count = int(count_str.replace("件", ""))
                            if count > 0:
                                logging.info(f"手動作成タスクが{count}件存在しますが、JSON形式で取得できませんでした")
                        except ValueError:
                            pass
                return []
        except Exception as e:
            logging.error(f"結果処理中にエラーが発生しました: {pc_ip} - {e}")
        return []

    def delete_task(self, pc_ip, task_name, user_identifier='system'):
        """指定されたタスクを削除する。"""
        command = f"Unregister-ScheduledTask -TaskName '{task_name}' -Confirm:$false"
        success, message = self._execute_ps_command(pc_ip, command)
        if success:
            self.db_manager.add_audit_log({"user_identifier": user_identifier, "action_type": "DELETE_TASK", "target_pc": pc_ip, "target_task": task_name, "details": "Task deleted"})
        return success, message
        
    def create_task(self, pc_ip, task_details, user_identifier='system'):
        """新しいタスクを作成する。"""
        exec_type = task_details.get("execution_type", "standard")
        if "Python" in exec_type:
            action = f"New-ScheduledTaskAction -Execute '\"{task_details['program_path']}\"' -Argument '\"{task_details['script_path']}\" {task_details.get('arguments', '')}'"
        else:
            action = f"New-ScheduledTaskAction -Execute '\"{task_details['program_path']}\"' -Argument '{task_details.get('arguments', '')}'"
        
        trigger_info = task_details.get("trigger", {})
        trigger = f"New-ScheduledTaskTrigger -Daily -At {trigger_info.get('at', '03:00')}"
        
        principal = f"New-ScheduledTaskPrincipal -UserId {task_details.get('user', 'SYSTEM')} -RunLevel Highest"
        
        # タスクパスを指定（デフォルトはCustomTasksフォルダ）
        task_path = task_details.get('task_path', '\\CustomTasks\\')
        
        command = f"$action = {action}; $trigger = {trigger}; $principal = {principal}; Register-ScheduledTask -TaskName '{task_details['TaskName']}' -Description '{task_details.get('Description', '')}' -Action $action -Trigger $trigger -Principal $principal -TaskPath '{task_path}'"
        
        success, message = self._execute_ps_command(pc_ip, command)
        if success:
            self.db_manager.add_audit_log({"user_identifier": user_identifier, "action_type": "CREATE_TASK", "target_pc": pc_ip, "target_task": task_details['TaskName'], "details": json.dumps(task_details)})
        return success, message

    def update_task(self, pc_ip, task_name, update_details, user_identifier='system'):
        """既存のタスクの設定を更新する。"""
        try:
            if 'State' in update_details:
                state_cmd = "Enable-ScheduledTask" if update_details['State'] == 'Ready' else "Disable-ScheduledTask"
                command = f"{state_cmd} -TaskName '{task_name}'"
                success, message = self._execute_ps_command(pc_ip, command)
                if success:
                    state_text = "有効" if update_details['State'] == 'Ready' else "無効"
                    self.db_manager.add_audit_log({
                        "user_identifier": user_identifier, 
                        "action_type": "UPDATE_TASK_STATE", 
                        "target_pc": pc_ip, 
                        "target_task": task_name, 
                        "details": json.dumps(update_details)
                    })
                    return True, f"タスク '{task_name}' を{state_text}に変更しました"
                else:
                    return False, f"ステータス変更に失敗しました: {message}"
            
            elif 'Description' in update_details:
                # 説明の更新（PowerShellコマンドで実装）
                command = f"Set-ScheduledTask -TaskName '{task_name}' -Description '{update_details['Description']}'"
                success, message = self._execute_ps_command(pc_ip, command)
                if success:
                    self.db_manager.add_audit_log({
                        "user_identifier": user_identifier, 
                        "action_type": "UPDATE_TASK_DESCRIPTION", 
                        "target_pc": pc_ip, 
                        "target_task": task_name, 
                        "details": json.dumps(update_details)
                    })
                    return True, f"タスク '{task_name}' の説明を更新しました"
                else:
                    return False, f"説明の更新に失敗しました: {message}"
            
            else:
                return False, "サポートされていない更新項目です"
                
        except Exception as e:
            logging.error(f"タスク更新中にエラーが発生しました: {e}")
            return False, f"タスク更新中にエラーが発生しました: {str(e)}"


# --- Streamlit アプリケーション設定 ---
st.set_page_config(
    page_title="タスク管理ダッシュボード", 
    page_icon="🤖", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# カスタムCSSを追加
st.markdown("""
<style>
/* トグルスイッチのスタイル */
.stToggle {
    background-color: #f0f2f6;
    border-radius: 20px;
    padding: 2px;
}

/* 有効状態のトグルスイッチ */
.stToggle > label[data-checked="true"] {
    background-color: #4CAF50;
    color: white;
}

/* 無効状態のトグルスイッチ */
.stToggle > label[data-checked="false"] {
    background-color: #f44336;
    color: white;
}

/* テーブルヘッダーのスタイル */
.table-header {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 12px 8px;
    border-radius: 8px 8px 0 0;
    font-weight: bold;
    text-align: center;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    margin-bottom: 2px;
}

/* テーブル行のスタイル */
.table-row {
    background: white;
    padding: 10px 8px;
    border-radius: 4px;
    margin: 2px 0;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    border-left: 4px solid #667eea;
    transition: all 0.3s ease;
}

.table-row:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 8px rgba(0,0,0,0.15);
    border-left-color: #764ba2;
}

/* テーブルセルのスタイル */
.table-cell {
    padding: 8px;
    border-radius: 4px;
    background: #f8f9fa;
    margin: 1px;
    border: 1px solid #e9ecef;
}

/* ステータス表示のスタイル */
.status-cell {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 4px;
}

/* ボタンのスタイル */
.action-button {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    border: none;
    border-radius: 6px;
    padding: 6px 12px;
    cursor: pointer;
    transition: all 0.3s ease;
    font-size: 12px;
}

.action-button:hover {
    transform: scale(1.05);
    box-shadow: 0 4px 8px rgba(0,0,0,0.2);
}

/* 成功/エラー状態のスタイル */
.status-success {
    color: #28a745;
    font-weight: bold;
}

.status-error {
    color: #dc3545;
    font-weight: bold;
}

.status-warning {
    color: #ffc107;
    font-weight: bold;
}

.status-info {
    color: #17a2b8;
    font-weight: bold;
}
</style>
""", unsafe_allow_html=True)

# --- 認証情報の読み込み ---
def load_credentials():
    try:
        with open('data/credentials.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        st.error("認証情報ファイルが見つかりません。data/credentials.jsonを作成してください。")
        return None
    except Exception as e:
        st.error(f"認証情報の読み込みに失敗しました: {e}")
        return None

def get_pc_credentials(credentials, pc_name):
    """指定されたPCの認証情報を取得する"""
    if not credentials:
        return None, None
    
    pc_creds = credentials.get(pc_name)
    if pc_creds:
        return pc_creds.get('username'), pc_creds.get('password')
    else:
        st.warning(f"PC '{pc_name}'の認証情報が見つかりません。")
        return None, None

# --- PC情報取得関数 ---
def get_pc_info(task_manager, pc_ip, pc_name):
    """PCの詳細情報を取得する"""
    info = {
        'name': pc_name,
        'ip': pc_ip,
        'status': 'Unknown',
        'system_info': {},
        'disk_info': {},
        'memory_info': {},
        'tasks_count': 0
    }
    
    try:
        # 1. 基本接続確認
        success, result = task_manager._execute_ps_command(pc_ip, "Get-Date -Format 'yyyy/MM/dd HH:mm:ss'")
        if success:
            info['status'] = 'Online'
            # 日付文字列をクリーンアップ
            cleaned_date = result.strip().replace('\r', '').replace('\n', '')
            info['last_seen'] = cleaned_date
        else:
            info['status'] = 'Offline'
            return info
        
        # 2. システム情報取得
        success, result = task_manager._execute_ps_command(pc_ip, "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; Get-ComputerInfo | Select-Object WindowsProductName, WindowsVersion, TotalPhysicalMemory | ConvertTo-Json -Compress")
        if success:
            try:
                # 改行文字を除去してからJSON解析
                cleaned_result = result.strip().replace('\r', '').replace('\n', '')
                system_data = json.loads(cleaned_result)
                info['system_info'] = system_data
            except:
                info['system_info'] = {'error': 'JSON parse failed'}
        
        # 3. ディスク情報取得
        success, result = task_manager._execute_ps_command(pc_ip, "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; Get-WmiObject -Class Win32_LogicalDisk | Select-Object DeviceID, Size, FreeSpace | ConvertTo-Json -Compress")
        if success:
            try:
                # 改行文字を除去してからJSON解析
                cleaned_result = result.strip().replace('\r', '').replace('\n', '')
                disk_data = json.loads(cleaned_result)
                info['disk_info'] = disk_data if isinstance(disk_data, list) else [disk_data]
            except:
                info['disk_info'] = []
        
        # 4. メモリ情報取得
        success, result = task_manager._execute_ps_command(pc_ip, "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; Get-WmiObject -Class Win32_OperatingSystem | Select-Object TotalVisibleMemorySize, FreePhysicalMemory | ConvertTo-Json -Compress")
        if success:
            try:
                # 改行文字を除去してからJSON解析
                cleaned_result = result.strip().replace('\r', '').replace('\n', '')
                memory_data = json.loads(cleaned_result)
                info['memory_info'] = memory_data
            except:
                info['memory_info'] = {'error': 'JSON parse failed'}
        
        # 5. タスク数取得
        tasks = task_manager.get_tasks_from_pc(pc_ip)
        info['tasks_count'] = len(tasks) if tasks else 0
        
    except Exception as e:
        info['status'] = 'Error'
        info['error'] = str(e)
    
    return info

# --- 初期化処理 ---
if 'initialized' not in st.session_state:
    logging.info("=== アプリケーション初期化開始 ===")
    CONFIG_PATH = 'data/config.json'
    DB_PATH = 'data/logs.db'
    st.session_state.config_manager = ConfigManager(CONFIG_PATH)
    st.session_state.db_manager = DBManager(DB_PATH)
    st.session_state.error_manager = ErrorManager('data/error_codes.json')
    # TODO: 認証情報を安全に取得する
    DUMMY_USER, DUMMY_PASS = "YOUR_USERNAME", "YOUR_PASSWORD"
    st.session_state.task_manager = TaskManager(st.session_state.config_manager, st.session_state.db_manager, DUMMY_USER, DUMMY_PASS)
    st.session_state.current_view = 'pc_info'  # デフォルトをPC情報に変更
    st.session_state.initialized = True
    logging.info("=== アプリケーション初期化完了 ===")

config_manager = st.session_state.config_manager
db_manager = st.session_state.db_manager
task_manager = st.session_state.task_manager
error_manager = st.session_state.error_manager

# --- 画面描画関数 ---
@st.dialog("タスク詳細")
def task_detail_dialog(task, pc_name, pc_ip):
    # ヘッダー部分
    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
    ">
        <h2 style="margin: 0; color: white;">📋 {task['TaskName']}</h2>
        <p style="margin: 5px 0 0 0; opacity: 0.9;">対象PC: {pc_name} ({pc_ip})</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 状態情報の表示
    state_info = get_task_state_info(task['State'])
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("状態", state_info['status'], delta=None)
    with col2:
        next_run = format_datetime(task.get('NextRunTime'))
        st.metric("次回実行", next_run)
    with col3:
        last_run = format_datetime(task.get('LastRunTime'))
        st.metric("最終実行", last_run)
    
    # エラー情報の表示
    if 'LastTaskResult' in task and task['LastTaskResult'] != 0:
        error_code = task['LastTaskResult']
        error_message = error_manager.get_error_message(error_code)
        
        st.error(f"⚠️ 最終実行でエラーが発生しました (コード: {error_code})")
        st.error(f"エラー内容: {error_message}")
        
        # タイムアウトエラーの場合の対処法を表示
        if error_manager.is_timeout_error(error_code):
            timeout_solutions = error_manager.get_timeout_solutions()
            with st.expander(f"🔧 {timeout_solutions['title']}", expanded=True):
                st.info("**対処法:**")
                for i, step in enumerate(timeout_solutions['steps'], 1):
                    st.write(f"{i}. **{step['title']}**")
                    st.write(f"   {step['description']}")
                    st.write("")
        
        st.write("---")
    
    # 詳細情報の表示
    with st.expander("📊 タスク詳細情報", expanded=True):
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**基本情報**")
            st.write(f"**タスク名:** {task['TaskName']}")
            st.write(f"**PC名:** {task['PC名']}")
            st.write(f"**状態:** {state_info['status']} {state_info['icon']}")
            if 'Author' in task:
                st.write(f"**作成者:** {task['Author']}")
            if 'Description' in task and task['Description']:
                st.write(f"**説明:** {task['Description']}")
        
        with col2:
            st.write("**実行情報**")
            st.write(f"**次回実行:** {format_datetime(task.get('NextRunTime'))}")
            st.write(f"**最終実行:** {format_datetime(task.get('LastRunTime'))}")
            if 'LastTaskResult' in task:
                if task['LastTaskResult'] == 0:
                    result_text = "成功"
                    result_color = "green"
                else:
                    error_message = error_manager.get_error_message(task['LastTaskResult'])
                    result_text = f"エラー (コード: {task['LastTaskResult']}) - {error_message}"
                    result_color = "red"
                st.write(f"**最終結果:** {result_text}")
            if 'Trigger' in task and task['Trigger']:
                trigger_formatted = format_trigger_info(task['Trigger'])
                st.write(f"**トリガー:** {trigger_formatted}")
                # 詳細なトリガー情報を展開可能なセクションに表示
                with st.expander("詳細トリガー情報"):
                    st.code(task['Trigger'], language="text")
    
    # アクションセクション
    st.write("---")
    st.subheader("🔧 アクション")
    
    # ステータストグルセクション
    st.write("**ステータス切り替え**")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # 現在の状態を表示
        current_state = task['State']
        is_currently_enabled = current_state in [3, 4]  # Ready(3) または Running(4)
        
        if is_currently_enabled:
            st.success(f"✅ 現在: 有効 ({state_info['status']})")
        else:
            st.error(f"🔴 現在: 無効 ({state_info['status']})")
    
    with col2:
        # トグルボタン
        if st.button("🔄 ステータスを切り替え", use_container_width=True, type="primary"):
            # PCの認証情報を取得
            credentials = load_credentials()
            username, password = get_pc_credentials(credentials, pc_name)
            if not username or not password:
                st.error(f"❌ {pc_name}の認証情報が見つかりません。")
            else:
                # PCごとにTaskManagerを初期化
                pc_task_manager = TaskManager(
                    st.session_state.config_manager, 
                    st.session_state.db_manager, 
                    username, 
                    password
                )
                
                # 新しい状態を決定
                new_state = "Disabled" if is_currently_enabled else "Ready"
                update_details = {"State": new_state}
                
                success, msg = pc_task_manager.update_task(pc_ip, task['TaskName'], update_details, user_identifier=os.getlogin())
                if success: 
                    st.success(f"✅ ステータスを{'無効' if is_currently_enabled else '有効'}に変更しました")
                    st.rerun()
                else: 
                    st.error(f"❌ ステータス変更に失敗しました: {msg}")
    
    with col3:
        # 手動実行ボタン
        if st.button("▶️ 手動実行", use_container_width=True):
            st.info("🚧 タスク実行機能は今後実装予定です。")
    
    # 編集フォーム
    with st.form("edit_task_form", clear_on_submit=False):
        st.write("**タスク設定の編集**")
        
        col1, col2 = st.columns(2)
        with col1:
            new_description = st.text_area("説明", value=task.get('Description', ''), height=100)
        with col2:
            st.write("**現在の状態:**", state_info['status'])
            st.write("**ステータス変更は上記のトグルボタンを使用してください**")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.form_submit_button("💾 説明を更新", use_container_width=True, type="primary"):
                # PCの認証情報を取得
                credentials = load_credentials()
                username, password = get_pc_credentials(credentials, pc_name)
                if not username or not password:
                    st.error(f"❌ {pc_name}の認証情報が見つかりません。")
                else:
                    # PCごとにTaskManagerを初期化
                    pc_task_manager = TaskManager(
                        st.session_state.config_manager, 
                        st.session_state.db_manager, 
                        username, 
                        password
                    )
                    update_details = {"Description": new_description}
                    
                    success, msg = pc_task_manager.update_task(pc_ip, task['TaskName'], update_details, user_identifier=os.getlogin())
                    if success: 
                        st.success(f"✅ 説明を更新しました")
                        st.rerun()
                    else: 
                        st.error(f"❌ 説明の更新に失敗しました: {msg}")
        
        with col2:
            if st.form_submit_button("🗑️ 削除", use_container_width=True, type="secondary"):
                # 削除確認
                if st.session_state.get("confirm_delete_task", False):
                    # PCの認証情報を取得
                    credentials = load_credentials()
                    username, password = get_pc_credentials(credentials, pc_name)
                    if not username or not password:
                        st.error(f"❌ {pc_name}の認証情報が見つかりません。")
                    else:
                        # PCごとにTaskManagerを初期化
                        pc_task_manager = TaskManager(
                            st.session_state.config_manager, 
                            st.session_state.db_manager, 
                            username, 
                            password
                        )
                        success, msg = pc_task_manager.delete_task(pc_ip, task['TaskName'], user_identifier=os.getlogin())
                        if success: 
                            st.success(f"✅ タスクを削除しました")
                            st.rerun()
                        else: 
                            st.error(f"❌ タスク削除に失敗しました: {msg}")
                else:
                    st.session_state["confirm_delete_task"] = True
                    st.warning("⚠️ 削除を確認するには、もう一度ボタンを押してください。")
    
    # 実行履歴セクション（将来実装）
    st.write("---")
    with st.expander("📈 実行履歴", expanded=False):
        st.info("📊 実行履歴機能は今後実装予定です。")
        # ここに実行履歴の表示を追加予定

@st.dialog("新規タスク作成")
def create_task_dialog():
    # ヘッダー部分
    st.markdown("""
    <div style="
        background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);
        color: white;
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
    ">
        <h2 style="margin: 0; color: white;">➕ 新しいタスクの作成</h2>
        <p style="margin: 5px 0 0 0; opacity: 0.9;">Windowsタスクスケジューラに新しいタスクを追加します</p>
    </div>
    """, unsafe_allow_html=True)
    
    with st.form("create_task_form", clear_on_submit=True):
        # 基本情報セクション
        st.subheader("📋 基本情報")
        
        pc_list = {pc['name']: pc['ip'] for pc in config_manager.get_config().get('pcs', [])}
        if not pc_list:
            st.error("❌ 管理対象PCが設定されていません。管理者設定画面からPCを追加・設定してください。")
            st.stop()
        
        col1, col2 = st.columns(2)
        with col1:
            selected_pc_name = st.selectbox("対象PC *", options=list(pc_list.keys()), help="タスクを実行するPCを選択してください")
        with col2:
            task_name = st.text_input("タスク名 *", placeholder="例: データバックアップ", help="一意のタスク名を入力してください")
        
        description = st.text_area("説明", placeholder="タスクの目的や処理内容を記述してください", height=80)
        
        st.write("---")
        
        # 実行設定セクション
        st.subheader("⚙️ 実行設定")
        
        execution_type = st.selectbox(
            "実行タイプ *", 
            ["標準プログラム (.exe, .bat)", "Python スクリプト", "PowerShell スクリプト"],
            help="実行するプログラムの種類を選択してください"
        )
        
        if "Python" in execution_type:
            col1, col2 = st.columns(2)
            with col1:
                program_path = st.text_input(
                    "python.exeのパス *", 
                    placeholder="C:\\Python311\\python.exe",
                    help="Python実行ファイルのフルパス"
                )
            with col2:
                script_path = st.text_input(
                    "スクリプトのパス (.py) *", 
                    placeholder="\\\\nas-server\\scripts\\my_script.py",
                    help="実行するPythonスクリプトのフルパス"
                )
        elif "PowerShell" in execution_type:
            col1, col2 = st.columns(2)
            with col1:
                program_path = st.text_input(
                    "PowerShellのパス *", 
                    placeholder="C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe",
                    help="PowerShell実行ファイルのフルパス"
                )
            with col2:
                script_path = st.text_input(
                    "スクリプトのパス (.ps1) *", 
                    placeholder="\\\\nas-server\\scripts\\my_script.ps1",
                    help="実行するPowerShellスクリプトのフルパス"
                )
        else:
            col1, col2 = st.columns(2)
            with col1:
                program_path = st.text_input(
                    "プログラム/スクリプトのパス *", 
                    placeholder="\\\\nas-server\\batch\\my_task.bat",
                    help="実行するプログラムまたはスクリプトのフルパス"
                )
            with col2:
                script_path = st.text_input(
                    "引数 (オプション)", 
                    placeholder="引数がある場合は入力してください",
                    help="プログラムに渡す引数（オプション）"
                )
        
        st.write("---")
        
        # スケジュール設定セクション
        st.subheader("📅 スケジュール設定")
        
        col1, col2 = st.columns(2)
        with col1:
            schedule_type = st.selectbox(
                "スケジュールタイプ",
                ["毎日", "毎週", "毎月", "一回限り"],
                help="タスクの実行スケジュールを選択してください"
            )
        with col2:
            start_time = st.time_input("開始時刻", value=datetime.time(9, 0), help="タスクの開始時刻を設定してください")
        
        # スケジュールタイプに応じた追加設定
        if schedule_type == "毎週":
            weekdays = st.multiselect(
                "実行曜日",
                ["月曜日", "火曜日", "水曜日", "木曜日", "金曜日", "土曜日", "日曜日"],
                default=["月曜日"],
                help="タスクを実行する曜日を選択してください"
            )
        elif schedule_type == "毎月":
            month_day = st.number_input("実行日", min_value=1, max_value=31, value=1, help="毎月の実行日を設定してください")
        
        st.write("---")
        
        # 確認・実行セクション
        st.subheader("✅ 確認・実行")
        
        # 入力内容の確認表示
        if task_name and program_path:
            st.info("**入力内容の確認:**")
            st.write(f"**対象PC:** {selected_pc_name}")
            st.write(f"**タスク名:** {task_name}")
            st.write(f"**実行タイプ:** {execution_type}")
            st.write(f"**プログラムパス:** {program_path}")
            if script_path:
                st.write(f"**スクリプトパス:** {script_path}")
            st.write(f"**スケジュール:** {schedule_type} {start_time.strftime('%H:%M')}")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.form_submit_button("🚫 キャンセル", use_container_width=True, type="secondary"):
                st.rerun()
        with col2:
            if st.form_submit_button("✅ 作成", use_container_width=True, type="primary"):
                if not task_name or not program_path:
                    st.warning("⚠️ タスク名とプログラムパスは必須です。")
                else:
                    # 選択されたPCの認証情報を取得
                    credentials = load_credentials()
                    username, password = get_pc_credentials(credentials, selected_pc_name)
                    if not username or not password:
                        st.error(f"❌ {selected_pc_name}の認証情報が見つかりません。")
                    else:
                        # PCごとにTaskManagerを初期化
                        pc_task_manager = TaskManager(
                            st.session_state.config_manager, 
                            st.session_state.db_manager, 
                            username, 
                            password
                        )
                        # 設定されたフォルダパスの最初のフォルダにタスクを作成
                        task_folders = config_manager.get_config().get('task_folders', ['\\CustomTasks\\'])
                        target_folder = task_folders[0] if task_folders else '\\CustomTasks\\'
                        
                        task_details = {
                            "TaskName": task_name, 
                            "Description": description, 
                            "execution_type": execution_type, 
                            "program_path": program_path, 
                            "script_path": script_path,
                            "task_path": target_folder,
                            "schedule_type": schedule_type,
                            "start_time": start_time.strftime('%H:%M')
                        }
                            
                        success, msg = pc_task_manager.create_task(pc_list[selected_pc_name], task_details, user_identifier=os.getlogin())
                        if success: 
                            st.success(f"✅ {msg}")
                            st.rerun()
                        else: 
                            st.error(f"❌ {msg}")

def render_dashboard():
    st.header("ダッシュボード")
    
    # 設定からPC一覧を取得
    config = config_manager.get_config()
    all_pcs = config.get('pcs', [])
    
    if not all_pcs:
        st.warning("管理対象PCが設定されていません。「管理者設定」画面からPCを追加・設定してください。")
        return
    
    # タブの作成（ALL + 各PC）
    tab_names = ["ALL"] + [pc['name'] for pc in all_pcs]
    tabs = st.tabs(tab_names)
    
    # 各タブの内容を処理
    for tab_idx, (tab, pc_name) in enumerate(zip(tabs, tab_names)):
        with tab:
            if pc_name == "ALL":
                # ALLタブ：全PCのタスクを表示
                render_pc_tasks(all_pcs, f"全PC ({len(all_pcs)}台)")
            else:
                # 個別PCタブ：該当PCのタスクのみを表示
                selected_pc = next((pc for pc in all_pcs if pc['name'] == pc_name), None)
                if selected_pc:
                    render_pc_tasks([selected_pc], f"{pc_name}")

def render_pc_tasks(pcs_to_scan, title):
    """指定されたPCのタスクを表示する関数"""
    st.subheader(f"タスク一覧 ({title} - 手動作成タスク)")
    
    # ソートと新規作成の設定
    col1, col2 = st.columns([1, 1])
    with col1:
        # 並べ替え機能を追加
        if f'sort_order_{title}' not in st.session_state:
            st.session_state[f'sort_order_{title}'] = "次回実行日時順"
        sort_order = st.selectbox("並べ替え順序", ["次回実行日時順", "作成日時順", "タスク名順"], key=f"sort_{title}")
        st.session_state[f'sort_order_{title}'] = sort_order
    
    with col2:
        if st.button("＋ 新規タスクを作成", type="primary", use_container_width=True, key=f"create_{title}"):
            create_task_dialog()
    

    
    # タスク情報の取得
    all_tasks = []
    progress_bar = st.progress(0, text="タスク情報を取得中...")
    
    # 認証情報の読み込み
    credentials = load_credentials()
    
    logging.info(f"=== タスク取得処理開始: {title} ===")
    logging.info(f"対象PC数: {len(pcs_to_scan)}")
    
    for i, pc in enumerate(pcs_to_scan):
        progress_bar.progress((i + 1) / len(pcs_to_scan), text=f"{pc['name']}...")
        logging.info(f"=== PC処理開始: {pc['name']} ({pc['ip']}) ===")
        
        # PCごとの認証情報を取得
        username, password = get_pc_credentials(credentials, pc['name'])
        if not username or not password:
            logging.warning(f"{pc['name']}の認証情報が見つかりません。スキップします。")
            st.warning(f"{pc['name']}の認証情報が見つかりません。スキップします。")
            continue
        
        # PCごとにTaskManagerを初期化
        pc_task_manager = TaskManager(
            st.session_state.config_manager, 
            st.session_state.db_manager, 
            username, 
            password
        )
        
        # 手動作成タスクのみを取得（修正済み）
        logging.info(f"=== {pc['name']}からタスク取得開始 ===")
        tasks = pc_task_manager.get_tasks_from_pc(pc['ip'])
        logging.info(f"=== {pc['name']}から取得されたタスク数: {len(tasks)} ===")
        
        for task in tasks:
            task['PC名'] = pc['name']
            task['PC_IP'] = pc['ip']
            all_tasks.append(task)
        
        logging.info(f"=== PC処理完了: {pc['name']}, 累計タスク数: {len(all_tasks)} ===")
    
    progress_bar.empty()
    logging.info(f"=== タスク取得処理完了: {title}, 総タスク数: {len(all_tasks)} ===")

    if not all_tasks:
        st.info("対象のタスクは見つかりませんでした。")
        return

    df = pd.DataFrame(all_tasks)
    
    # デバッグ情報を表示（開発時のみ）
    if st.checkbox("デバッグ情報を表示", key=f"debug_{title}"):
        st.write("**取得されたタスクデータ:**")
        st.write(f"総タスク数: {len(df)}")
        st.write("**State値の分布:**")
        state_counts = df['State'].value_counts()
        st.write(state_counts)
        st.write("**State値の詳細（最初の10件）:**")
        for i, (idx, task) in enumerate(df.head(10).iterrows()):
            st.write(f"{i+1}. {task['TaskName']} - State: {task['State']}")
        st.write("**サンプルデータ:**")
        st.write(df.head(3)[['TaskName', 'State', 'LastTaskResult', 'NextRunTime', 'LastRunTime']])
    

    
    if df.empty:
        st.info("フィルタ条件に一致するタスクは見つかりませんでした。")
        return
    
    # 並べ替え処理
    if st.session_state[f'sort_order_{title}'] == "次回実行日時順":
        df = df.sort_values('NextRunTime', na_position='last')
    elif st.session_state[f'sort_order_{title}'] == "作成日時順":
        df = df.sort_values('LastRunTime', na_position='last')
    elif st.session_state[f'sort_order_{title}'] == "タスク名順":
        df = df.sort_values('TaskName')
    
    # 統計情報の表示
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        total_tasks = len(df)
        st.metric("総タスク数", total_tasks)
    with col2:
        active_tasks = len(df[df['State'].isin([3, 4])])
        st.metric("アクティブ", active_tasks, delta=f"{active_tasks - (total_tasks - active_tasks)}")
    with col3:
        error_tasks = len(df[df['LastTaskResult'] != 0]) if 'LastTaskResult' in df.columns else 0
        st.metric("エラー", error_tasks, delta=f"-{error_tasks}" if error_tasks > 0 else None)
    with col4:
        pc_count = df['PC名'].nunique()
        st.metric("対象PC数", pc_count)
    
    st.write("---")
    
    # テーブル形式でのタスク表示
    st.subheader("タスク詳細一覧")
    
    # ページネーション
    items_per_page = 100  # 1ページあたりの表示件数を100件に設定
    if f'current_page_{title}' not in st.session_state:
        st.session_state[f'current_page_{title}'] = 0
    
    total_pages = (len(df) - 1) // items_per_page + 1
    start_idx = st.session_state[f'current_page_{title}'] * items_per_page
    end_idx = min(start_idx + items_per_page, len(df))
    
    # ページネーションコントロール
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        if st.button("← 前のページ", disabled=st.session_state[f'current_page_{title}'] == 0, key=f"prev_{title}"):
            st.session_state[f'current_page_{title}'] = max(0, st.session_state[f'current_page_{title}'] - 1)
            st.rerun()
    with col2:
        st.write(f"ページ {st.session_state[f'current_page_{title}'] + 1} / {total_pages} ({start_idx + 1}-{end_idx} / {len(df)}件)")
    with col3:
        if st.button("次のページ →", disabled=st.session_state[f'current_page_{title}'] >= total_pages - 1, key=f"next_{title}"):
            st.session_state[f'current_page_{title}'] = min(total_pages - 1, st.session_state[f'current_page_{title}'] + 1)
            st.rerun()
    
    # 現在のページのタスクを表示
    current_page_df = df.iloc[start_idx:end_idx]
    
    # テーブルヘッダー
    col1, col2, col3, col4, col5, col6, col7, col8 = st.columns((1, 1, 2, 1, 1, 1.5, 0.5, 1))
    col1.markdown("<div style='text-align: center; background: #3498db; color: white; padding: 12px 8px; border-radius: 4px; font-weight: bold;'><strong>ステータス</strong></div>", unsafe_allow_html=True)
    col2.markdown("<div style='text-align: center; background: #3498db; color: white; padding: 12px 8px; border-radius: 4px; font-weight: bold;'><strong>タスク名</strong></div>", unsafe_allow_html=True)
    col3.markdown("<div style='text-align: center; background: #3498db; color: white; padding: 12px 8px; border-radius: 4px; font-weight: bold;'><strong>実行結果</strong></div>", unsafe_allow_html=True)
    col4.markdown("<div style='text-align: center; background: #3498db; color: white; padding: 12px 8px; border-radius: 4px; font-weight: bold;'><strong>次回実行</strong></div>", unsafe_allow_html=True)
    col5.markdown("<div style='text-align: center; background: #3498db; color: white; padding: 12px 8px; border-radius: 4px; font-weight: bold;'><strong>最終実行</strong></div>", unsafe_allow_html=True)
    col6.markdown("<div style='text-align: center; background: #3498db; color: white; padding: 12px 8px; border-radius: 4px; font-weight: bold;'><strong>⏱ 開始時刻</strong></div>", unsafe_allow_html=True)
    col7.markdown("<div style='text-align: center; background: #3498db; color: white; padding: 12px 8px; border-radius: 4px; font-weight: bold;'><strong>実行</strong></div>", unsafe_allow_html=True)
    col8.markdown("<div style='text-align: center; background: #3498db; color: white; padding: 12px 8px; border-radius: 4px; font-weight: bold;'><strong>詳細｜設定</strong></div>", unsafe_allow_html=True)
    
    # ヘッダーとボディの間にマージンを追加
    st.markdown("<div style='margin: 20px 0;'></div>", unsafe_allow_html=True)
    
    # テーブルボディ（各行）
    for idx, task in current_page_df.iterrows():
        # 状態に応じたクラスとアイコン
        state_info = get_task_state_info(task['State'])
        
        # 実行結果の判定と表示
        result_info = get_task_result_info(task)
        
        # 日時フォーマット
        next_run = format_datetime(task.get('NextRunTime'))
        last_run = format_datetime(task.get('LastRunTime'))
        
        # 各行の列を作成
        col1, col2, col3, col4, col5, col6, col7, col8 = st.columns((1, 1, 2, 1, 1, 1.5, 0.5, 1))
        
        # ステータス表示（一番左）
        current_state = task['State']
        is_enabled = current_state in [3, 4]  # Ready(3) または Running(4)
        
        with col1:
            # ステータス表示（中央寄せ、縦も中央寄せ）
            if is_enabled:
                st.markdown(f"<div style='text-align: center; display: flex; align-items: center; justify-content: center; min-height: 50px; color: #28a745; font-weight: bold;'>{state_info['icon']} {state_info['status']}</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div style='text-align: center; display: flex; align-items: center; justify-content: center; min-height: 50px; color: #dc3545; font-weight: bold;'>{state_info['icon']} {state_info['status']}</div>", unsafe_allow_html=True)
        
        # データを表示（中央寄せ、縦も中央寄せ）
        col2.markdown(f"<div style='text-align: center; display: flex; align-items: center; justify-content: center; min-height: 50px;'><strong>{task['TaskName']}</strong></div>", unsafe_allow_html=True)
        col3.markdown(f"<div style='text-align: center; display: flex; align-items: center; justify-content: center; min-height: 50px;'>{result_info['icon']} {result_info['status']}</div>", unsafe_allow_html=True)
        col4.markdown(f"<div style='text-align: center; display: flex; align-items: center; justify-content: center; min-height: 50px;'>{next_run}</div>", unsafe_allow_html=True)
        col5.markdown(f"<div style='text-align: center; display: flex; align-items: center; justify-content: center; min-height: 50px;'>{last_run}</div>", unsafe_allow_html=True)
        
        # 開始時刻の表示（中央寄せ、縦も中央寄せ）
        trigger_info = format_trigger_info(task.get('Trigger', ''))
        col6.markdown(f"<div style='text-align: center; display: flex; align-items: center; justify-content: center; min-height: 50px;'>{trigger_info}</div>", unsafe_allow_html=True)
        
        # 手動実行ボタン（詳細｜設定の左）
        with col7:
            if st.button(f"▶️ ", key=f"run_{title}_{idx}", help="タスクを手動実行", use_container_width=True):
                # 手動実行機能（将来実装）
                st.info("🚧 タスク実行機能は今後実装予定です。")
        
        # 詳細ボタン
        with col8:
            if st.button(f"📋", key=f"detail_{title}_{idx}", help="詳細を表示", use_container_width=True):
                task_detail_dialog(task.to_dict(), task['PC名'], task['PC_IP'])
    
    # 一括操作セクション
    st.write("---")
    st.subheader("🔧 一括操作")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**一括ステータス変更:**")
        bulk_action = st.selectbox(
            "操作を選択",
            ["操作なし", "選択したタスクを有効にする", "選択したタスクを無効にする"],
            key=f"bulk_action_{title}"
        )
        
        if bulk_action != "操作なし":
            # 現在のページのタスクから選択可能なタスクを取得
            available_tasks = [(task[1]['TaskName'], task[1]['PC名']) for task in current_page_df.iterrows()]
            selected_tasks = st.multiselect(
                "対象タスクを選択",
                options=available_tasks,
                format_func=lambda x: f"{x[1]} - {x[0]}",
                key=f"bulk_tasks_{title}"
            )
            
            if st.button("🚀 一括実行", key=f"bulk_execute_{title}", type="primary"):
                if selected_tasks:
                    success_count = 0
                    error_count = 0
                    
                    for task_name, pc_name in selected_tasks:
                        # PCの認証情報を取得
                        credentials = load_credentials()
                        username, password = get_pc_credentials(credentials, pc_name)
                        if not username or not password:
                            st.error(f"❌ {pc_name}の認証情報が見つかりません。")
                            continue
                        
                        # PCのIPアドレスを取得
                        pc_ip = next((task[1]['PC_IP'] for task in current_page_df.iterrows() 
                                    if task[1]['PC名'] == pc_name and task[1]['TaskName'] == task_name), None)
                        if not pc_ip:
                            st.error(f"❌ {pc_name}のIPアドレスが見つかりません。")
                            continue
                        
                        # PCごとにTaskManagerを初期化
                        pc_task_manager = TaskManager(
                            st.session_state.config_manager, 
                            st.session_state.db_manager, 
                            username, 
                            password
                        )
                        
                        # 新しい状態を決定
                        new_state = "Ready" if "有効" in bulk_action else "Disabled"
                        update_details = {"State": new_state}
                        
                        success, msg = pc_task_manager.update_task(pc_ip, task_name, update_details, user_identifier=os.getlogin())
                        if success:
                            success_count += 1
                        else:
                            error_count += 1
                            st.error(f"❌ {pc_name} - {task_name}: {msg}")
                    
                    if success_count > 0:
                        st.success(f"✅ {success_count}件のタスクを{'有効' if '有効' in bulk_action else '無効'}に変更しました")
                    if error_count > 0:
                        st.error(f"❌ {error_count}件のタスクでエラーが発生しました")
                    
                    if success_count > 0:
                        st.rerun()
                else:
                    st.warning("⚠️ 対象タスクを選択してください")
    
    with col2:
        st.write("**削除アクション:**")
        
        # 削除確認状態の表示
        if st.session_state.get("confirm_delete_task", False):
            st.warning("⚠️ 削除確認モードが有効です。削除ボタンを押すとタスクが削除されます。")
            if st.button("❌ 削除確認をキャンセル", key=f"cancel_delete_{title}"):
                st.session_state["confirm_delete_task"] = False
                st.rerun()
        
        # 削除確認の切り替え
        if not st.session_state.get("confirm_delete_task", False):
            if st.button("🗑️ 削除確認を有効にする", key=f"enable_delete_{title}"):
                st.session_state["confirm_delete_task"] = True
                st.rerun()
    
    # 削除フォーム
    with st.form(f"delete_form_{title}"):
        col1, col2, col3 = st.columns(3)
        with col1:
            pc_name = st.selectbox("PC名", options=[task[1]['PC名'] for task in current_page_df.iterrows()], key=f"delete_pc_{title}")
        with col2:
            task_name = st.selectbox("タスク名", options=[task[1]['TaskName'] for task in current_page_df.iterrows() if task[1]['PC名'] == pc_name], key=f"delete_task_{title}")
        with col3:
            if st.form_submit_button("🗑️ 削除", use_container_width=True, type="secondary"):
                # 削除確認
                if st.session_state.get("confirm_delete_task", False):
                    # PCの認証情報を取得
                    credentials = load_credentials()
                    username, password = get_pc_credentials(credentials, pc_name)
                    if not username or not password:
                        st.error(f"❌ {pc_name}の認証情報が見つかりません。")
                    else:
                        # PCごとにTaskManagerを初期化
                        pc_task_manager = TaskManager(
                            st.session_state.config_manager, 
                            st.session_state.db_manager, 
                            username, 
                            password
                        )
                        # PCのIPアドレスを取得
                        pc_ip = next((task[1]['PC_IP'] for task in current_page_df.iterrows() if task[1]['PC名'] == pc_name and task[1]['TaskName'] == task_name), None)
                        if pc_ip:
                            success, msg = pc_task_manager.delete_task(pc_ip, task_name, user_identifier=os.getlogin())
                        else:
                            st.error(f"❌ {pc_name}のIPアドレスが見つかりません。")
                            return
                        if success:
                            st.success(f"✅ タスク '{task_name}' を削除しました。")
                            st.session_state["confirm_delete_task"] = False
                            st.rerun()
                        else:
                            st.error(f"❌ タスク削除に失敗しました: {msg}")
                else:
                    st.warning("⚠️ 削除確認を有効にしてから削除してください。")



def get_task_result_info(task):
    """タスクの実行結果に応じた情報を返す"""
    last_task_result = task.get('LastTaskResult')
    
    # LastTaskResultがNone、NaN、または未設定の場合
    if last_task_result is None or pd.isna(last_task_result):
        return {
            'status': '未実行',
            'icon': '⏸️'
        }
    
    # 数値に変換できるかチェック
    try:
        last_task_result_int = int(last_task_result)
    except (ValueError, TypeError):
        return {
            'status': '未実行',
            'icon': '⏸️'
        }
    
    # 成功の場合（0）
    if last_task_result_int == 0:
        return {
            'status': '成功',
            'icon': '✅'
        }
    
    # エラーの場合（0以外）
    try:
        error_message = error_manager.get_error_message(last_task_result_int)
        
        # 実行中の場合は特別な処理
        if "実行中" in error_message or "running" in error_message.lower():
            return {
                'status': '実行中',
                'icon': '🔄'
            }
        
        return {
            'status': error_message,
            'icon': '❌'
        }
    except Exception as e:
        # エラーメッセージの取得に失敗した場合
        return {
            'status': f'エラー (コード: {last_task_result_int})',
            'icon': '❌'
        }

def get_task_state_info(state):
    """タスクの状態に応じた情報を返す"""
    # PowerShell Get-ScheduledTaskのState値の正しい対応表
    # 0: TASK_STATE_UNKNOWN - 状態が不明
    # 1: TASK_STATE_DISABLED - タスクは無効
    # 2: TASK_STATE_QUEUED - タスクは実行キューに入っている
    # 3: TASK_STATE_READY - タスクは実行準備完了
    # 4: TASK_STATE_RUNNING - タスクは実行中
    if state == 0:
        return {
            'status': '不明',
            'icon': '❓',
            'style': 'background-color: #9e9e9e; color: white;'
        }
    elif state == 1:
        return {
            'status': '無効',
            'icon': '🔴',
            'style': 'background-color: #f44336; color: white;'
        }
    elif state == 2:
        return {
            'status': '待機中',
            'icon': '🟡',
            'style': 'background-color: #ff9800; color: white;'
        }
    elif state == 3:
        return {
            'status': '準備完了',
            'icon': '🟢',
            'style': 'background-color: #4caf50; color: white;'
        }
    elif state == 4:
        return {
            'status': '実行中',
            'icon': '🟡',
            'style': 'background-color: #ff9800; color: white;'
        }
    else:
        return {
            'status': '不明',
            'icon': '❓',
            'style': 'background-color: #9e9e9e; color: white;'
        }

def format_datetime(dt_value):
    """日時をフォーマットする"""
    if pd.isna(dt_value) or dt_value is None:
        return "未設定"
    try:
        if isinstance(dt_value, str):
            return dt_value
        return dt_value.strftime("%Y/%m/%d %H:%M")
    except:
        return str(dt_value)

def format_trigger_info(trigger_str):
    """トリガー情報をフォーマットする"""
    if not trigger_str or trigger_str == 'null':
        return "未設定"
    
    try:
        # トリガー文字列から主要な情報を抽出
        lines = trigger_str.split('\n')
        
        # 設定時間と繰り返し間隔を抽出
        start_time = None
        days_interval = None
        hours_interval = None
        minutes_interval = None
        
        for line in lines:
            line = line.strip()
            if 'StartBoundary' in line and ':' in line:
                # StartBoundary: 2024-03-09T06:00:00 形式を処理
                start_time = line.split(':', 1)[1].strip()
            elif 'DaysInterval' in line and ':' in line:
                days_interval = line.split(':', 1)[1].strip()
            elif 'HoursInterval' in line and ':' in line:
                hours_interval = line.split(':', 1)[1].strip()
            elif 'MinutesInterval' in line and ':' in line:
                minutes_interval = line.split(':', 1)[1].strip()
        
        # 設定時刻のフォーマット
        time_str = "未設定"
        if start_time:
            try:
                # ISO形式の日時を読みやすい形式に変換
                if 'T' in start_time:
                    # 2024-03-09T06:00:00 形式を処理
                    date_part, time_part = start_time.split('T')
                    time_only = time_part.split(':')[:2]  # 時:分のみ取得
                    time_str = f"{time_only[0]}:{time_only[1]}"
                else:
                    time_str = start_time
            except:
                time_str = start_time
        
        # 頻度のフォーマット（繰り返し表示を削除）
        frequency_str = "未設定"
        interval_parts = []
        if days_interval and days_interval != '0':
            interval_parts.append(f"{days_interval}日")
        if hours_interval and hours_interval != '0':
            interval_parts.append(f"{hours_interval}時間")
        if minutes_interval and minutes_interval != '0':
            interval_parts.append(f"{minutes_interval}分")
        
        if interval_parts:
            frequency_str = " | ".join(interval_parts)
        
        # 頻度が「未設定」の場合は時刻のみを返す
        if frequency_str == "未設定":
            return time_str
        else:
            return f"{time_str} | {frequency_str}"
    except:
        return "トリガーあり"

def render_logs():
    st.header("実行結果ログ")
    with st.expander("ログを検索", expanded=True):
        col1, col2, col3, col4 = st.columns(4)
        with col1: pc_name = st.text_input("PC名")
        with col2: task_name = st.text_input("タスク名")
        with col3: start_date = st.date_input("期間 (開始)", value=None)
        with col4: end_date = st.date_input("期間 (終了)", value=None)
        if st.button("検索"):
            st.session_state.log_search_results = db_manager.search_execution_logs(pc_name=pc_name, task_name=task_name, start_date=start_date, end_date=end_date)
    if 'log_search_results' in st.session_state:
        st.dataframe(pd.DataFrame(st.session_state.log_search_results), use_container_width=True, hide_index=True)

def render_reports():
    st.header("サマリーレポート")
    logs = db_manager.search_execution_logs()
    if not logs:
        st.warning("分析対象のログデータがありません。")
        return
    df = pd.DataFrame(logs)
    df['result_code'] = pd.to_numeric(df['result_code'], errors='coerce')
    df['recorded_at'] = pd.to_datetime(df['recorded_at'], errors='coerce')
    st.subheader("タスク実行状況")
    col1, col2 = st.columns(2)
    with col1:
        status_counts = df['result_code'].apply(lambda x: '成功' if x == 0 else '失敗').value_counts()
        fig_pie = px.pie(status_counts, values=status_counts.values, names=status_counts.index, title='タスク成功率', color=status_counts.index, color_discrete_map={'成功':'#2ca02c', '失敗':'#d62728'})
        st.plotly_chart(fig_pie, use_container_width=True)
    with col2:
        df_errors = df[df['result_code'] != 0].copy()
        df_errors['date'] = df_errors['recorded_at'].dt.date
        error_counts_by_day = df_errors.groupby('date').size().reset_index(name='counts')
        fig_bar = px.bar(error_counts_by_day, x='date', y='counts', title='日別エラー発生件数', labels={'date': '日付', 'counts': 'エラー数'})
        st.plotly_chart(fig_bar, use_container_width=True)

def render_admin_settings():
    st.header("管理者設定")
    password = st.text_input("管理者パスワードを入力してください", type="password")
    if password != "admin": st.warning("パスワードが違います。"); st.stop()
    st.success("認証成功")
    
    # タブの作成
    tab1, tab2, tab3 = st.tabs(["PC設定", "通知設定", "エラーコード管理"])
    
    with tab1:
        config_data = config_manager.get_config()
        with st.form("admin_settings_form"):
            st.subheader("管理対象PC設定")
            edited_pcs = st.data_editor(pd.DataFrame(config_data.get('pcs', [])), num_rows="dynamic", use_container_width=True)
            
            st.subheader("PCグループ設定")
            edited_pc_groups = st.data_editor(pd.DataFrame(config_data.get('pc_groups', [])), num_rows="dynamic", use_container_width=True)
            
            submitted = st.form_submit_button("設定を保存")
            if submitted:
                config_data['pcs'] = edited_pcs.to_dict('records')
                config_data['pc_groups'] = edited_pc_groups.to_dict('records')
                config_manager.update_config(config_data)
                st.success("設定を保存しました。")
    
    with tab2:
        config_data = config_manager.get_config()
        with st.form("notification_settings_form"):
            st.subheader("通知設定")
            notification_enabled = st.checkbox("Google Chat通知を有効にする", value=config_data['notification']['enabled'])
            webhook_url = st.text_input("Webhook URL", value=config_data['notification']['google_chat_webhook_url'])
            submitted = st.form_submit_button("通知設定を保存")
            if submitted:
                config_data['notification']['enabled'] = notification_enabled
                config_data['notification']['google_chat_webhook_url'] = webhook_url
                config_manager.update_config(config_data)
                st.success("通知設定を保存しました。")
    
    with tab3:
        st.subheader("エラーコード管理")
        
        # 現在のエラーコード一覧を表示
        st.write("**現在のエラーコード一覧:**")
        error_codes_df = pd.DataFrame([
            {"エラーコード": code, "説明": message}
            for code, message in error_manager.error_codes.items()
        ])
        st.dataframe(error_codes_df, use_container_width=True)
        
        # 新しいエラーコードの追加
        with st.form("add_error_code_form"):
            st.write("**新しいエラーコードを追加:**")
            col1, col2 = st.columns(2)
            with col1:
                new_error_code = st.text_input("エラーコード", placeholder="例: 0x00041306 または 124")
            with col2:
                new_error_message = st.text_input("エラーメッセージ", placeholder="例: タスクがタイムアウトにより停止されました")
            
            is_timeout_error = st.checkbox("タイムアウトエラーとして登録")
            
            if st.form_submit_button("エラーコードを追加"):
                if new_error_code and new_error_message:
                    error_manager.add_error_code(new_error_code, new_error_message)
                    if is_timeout_error:
                        # タイムアウトエラーコードに追加
                        if new_error_code.startswith('0x'):
                            try:
                                decimal_code = int(new_error_code, 16)
                                error_manager.timeout_error_codes.append(decimal_code)
                            except ValueError:
                                st.error("無効な16進数コードです")
                        else:
                            try:
                                decimal_code = int(new_error_code)
                                error_manager.timeout_error_codes.append(decimal_code)
                            except ValueError:
                                st.error("無効なエラーコードです")
                    
                    error_manager.save_error_codes()
                    st.success("エラーコードを追加しました")
                    st.rerun()
                else:
                    st.warning("エラーコードとメッセージを入力してください")
        
        # 設定の再読み込み
        if st.button("設定を再読み込み"):
            error_manager.reload_error_codes()
            st.success("エラーコード設定を再読み込みしました")

# --- PC情報表示関数 ---
def render_pc_info():
    st.header("PC情報")
    
    # 認証情報の読み込み
    credentials = load_credentials()
    if not credentials:
        st.error("認証情報が設定されていません。credentials.jsonを作成してください。")
        return
    
    # 設定からPC一覧とPCグループを取得
    config = config_manager.get_config()
    pcs = config.get('pcs', [])
    pc_groups = config.get('pc_groups', [])
    
    if not pcs:
        st.warning("管理対象PCが設定されていません。")
        return
    
    # PCグループ情報の表示
    if pc_groups:
        st.subheader("PCグループ一覧")
        for group in pc_groups:
            st.info(f"**{group['name']}**: {group['description']}")
        
        st.write("---")
    
    # PC情報の取得
    st.subheader("PC一覧")
    
    # 進捗バー
    progress_bar = st.progress(0, text="PC情報を取得中...")
    
    pc_info_list = []
    for i, pc in enumerate(pcs):
        progress_bar.progress((i + 1) / len(pcs), text=f"{pc['name']}...")
        
        # PCごとの認証情報を取得
        username, password = get_pc_credentials(credentials, pc['name'])
        if not username or not password:
            # 認証情報が取得できない場合はスキップ
            pc_info = {
                'name': pc['name'],
                'ip': pc['ip'],
                'group': pc.get('group', '未分類'),
                'status': 'Error',
                'error': f'認証情報が見つかりません: {pc["name"]}'
            }
            pc_info_list.append(pc_info)
            continue
        
        # PCごとにTaskManagerを初期化
        pc_task_manager = TaskManager(
            st.session_state.config_manager, 
            st.session_state.db_manager, 
            username, 
            password
        )
        
        pc_info = get_pc_info(pc_task_manager, pc['ip'], pc['name'])
        pc_info['group'] = pc.get('group', '未分類')
        pc_info_list.append(pc_info)
    
    progress_bar.empty()
    
    # PC情報を表示
    for pc_info in pc_info_list:
        group_info = f" [{pc_info['group']}]" if pc_info.get('group') else ""
        with st.expander(f"{pc_info['name']} ({pc_info['ip']}){group_info} - {pc_info['status']}", expanded=True):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("ステータス", pc_info['status'])
                if pc_info['status'] == 'Online':
                    st.metric("最終確認", pc_info.get('last_seen', 'Unknown'))
                st.metric("タスク数", pc_info['tasks_count'])
                if pc_info.get('group'):
                    st.metric("グループ", pc_info['group'])
            
            with col2:
                st.subheader("システム情報")
                if pc_info['system_info'] and 'error' not in pc_info['system_info']:
                    st.write(f"**OS:** {pc_info['system_info'].get('WindowsProductName', 'Unknown')}")
                    st.write(f"**バージョン:** {pc_info['system_info'].get('WindowsVersion', 'Unknown')}")
                    if pc_info['system_info'].get('TotalPhysicalMemory'):
                        memory_gb = pc_info['system_info']['TotalPhysicalMemory'] / (1024**3)
                        st.write(f"**メモリ:** {memory_gb:.1f} GB")
                else:
                    st.write("システム情報の取得に失敗しました")
            
            with col3:
                st.subheader("リソース情報")
                if pc_info['disk_info']:
                    for disk in pc_info['disk_info']:
                        if disk.get('Size') and disk.get('FreeSpace'):
                            total_gb = disk['Size'] / (1024**3)
                            free_gb = disk['FreeSpace'] / (1024**3)
                            used_gb = total_gb - free_gb
                            usage_percent = (used_gb / total_gb) * 100
                            
                            st.write(f"**{disk.get('DeviceID', 'Unknown')}:**")
                            st.progress(usage_percent / 100)
                            st.caption(f"{used_gb:.1f}GB / {total_gb:.1f}GB ({usage_percent:.1f}%)")
                
                if pc_info['memory_info'] and 'error' not in pc_info['memory_info']:
                    total_mb = pc_info['memory_info'].get('TotalVisibleMemorySize', 0) / 1024
                    free_mb = pc_info['memory_info'].get('FreePhysicalMemory', 0) / 1024
                    used_mb = total_mb - free_mb
                    memory_usage = (used_mb / total_mb) * 100 if total_mb > 0 else 0
                    
                    st.write("**メモリ使用率:**")
                    st.progress(memory_usage / 100)
                    st.caption(f"{used_mb:.1f}GB / {total_mb:.1f}GB ({memory_usage:.1f}%)")
            
            # エラー情報の表示
            if pc_info['status'] == 'Error' and 'error' in pc_info:
                st.error(f"エラー: {pc_info['error']}")

# --- サイドバーと画面切り替え ---
with st.sidebar:
    st.title("メニュー")
    if st.button("PC情報", use_container_width=True): st.session_state.current_view = 'pc_info'
    if st.button("ダッシュボード", use_container_width=True): st.session_state.current_view = 'dashboard'
    if st.button("実行結果ログ", use_container_width=True): st.session_state.current_view = 'logs'
    if st.button("レポート", use_container_width=True): st.session_state.current_view = 'reports'
    if st.button("管理者設定", use_container_width=True): st.session_state.current_view = 'admin'

# --- メインコンテンツの表示 ---
if st.session_state.current_view == 'pc_info':
    render_pc_info()
elif st.session_state.current_view == 'dashboard':
    render_dashboard()
elif st.session_state.current_view == 'logs':
    render_logs()
elif st.session_state.current_view == 'reports':
    render_reports()
elif st.session_state.current_view == 'admin':
    render_admin_settings()
