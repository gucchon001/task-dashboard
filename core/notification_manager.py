import json
import logging
import requests
from datetime import datetime

class NotificationManager:
    """Google Chatへの通知送信を管理するクラス。"""
    def __init__(self, config_manager):
        """
        コンストラクタ。
        :param config_manager: 設定管理オブジェクト。
        """
        self.config_manager = config_manager

    def _build_payload(self, error_details):
        """
        外部インターフェース設計書に基づき、JSONペイロードを生成する。
        """
        ai_analysis_text = error_details.get('ai_analysis', 'AIによる分析は実行されませんでした。')
        payload = {
          "cardsV2": [
            {
              "cardId": "task-error-notification",
              "card": {
                "header": {
                  "title": "🔴 タスク実行エラー通知",
                  "subtitle": "タスクの実行に失敗しました。詳細を確認してください。",
                  "imageUrl": "https://img.icons8.com/color/48/error--v1.png",
                  "imageType": "CIRCLE"
                },
                "sections": [
                  {
                    "header": "エラー概要",
                    "widgets": [
                      {"decoratedText": {"startIcon": {"knownIcon": "COMPUTER"}, "text": f"<b>PC名:</b> {error_details.get('pc_name', 'N/A')}"}},
                      {"decoratedText": {"startIcon": {"knownIcon": "INVITE"}, "text": f"<b>タスク名:</b> {error_details.get('task_name', 'N/A')}"}},
                      {"decoratedText": {"startIcon": {"knownIcon": "CLOCK"}, "text": f"<b>検知日時:</b> {datetime.now().strftime('%Y/%m/%d %H:%M:%S')}"}},
                      {"decoratedText": {"startIcon": {"knownIcon": "TICKET"}, "text": f"<b>エラーコード:</b> {error_details.get('result_code', 'N/A')}"}}
                    ]
                  },
                  {
                    "header": "AIによる分析結果 (要約)",
                    "collapsible": True,
                    "widgets": [
                      {"textParagraph": {"text": ai_analysis_text.replace('\n', '<br>')}}
                    ]
                  }
                ]
              }
            }
          ]
        }
        return payload

    def send_error_notification(self, error_details):
        """
        タスク実行エラーの情報をGoogle Chatに送信する。
        :param error_details: pc_name, task_nameなどを含む辞書。
        :return: (bool, str) 成功/失敗の真偽値と結果メッセージ。
        """
        config = self.config_manager.get_config()
        notification_settings = config.get('notification', {})
        if not notification_settings.get('enabled'):
            return False, "通知機能が無効です。"
        webhook_url = notification_settings.get('google_chat_webhook_url')
        if not webhook_url:
            return False, "Webhook URLが設定されていません。"
        payload = self._build_payload(error_details)
        try:
            response = requests.post(
                webhook_url,
                headers={'Content-Type': 'application/json; charset=UTF-8'},
                data=json.dumps(payload),
                timeout=10
            )
            response.raise_for_status()
            logging.info("Google Chatへの通知に成功しました。")
            return True, "通知を送信しました。"
        except requests.exceptions.RequestException as e:
            logging.error(f"Google Chatへの通知に失敗しました: {e}")
            return False, f"通知の送信に失敗しました: {e}"
