import json

config = {
  "pcs": [
    {
      "name": "EPS50",
      "ip": "192.168.1.57",
      "group": "勤怠用"
    },
    {
      "name": "WIN-ND0QPM2D7G1",
      "ip": "192.168.1.58",
      "group": "統合用"
    }
  ],
  "pc_groups": [
    {
      "name": "勤怠用",
      "description": "勤怠システム用のPC群"
    },
    {
      "name": "統合用",
      "description": "統合システム用のPC群"
    }
  ],
  "task_folders": ["\\"],
  "notification": {
    "enabled": False,
    "google_chat_webhook_url": ""
  },
  "admin": {
    "password_hash": ""
  },
  "api_keys": {
    "gemini": ""
  }
}

with open('data/config.json', 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=2, ensure_ascii=False)

print("設定ファイルを復元しました") 