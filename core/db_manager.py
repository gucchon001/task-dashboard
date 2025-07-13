import sqlite3
import json
from datetime import datetime

class DBManager:
    """
    ログデータベース(logs.db)への接続と操作を管理するクラス。
    """
    def __init__(self, path='logs.db'):
        """
        コンストラクタ。データベースファイルのパスを受け取る。
        :param path: logs.dbへのファイルパス。
        """
        self.db_path = path
        self.conn = None
        self._create_tables_if_not_exists()

    def _get_connection(self):
        """データベースへの接続を確立する。"""
        return sqlite3.connect(self.db_path)

    def _create_tables_if_not_exists(self):
        """
        データベース起動時にテーブルが存在しない場合、作成する。
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # 実行結果ログテーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS execution_logs (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                recorded_at TEXT NOT NULL,
                pc_name TEXT NOT NULL,
                task_path TEXT NOT NULL,
                task_name TEXT NOT NULL,
                result_code INTEGER,
                result_message TEXT,
                ai_analysis TEXT
            )
        ''')

        # 操作監査ログテーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS audit_logs (
                audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                user_identifier TEXT NOT NULL,
                action_type TEXT NOT NULL,
                target_pc TEXT,
                target_task TEXT,
                details TEXT
            )
        ''')
        conn.commit()
        conn.close()

    def add_execution_log(self, log_data):
        """
        実行結果ログを1件追加する。
        :param log_data: pc_name, task_nameなどを含む辞書。
        :return: 追加されたログのID。
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # 現在時刻をISO 8601形式で追加
        log_data['recorded_at'] = datetime.now().isoformat()

        keys = ', '.join(log_data.keys())
        placeholders = ', '.join(['?'] * len(log_data))
        
        cursor.execute(f"INSERT INTO execution_logs ({keys}) VALUES ({placeholders})", list(log_data.values()))
        
        last_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return last_id
        
    def update_ai_analysis(self, log_id, analysis_text):
        """
        指定されたログにAI分析結果を追記する。
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE execution_logs SET ai_analysis = ? WHERE log_id = ?", (analysis_text, log_id))
        conn.commit()
        conn.close()

    def search_execution_logs(self, **kwargs):
        """
        指定された条件で実行結果ログを検索する。
        :param kwargs: pc_name, task_name, start_date, end_dateなどの検索条件。
        :return: 検索結果のリスト。
        """
        conn = self._get_connection()
        # 結果を辞書形式で受け取れるようにする
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        query = "SELECT * FROM execution_logs WHERE 1=1"
        params = []

        if kwargs.get('pc_name'):
            query += " AND pc_name LIKE ?"
            params.append(f"%{kwargs['pc_name']}%")
        if kwargs.get('task_name'):
            query += " AND task_name LIKE ?"
            params.append(f"%{kwargs['task_name']}%")
        if kwargs.get('start_date'):
            query += " AND recorded_at >= ?"
            params.append(kwargs['start_date'])
        if kwargs.get('end_date'):
            query += " AND recorded_at <= ?"
            params.append(kwargs['end_date'])
        
        query += " ORDER BY recorded_at DESC" # 新しい順に並べる

        cursor.execute(query, params)
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return rows

    def add_audit_log(self, audit_data):
        """
        操作監査ログを1件追加する。
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        audit_data['timestamp'] = datetime.now().isoformat()
        
        keys = ', '.join(audit_data.keys())
        placeholders = ', '.join(['?'] * len(audit_data))

        cursor.execute(f"INSERT INTO audit_logs ({keys}) VALUES ({placeholders})", list(audit_data.values()))
        conn.commit()
        conn.close()
