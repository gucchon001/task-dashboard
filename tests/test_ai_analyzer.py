import os
import sys

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config_manager import ConfigManager
from core.ai_analyzer import AIAnalyzer

if __name__ == '__main__':
    # テスト用の設定マネージャーを準備
    test_config_path = 'test_config.json'
    if os.path.exists(test_config_path):
        os.remove(test_config_path)

    config_mgr = ConfigManager(test_config_path)
    
    # 【注意】実際にテストする際は、ご自身のAPIキーに書き換えてください
    config_data = config_mgr.get_config()
    config_data['api_keys']['gemini'] = "YOUR_GEMINI_API_KEY_HERE" # ここを書き換える
    config_mgr.update_config(config_data)

    # AIAnalyzerを初期化
    analyzer = AIAnalyzer(config_mgr)
    
    # テスト用のエラーログデータ
    test_error_log = {
        "pc_name": "PC-DB-01",
        "task_name": "ExportUserData",
        "result_code": 1,
        "result_message": "The system cannot find the file specified. (0x80070002)"
    }
    
    # エラーを分析
    print("\n--- AIAnalyzer Test ---")
    print("Analyzing an error log with Gemini API...")
    # 実際にAPIを呼び出したくない場合は、以下の行をコメントアウトしてください
    # analysis_result = analyzer.analyze_error_log(test_error_log)
    # print("\n--- Analysis Result ---")
    # print(analysis_result)

    # テスト後にファイルをクリーンアップ
    if os.path.exists(test_config_path):
        os.remove(test_config_path) 