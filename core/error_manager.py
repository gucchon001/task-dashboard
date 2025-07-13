import json
import os
import logging

class ErrorManager:
    """エラーコードとメッセージを管理するクラス"""
    
    def __init__(self, error_codes_path='data/error_codes.json'):
        self.error_codes_path = error_codes_path
        self.error_codes = {}
        self.timeout_error_codes = []
        self.timeout_solutions = {}
        self.load_error_codes()
    
    def load_error_codes(self):
        """エラーコード設定ファイルを読み込む"""
        try:
            if os.path.exists(self.error_codes_path):
                with open(self.error_codes_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                # エラーコード辞書を統合
                self.error_codes = {}
                if 'error_codes' in data:
                    for category, codes in data['error_codes'].items():
                        for code, message in codes.items():
                            # 16進数コードを10進数に変換
                            if code.startswith('0x'):
                                try:
                                    decimal_code = int(code, 16)
                                    self.error_codes[decimal_code] = message
                                except ValueError:
                                    logging.warning(f"無効な16進数コード: {code}")
                            else:
                                try:
                                    decimal_code = int(code)
                                    self.error_codes[decimal_code] = message
                                except ValueError:
                                    logging.warning(f"無効なエラーコード: {code}")
                
                # タイムアウトエラーコードを設定
                if 'timeout_error_codes' in data:
                    self.timeout_error_codes = []
                    for code in data['timeout_error_codes']:
                        if code.startswith('0x'):
                            try:
                                decimal_code = int(code, 16)
                                self.timeout_error_codes.append(decimal_code)
                            except ValueError:
                                logging.warning(f"無効なタイムアウトエラーコード: {code}")
                        else:
                            try:
                                decimal_code = int(code)
                                self.timeout_error_codes.append(decimal_code)
                            except ValueError:
                                logging.warning(f"無効なタイムアウトエラーコード: {code}")
                
                # タイムアウト対処法を設定
                if 'timeout_solutions' in data:
                    self.timeout_solutions = data['timeout_solutions']
                
                logging.info(f"エラーコード設定を読み込みました: {len(self.error_codes)}件")
            else:
                logging.warning(f"エラーコード設定ファイルが見つかりません: {self.error_codes_path}")
                self._create_default_error_codes()
        except Exception as e:
            logging.error(f"エラーコード設定の読み込みに失敗しました: {e}")
            self._create_default_error_codes()
    
    def _create_default_error_codes(self):
        """デフォルトのエラーコードを設定"""
        self.error_codes = {
            1: '一般エラー',
            2: '無効なパラメータ',
            3: 'ファイルが見つかりません',
            4: 'アクセス拒否',
            5: 'タイムアウト',
            6: 'メモリ不足',
            7: 'ネットワークエラー',
            8: '権限不足',
            9: 'システムエラー',
            10: 'サービスエラー',
            124: 'タイムアウトエラー',
            258: 'タイムアウトエラー',
            1460: 'タイムアウトエラー',
            1461: 'タイムアウトエラー',
            267009: '権限不足またはファイルアクセスエラー',
            2519049: '権限不足またはファイルアクセスエラー',
            0x00041306: 'タスクがタイムアウトにより停止されました',
            0x00041324: 'タスク実行が制約により失敗しました',
            0x00041325: 'タスクが実行キューに入っています',
            0x00041326: 'タスクが無効になっています'
        }
        
        self.timeout_error_codes = [
            0x00041306,
            0x00041324,
            124,
            258,
            1460,
            1461
        ]
        
        self.timeout_solutions = {
            "title": "タイムアウトエラーの対処法",
            "steps": [
                {
                    "title": "タスクの実行時間制限を延長する",
                    "description": "タスクスケジューラでタスクのプロパティを開き、「設定」タブで「タスクを停止する時間」を延長します"
                },
                {
                    "title": "外部要因の調査",
                    "description": "ネットワーク接続の確認、対象ファイルやサーバーの応答時間確認、システムリソース（CPU、メモリ）の使用状況確認を行います"
                },
                {
                    "title": "タスクの最適化",
                    "description": "処理内容の見直し、バッチサイズの調整、並列処理の検討を行います"
                },
                {
                    "title": "ログの確認",
                    "description": "イベントビューアで詳細なエラー情報を確認し、アプリケーションログを確認します"
                }
            ]
        }
    
    def get_error_message(self, error_code):
        """エラーコードに対応するメッセージを返す"""
        # 浮動小数点の場合は整数部分を取得
        if isinstance(error_code, float):
            error_code_int = int(error_code)
        else:
            error_code_int = error_code
        
        return self.error_codes.get(error_code_int, f'エラー({error_code})')
    
    def is_timeout_error(self, error_code):
        """エラーコードがタイムアウトエラーかどうかを判定"""
        # 浮動小数点の場合は整数部分を取得
        if isinstance(error_code, float):
            error_code_int = int(error_code)
        else:
            error_code_int = error_code
        
        return error_code_int in self.timeout_error_codes
    
    def get_timeout_solutions(self):
        """タイムアウトエラーの対処法を返す"""
        return self.timeout_solutions
    
    def reload_error_codes(self):
        """エラーコード設定を再読み込み"""
        self.load_error_codes()
    
    def add_error_code(self, code, message):
        """新しいエラーコードを追加"""
        if isinstance(code, str) and code.startswith('0x'):
            try:
                decimal_code = int(code, 16)
                self.error_codes[decimal_code] = message
            except ValueError:
                logging.error(f"無効な16進数コード: {code}")
        else:
            try:
                decimal_code = int(code)
                self.error_codes[decimal_code] = message
            except ValueError:
                logging.error(f"無効なエラーコード: {code}")
    
    def save_error_codes(self):
        """エラーコード設定をファイルに保存"""
        try:
            # 現在の設定をファイル形式に変換
            data = {
                "error_codes": {
                    "general": {},
                    "task_scheduler": {}
                },
                "timeout_error_codes": [],
                "timeout_solutions": self.timeout_solutions
            }
            
            # エラーコードを分類して保存
            for code, message in self.error_codes.items():
                if code >= 0x80041300:  # タスクスケジューラエラー
                    data["error_codes"]["task_scheduler"][f"0x{code:08X}"] = message
                else:  # 一般エラー
                    data["error_codes"]["general"][str(code)] = message
            
            # タイムアウトエラーコードを保存
            for code in self.timeout_error_codes:
                if code >= 0x80041300:
                    data["timeout_error_codes"].append(f"0x{code:08X}")
                else:
                    data["timeout_error_codes"].append(str(code))
            
            # ファイルに保存
            os.makedirs(os.path.dirname(self.error_codes_path), exist_ok=True)
            with open(self.error_codes_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logging.info("エラーコード設定を保存しました")
        except Exception as e:
            logging.error(f"エラーコード設定の保存に失敗しました: {e}") 