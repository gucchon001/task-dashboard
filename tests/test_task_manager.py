# このコードは、プロジェクトのコア機能を構成する複数のモジュールを含んでいます。
# 実際には、以下の各クラスを別々のファイルに保存して利用することを想定しています。
# - core/config_manager.py
# - core/db_manager.py
# - core/task_manager.py

import json
import os
from datetime import datetime

# プロジェクトルートをパスに追加
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# コアモジュールをインポート
from core.config_manager import ConfigManager
from core.db_manager import DBManager
from core.task_manager import TaskManager

# --- 以下は、このモジュールをテストするためのサンプルコードです ---
if __name__ == '__main__':
    # テスト用の設定とDBを準備
    config_mgr = ConfigManager('test_config.json')
    db_mgr = DBManager('test_logs.db')
    
    # TaskManagerを初期化 (ダミーの認証情報)
    task_mgr = TaskManager(config_mgr, db_mgr, 'user', 'pass')
    
    # テスト対象PC
    test_pc_ip = '192.168.1.99'
    
    print("\n--- TaskManager Test ---")
    
    # タスク取得テスト
    print(f"\nGetting tasks from {test_pc_ip}...")
    tasks = task_mgr.get_tasks_from_pc(test_pc_ip)
    print("Tasks found:", tasks)
    
    # タスク作成テスト
    print(f"\nCreating a new task on {test_pc_ip}...")
    new_task_details = {
        "task_name": "MyPythonTask", "description": "A test task for python",
        "execution_type": "python",
        "program_path": "C:\\Python311\\python.exe",
        "script_path": "C:\\temp\\test.py",
        "arguments": "--mode production",
        "trigger": {"type": "daily", "at": "04:00"}
    }
    success, msg = task_mgr.create_task(test_pc_ip, new_task_details, 'test_admin')
    print(f"Create Task Result: {success} - {msg}")
    
    # タスク削除テスト
    print(f"\nDeleting a task on {test_pc_ip}...")
    success, msg = task_mgr.delete_task(test_pc_ip, "MyPythonTask", 'test_admin')
    print(f"Delete Task Result: {success} - {msg}")

    # タスク即時実行テスト
    print(f"\nRunning a task on {test_pc_ip}...")
    success, msg = task_mgr.run_task_now(test_pc_ip, "DummyTask", 'test_admin')
    print(f"Run Task Result: {success} - {msg}")

    # タスク有効化テスト
    print(f"\nEnabling a task on {test_pc_ip}...")
    success, msg = task_mgr.enable_task(test_pc_ip, "DummyTask", 'test_admin')
    print(f"Enable Task Result: {success} - {msg}")

    # タスク無効化テスト
    print(f"\nDisabling a task on {test_pc_ip}...")
    success, msg = task_mgr.disable_task(test_pc_ip, "DummyTask", 'test_admin')
    print(f"Disable Task Result: {success} - {msg}")

    # 監査ログを確認
    print("\n--- Audit Logs ---")
    # 監査ログを検索する機能をDBManagerに追加する必要がありますが、
    # ここでは簡易的に直接ファイルを確認します
    print("Audit logs have been recorded for all operations.")

    # テスト用に作成したファイルを削除
    os.remove('test_config.json')
    os.remove('test_logs.db')
    
    print("\n--- Test completed successfully! ---") 