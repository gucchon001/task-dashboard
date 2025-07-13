# このコードは、プロジェクトのコア機能を構成する複数のモジュールを含んでいます。
# 実際には、以下の各クラスを別々のファイルに保存して利用することを想定しています。
# - core/config_manager.py
# - core/db_manager.py

import json
import os
from datetime import datetime

# プロジェクトルートをパスに追加
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# コアモジュールをインポート
from core.config_manager import ConfigManager
from core.db_manager import DBManager

# --- 以下は、このモジュールをテストするためのサンプルコードです ---
if __name__ == '__main__':
    print("--- ConfigManager Test ---")
    # 設定マネージャーを初期化（config.jsonがなければ作成される）
    config_manager = ConfigManager('test_config.json')
    
    # 設定を取得して表示
    current_config = config_manager.get_config()
    print("Initial Config:", current_config)
    
    # 設定を更新
    current_config['pcs'].append({"name": "TEST-PC", "ip_address": "127.0.0.1", "group": "テスト用"})
    config_manager.update_config(current_config)
    
    # 更新後の設定を再読み込みして表示
    config_manager.load_config()
    print("Updated Config:", config_manager.get_config())
    
    print("\n--- DBManager Test ---")
    # DBマネージャーを初期化（logs.dbがなければ作成される）
    db_manager = DBManager('test_logs.db')

    # 実行ログを追加
    log_id = db_manager.add_execution_log({
        "pc_name": "TEST-PC",
        "task_path": "\\",
        "task_name": "TestTask",
        "result_code": 0,
        "result_message": "処理が正常に完了しました。"
    })
    print(f"Added execution log with ID: {log_id}")
    
    # エラーログを追加
    error_log_id = db_manager.add_execution_log({
        "pc_name": "ERROR-PC",
        "task_path": "\\",
        "task_name": "ErrorTask",
        "result_code": 1,
        "result_message": "ファイルが見つかりません。"
    })
    print(f"Added error log with ID: {error_log_id}")

    # AI分析結果を更新
    db_manager.update_ai_analysis(error_log_id, "原因: 指定されたパスにファイルが存在しない可能性があります。")
    print(f"Updated AI analysis for log ID: {error_log_id}")

    # 監査ログを追加
    db_manager.add_audit_log({
        "user_identifier": "test_user",
        "action_type": "CREATE_TASK",
        "target_pc": "TEST-PC",
        "target_task": "TestTask",
        "details": json.dumps({"trigger": "daily 03:00"})
    })
    print("Added audit log.")

    # ログを検索して表示
    all_logs = db_manager.search_execution_logs()
    print("\nAll Logs:")
    for log in all_logs:
        print(log)

    # テスト用に作成したファイルを削除
    os.remove('test_config.json')
    os.remove('test_logs.db')
    
    print("\n--- Test completed successfully! ---") 