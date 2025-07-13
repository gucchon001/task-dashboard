import json
import logging
import winrm

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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