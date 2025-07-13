import json
import logging
import requests
from datetime import datetime

class AIAnalyzer:
    """Gemini APIと連携し、エラーログの分析を行うクラス。"""
    def __init__(self, config_manager):
        """
        コンストラクタ。
        :param config_manager: 設定管理オブジェクト。
        """
        self.config_manager = config_manager
        self.api_key = self.config_manager.get_config().get('api_keys', {}).get('gemini')
        self.api_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

    def _build_prompt(self, error_log):
        """
        外部インターフェース設計書に基づき、プロンプトを生成する。
        """
        prompt = f"""
あなたはITシステムの運用保守の専門家です。
以下のWindowsタスクスケジューラのエラーログを分析し、「考えられる原因」と「具体的な対処法の候補」を、それぞれ箇条書きで初心者にも分かりやすいように日本語でまとめてください。

--- エラーログ ---
PC名: {error_log.get('pc_name', 'N/A')}
タスク名: {error_log.get('task_name', 'N/A')}
エラーコード: {error_log.get('result_code', 'N/A')}
メッセージ: {error_log.get('result_message', 'N/A')}
---

分析結果:
"""
        return prompt

    def analyze_error_log(self, error_log):
        """
        タスクのエラーログを分析し、原因と対策のテキストを生成する。
        :param error_log: pc_name, task_nameなどを含む辞書。
        :return: AIが生成した分析結果テキスト。
        """
        if not self.api_key:
            return "AI分析失敗: Gemini APIキーが設定されていません。"

        prompt = self._build_prompt(error_log)
        
        payload = {
          "contents": [{"parts": [{"text": prompt}]}],
          "generationConfig": {"temperature": 0.3, "maxOutputTokens": 1024}
        }
        
        headers = {'Content-Type': 'application/json'}
        
        try:
            response = requests.post(
                f"{self.api_url}?key={self.api_key}",
                headers=headers,
                data=json.dumps(payload),
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            # レスポンスの構造を安全にチェック
            if (result.get('candidates') and 
                result['candidates'][0].get('content') and
                result['candidates'][0]['content'].get('parts') and
                result['candidates'][0]['content']['parts'][0].get('text')):
                
                analysis_text = result['candidates'][0]['content']['parts'][0]['text']
                logging.info("Gemini APIによるエラー分析に成功しました。")
                return analysis_text.strip()
            else:
                logging.error(f"Gemini APIからのレスポンス形式が不正です: {result}")
                return "AI分析失敗: APIから予期しない形式の応答がありました。"

        except requests.exceptions.RequestException as e:
            logging.error(f"Gemini APIへのリクエストに失敗しました: {e}")
            return f"AI分析失敗: APIへの接続中にエラーが発生しました ({e})。"
