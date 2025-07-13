import json
import os

class ConfigManager:
    """
    設定ファイル(config.json)の読み書きを管理するクラス。
    """
    def __init__(self, path='config.json'):
        """
        コンストラクタ。設定ファイルのパスを受け取り、初期化する。
        :param path: config.jsonへのファイルパス。
        """
        self.config_path = path
        self.config_data = {}
        self.load_config()

    def load_config(self):
        """
        設定ファイルをディスクから読み込む。
        ファイルが存在しない場合は、空のテンプレートで作成する。
        """
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config_data = json.load(f)
        else:
            # デフォルトのテンプレートを作成
            self.config_data = {
                "pcs": [],
                "pc_groups": [],
                "task_folders": ["\\"],
                "notification": {
                    "enabled": False,
                    "google_chat_webhook_url": ""
                },
                "admin": {
                    "password_hash": "" # パスワードはハッシュ化して保存
                },
                "api_keys": {
                    "gemini": "" # Gemini APIキー
                }
            }
            self.save_config()

    def save_config(self):
        """
        現在の設定内容を設定ファイルに書き込む（上書き保存）。
        """
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self.config_data, f, indent=2, ensure_ascii=False)

    def get_config(self):
        """
        全ての設定データを取得する。
        """
        return self.config_data

    def update_config(self, new_config_data):
        """
        設定データ全体を更新し、ファイルに保存する。
        """
        self.config_data = new_config_data
        self.save_config()
