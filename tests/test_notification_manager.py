import os
import sys

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config_manager import ConfigManager
from core.notification_manager import NotificationManager

if __name__ == '__main__':
    # テスト用の設定マネージャーを準備
    test_config_path = 'test_config.json'
    if os.path.exists(test_config_path):
        os.remove(test_config_path)

    config_mgr = ConfigManager(test_config_path)
    
    # 通知設定を有効化し、ダミーのWebhook URLを設定
    # 【注意】実際にテストする際は、ご自身のWebhook URLに書き換えてください
    config_data = config_mgr.get_config()
    config_data['notification']['enabled'] = True
    config_data['notification']['google_chat_webhook_url'] = "YOUR_WEBHOOK_URL_HERE" # ここを書き換える
    config_mgr.update_config(config_data)

    # NotificationManagerを初期化
    notifier = NotificationManager(config_mgr)
    
    # テスト用のエラー詳細データ
    test_error = {
        "pc_name": "PC-PROD-99",
        "task_name": "CriticalBatch",
        "result_code": 500,
        "ai_analysis": "<b>原因:</b> サーバーが応答しませんでした。\n<b>対策:</b> ネットワーク接続を確認してください。"
    }
    
    # 通知を送信
    print("\n--- NotificationManager Test ---")
    print("Sending a test notification to Google Chat...")
    # 実際に通知を飛ばしたくない場合は、以下の行をコメントアウトしてください
    # success, message = notifier.send_error_notification(test_error)
    # print(f"Result: {success} - {message}")

    # テスト後にファイルをクリーンアップ
    if os.path.exists(test_config_path):
        os.remove(test_config_path) 