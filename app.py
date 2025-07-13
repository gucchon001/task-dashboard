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

# --- バックエンドモジュールのインポート ---
# 実際には、これらのファイルは `core` フォルダに配置します。
# このサンプルでは、便宜上同一ファイル内に記述していますが、
# 構造を理解しやすくするため、あえてインポート文を記述しています。
from core.config_manager import ConfigManager
from core.db_manager import DBManager
from core.task_manager import TaskManager
from core.notification_manager import NotificationManager
from core.ai_analyzer import AIAnalyzer

# --- 実際のモジュール定義 (本来は別ファイル) ---
# この部分は、前のステップで作成した `backend_modules_v4` の内容と同じです。
# Streamlitアプリの動作を理解するために、ここに含めています。
import sqlite3
from datetime import datetime
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
            log_data['recorded_at'] = datetime.now().isoformat()
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
            audit_data['timestamp'] = datetime.now().isoformat()
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

            if result.status_code == 0:
                return True, stdout
            else:
                logging.error(f"Error on {pc_ip}. Status code: {result.status_code}. Error: {stderr}")
                return False, stderr
        except Exception as e:
            logging.error(f"Failed to execute command on {pc_ip}: {e}")
            return False, str(e)

    def get_tasks_from_pc(self, pc_ip):
        """指定されたPCから手動作成タスクを取得する。"""
        command = """
        [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
        $manualTasks = Get-ScheduledTask | Where-Object { 
            $_.Author -like '*\\*' -and 
            $_.Author -notlike '*NT AUTHORITY*' -and
            $_.Author -notlike '*$(@%SystemRoot%*' -and
            $_.Author -notlike '*$(@%systemroot%*'
        }
        $result = @()
        foreach ($task in $manualTasks) {
            $taskInfo = [PSCustomObject]@{
                TaskName = $task.TaskName
                State = $task.State
                NextRunTime = $task.NextRunTime
                LastRunTime = $task.LastRunTime
                LastTaskResult = $task.LastTaskResult
                Description = $task.Description
                TaskPath = $task.TaskPath
                Author = $task.Author
                Trigger = (($task.Triggers | ForEach-Object { $_ | Out-String }) -join '; ')
            }
            $result += $taskInfo
        }
        $result | ConvertTo-Json -Compress -Depth 3
        """
        
        # コマンドを実行
        success, result = self._execute_ps_command(pc_ip, command)
        
        if not success:
            logging.error(f"PowerShell実行失敗: {pc_ip} - {result}")
            return []
            
        if not result or len(result.strip()) == 0:
            logging.warning(f"PowerShell実行結果が空: {pc_ip}")
            return []
            
        if success and result:
            try:
                # 改行文字を除去してからJSON解析
                cleaned_result = result.strip().replace('\r', '').replace('\n', '')
                tasks = json.loads(cleaned_result)
                # 単一のタスクの場合、リストに変換
                if isinstance(tasks, dict):
                    tasks = [tasks]
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
        # このサンプルでは有効/無効の切り替えのみ実装
        if 'State' in update_details:
            state_cmd = "Enable-ScheduledTask" if update_details['State'] == 'Ready' else "Disable-ScheduledTask"
            command = f"{state_cmd} -TaskName '{task_name}'"
            success, message = self._execute_ps_command(pc_ip, command)
            if success:
                self.db_manager.add_audit_log({"user_identifier": user_identifier, "action_type": "UPDATE_TASK_STATE", "target_pc": pc_ip, "target_task": task_name, "details": json.dumps(update_details)})
            return success, message
        return False, "更新ロジックが実装されていません。"


# --- Streamlit アプリケーション設定 ---
st.set_page_config(
    page_title="タスク管理ダッシュボード", 
    page_icon="🤖", 
    layout="wide",
    initial_sidebar_state="expanded"
)

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
    # TODO: 認証情報を安全に取得する
    DUMMY_USER, DUMMY_PASS = "YOUR_USERNAME", "YOUR_PASSWORD"
    st.session_state.task_manager = TaskManager(st.session_state.config_manager, st.session_state.db_manager, DUMMY_USER, DUMMY_PASS)
    st.session_state.current_view = 'pc_info'  # デフォルトをPC情報に変更
    st.session_state.initialized = True
    logging.info("=== アプリケーション初期化完了 ===")

config_manager = st.session_state.config_manager
db_manager = st.session_state.db_manager
task_manager = st.session_state.task_manager

# --- 画面描画関数 ---
@st.dialog("タスク詳細")
def task_detail_dialog(task, pc_name, pc_ip):
    st.subheader(f"タスク: {task['TaskName']}")
    st.caption(f"対象PC: {pc_name}")
    with st.form("edit_task_form"):
        new_description = st.text_area("説明", value=task.get('Description', ''))
        is_enabled = st.toggle("タスクを有効にする", value=(task['State'] == 'Ready'))
        st.write("---")
        col1, col2 = st.columns(2)
        with col1:
            if st.form_submit_button("更新", use_container_width=True):
                # PCの認証情報を取得
                credentials = load_credentials()
                username, password = get_pc_credentials(credentials, pc_name)
                if not username or not password:
                    st.error(f"{pc_name}の認証情報が見つかりません。")
                else:
                    # PCごとにTaskManagerを初期化
                    pc_task_manager = TaskManager(
                        st.session_state.config_manager, 
                        st.session_state.db_manager, 
                        username, 
                        password
                    )
                    update_details = {"State": "Ready" if is_enabled else "Disabled"}
                    success, msg = pc_task_manager.update_task(pc_ip, task['TaskName'], update_details, user_identifier=os.getlogin())
                    if success: st.success(msg); st.rerun()
                    else: st.error(msg)
        with col2:
            if st.form_submit_button("削除", type="primary", use_container_width=True):
                # PCの認証情報を取得
                credentials = load_credentials()
                username, password = get_pc_credentials(credentials, pc_name)
                if not username or not password:
                    st.error(f"{pc_name}の認証情報が見つかりません。")
                else:
                    # PCごとにTaskManagerを初期化
                    pc_task_manager = TaskManager(
                        st.session_state.config_manager, 
                        st.session_state.db_manager, 
                        username, 
                        password
                    )
                    success, msg = pc_task_manager.delete_task(pc_ip, task['TaskName'], user_identifier=os.getlogin())
                    if success: st.success(msg); st.rerun()
                    else: st.error(msg)

@st.dialog("新規タスク作成")
def create_task_dialog():
    st.subheader("新しいタスクの作成")
    with st.form("create_task_form"):
        pc_list = {pc['name']: pc['ip'] for pc in config_manager.get_config().get('pcs', [])}
        if not pc_list:
            st.error("管理対象PCが設定されていません。"); st.stop()
        selected_pc_name = st.selectbox("対象PC", options=list(pc_list.keys()))
        task_name = st.text_input("タスク名 *")
        description = st.text_area("説明")
        st.write("---")
        execution_type = st.selectbox("実行タイプ", ["標準プログラム (.exe, .bat)", "Python スクリプト"])
        if "Python" in execution_type:
            program_path = st.text_input("python.exeのパス", placeholder="C:\\Python311\\python.exe")
            script_path = st.text_input("スクリプトのパス (.py)", placeholder="\\\\nas-server\\scripts\\my_script.py")
        else:
            program_path = st.text_input("プログラム/スクリプトのパス", placeholder="\\\\nas-server\\batch\\my_task.bat")
            script_path = ""
        if st.form_submit_button("作成", type="primary"):
            if not task_name or not program_path:
                st.warning("タスク名とパスは必須です。")
            else:
                # 選択されたPCの認証情報を取得
                credentials = load_credentials()
                username, password = get_pc_credentials(credentials, selected_pc_name)
                if not username or not password:
                    st.error(f"{selected_pc_name}の認証情報が見つかりません。")
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
                        "task_path": target_folder
                    }
                    success, msg = pc_task_manager.create_task(pc_list[selected_pc_name], task_details, user_identifier=os.getlogin())
                    if success: st.success(msg); st.rerun()
                    else: st.error(msg)

def render_dashboard():
    st.header("ダッシュボード")
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        config = config_manager.get_config()
        pc_groups = config.get('pc_groups', [])
        group_options = ["すべてのPC"] + [group['name'] for group in pc_groups]
        selected_group = st.selectbox("PCグループ", group_options)
    with col2:
        # 仕様通りにボタンで切り替え
        st.write("表示フィルタ:")
        col2_1, col2_2 = st.columns(2)
        with col2_1:
            if st.button("すべてのタスク", type="secondary", use_container_width=True):
                st.session_state.display_filter = "すべて"
        with col2_2:
            if st.button("アクティブなタスクのみ", type="primary", use_container_width=True):
                st.session_state.display_filter = "アクティブのみ"
        
        # 並べ替え機能を追加
        if 'sort_order' not in st.session_state:
            st.session_state.sort_order = "次回実行日時順"
        sort_order = st.selectbox("並べ替え順序", ["次回実行日時順", "作成日時順", "タスク名順"])
        st.session_state.sort_order = sort_order
    with col3:
        st.write(""); st.write("")
        if st.button("＋ 新規タスクを作成", type="primary", use_container_width=True):
            create_task_dialog()
    
    # 表示フィルターの初期化
    if 'display_filter' not in st.session_state:
        st.session_state.display_filter = "すべて"
    
    # 選択されたグループの説明を表示
    if selected_group != "すべてのPC":
        selected_group_info = next((group for group in pc_groups if group['name'] == selected_group), None)
        if selected_group_info:
            st.info(f"**{selected_group_info['name']}**: {selected_group_info['description']}")
    
    st.subheader(f"タスク一覧 ({selected_group} - 手動作成タスク)")
    
    all_pcs = config.get('pcs', [])
    pcs_to_scan = [pc for pc in all_pcs if selected_group == "すべてのPC" or pc.get('group') == selected_group]
    if not pcs_to_scan: 
        st.warning("表示対象のPCがありません。「管理者設定」画面からPCを追加・設定してください。")
        return

    all_tasks = []
    progress_bar = st.progress(0, text="タスク情報を取得中...")
    
    # 認証情報の読み込み
    credentials = load_credentials()
    
    for i, pc in enumerate(pcs_to_scan):
        progress_bar.progress((i + 1) / len(pcs_to_scan), text=f"{pc['name']}...")
        
        # PCごとの認証情報を取得
        username, password = get_pc_credentials(credentials, pc['name'])
        if not username or not password:
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
        tasks = pc_task_manager.get_tasks_from_pc(pc['ip'])
        
        for task in tasks:
            task['PC名'] = pc['name']
            task['PC_IP'] = pc['ip']
            all_tasks.append(task)
    progress_bar.empty()

    if not all_tasks:
        st.info("対象のタスクは見つかりませんでした。")
        return

    df = pd.DataFrame(all_tasks)
    
    # フィルタリング処理（仕様通りに修正）
    if st.session_state.display_filter == "アクティブのみ":
        # Stateが1（Ready）または3（Running）のタスクのみを表示
        df = df[df['State'].isin([1, 3])]
    
    if df.empty:
        st.info("フィルタ条件に一致するタスクは見つかりませんでした。")
        return
    
    # 並べ替え処理
    if st.session_state.sort_order == "次回実行日時順":
        df = df.sort_values('NextRunTime', na_position='last')
    elif st.session_state.sort_order == "作成日時順":
        df = df.sort_values('LastRunTime', na_position='last')
    elif st.session_state.sort_order == "タスク名順":
        df = df.sort_values('TaskName')
    
    # 利用可能な列を確認して表示列を選択
    available_columns = df.columns.tolist()
    
    # 基本列（必ず存在するはず）
    base_columns = ['PC名', 'TaskName', 'State', 'NextRunTime']
    
    # オプション列（存在する場合のみ追加）
    optional_columns = []
    if 'Author' in available_columns:
        optional_columns.append('Author')
    
    display_columns = base_columns + optional_columns
    
    # 列名のマッピング（存在する列のみ）
    column_mapping = {
        'TaskName': 'タスク名', 
        'State': '状態', 
        'NextRunTime': '次回実行日時'
    }
    
    if 'Author' in display_columns:
        column_mapping['Author'] = '作成者'
    
    # 存在する列のみでデータフレームを作成
    existing_columns = [col for col in display_columns if col in df.columns]
    display_df = df[existing_columns].rename(columns=column_mapping)
    
    # エラーハイライト機能（将来の実装）
    # 現在は通常のデータフレーム表示
    st.dataframe(display_df, use_container_width=True, hide_index=True, column_config={
        "次回実行日時": st.column_config.DatetimeColumn("次回実行日時", format="YYYY/MM/DD HH:mm")
    })
    
    # 詳細ボタンのロジック
    # st.dataframeは直接ボタンを埋め込めないため、別の方法で実装
    st.write("---")
    st.write("タスク詳細の表示・編集:")
    selected_task_name = st.selectbox("タスクを選択", options=df['TaskName'].unique())
    selected_task_data = df[df['TaskName'] == selected_task_name].iloc[0].to_dict()
    if st.button(f"「{selected_task_name}」の詳細を開く"):
        task_detail_dialog(selected_task_data, selected_task_data['PC名'], selected_task_data['PC_IP'])

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
    config_data = config_manager.get_config()
    with st.form("admin_settings_form"):
        st.subheader("管理対象PC設定")
        edited_pcs = st.data_editor(pd.DataFrame(config_data.get('pcs', [])), num_rows="dynamic", use_container_width=True)
        
        st.subheader("PCグループ設定")
        edited_pc_groups = st.data_editor(pd.DataFrame(config_data.get('pc_groups', [])), num_rows="dynamic", use_container_width=True)
        

        
        st.subheader("通知設定")
        notification_enabled = st.checkbox("Google Chat通知を有効にする", value=config_data['notification']['enabled'])
        webhook_url = st.text_input("Webhook URL", value=config_data['notification']['google_chat_webhook_url'])
        submitted = st.form_submit_button("設定を保存")
        if submitted:
            config_data['pcs'] = edited_pcs.to_dict('records')
            config_data['pc_groups'] = edited_pc_groups.to_dict('records')
            config_data['notification']['enabled'] = notification_enabled
            config_data['notification']['google_chat_webhook_url'] = webhook_url
            config_manager.update_config(config_data)
            st.success("設定を保存しました。")

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
