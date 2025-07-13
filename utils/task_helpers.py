# ==============================================================================
# タスク関連のヘルパー関数
# ==============================================================================

import pandas as pd
import datetime

def get_task_result_info(task):
    """タスクの実行結果に応じた情報を返す"""
    last_task_result = task.get('LastTaskResult')
    
    # LastTaskResultがNone、NaN、または未設定の場合
    if last_task_result is None or pd.isna(last_task_result):
        return {
            'status': '未実行',
            'icon': '⏸️'
        }
    
    # 数値に変換できるかチェック
    try:
        last_task_result_int = int(last_task_result)
    except (ValueError, TypeError):
        return {
            'status': '未実行',
            'icon': '⏸️'
        }
    
    # 成功の場合（0）
    if last_task_result_int == 0:
        return {
            'status': '成功',
            'icon': '✅'
        }
    
    # エラーの場合（0以外）
    try:
        from core.error_manager import ErrorManager
        error_manager = ErrorManager('data/error_codes.json')
        error_message = error_manager.get_error_message(last_task_result_int)
        
        # 実行中の場合は特別な処理
        if "実行中" in error_message or "running" in error_message.lower():
            return {
                'status': '実行中',
                'icon': '🔄'
            }
        
        return {
            'status': error_message,
            'icon': '❌'
        }
    except Exception as e:
        # エラーメッセージの取得に失敗した場合
        return {
            'status': f'エラー (コード: {last_task_result_int})',
            'icon': '❌'
        }

def get_task_state_info(state):
    """タスクの状態に応じた情報を返す"""
    # PowerShell Get-ScheduledTaskのState値の正しい対応表
    # 0: TASK_STATE_UNKNOWN - 状態が不明
    # 1: TASK_STATE_DISABLED - タスクは無効
    # 2: TASK_STATE_QUEUED - タスクは実行キューに入っている
    # 3: TASK_STATE_READY - タスクは実行準備完了
    # 4: TASK_STATE_RUNNING - タスクは実行中
    if state == 0:
        return {
            'status': '不明',
            'icon': '❓',
            'style': 'background-color: #9e9e9e; color: white;'
        }
    elif state == 1:
        return {
            'status': '無効',
            'icon': '🔴',
            'style': 'background-color: #f44336; color: white;'
        }
    elif state == 2:
        return {
            'status': '待機中',
            'icon': '🟡',
            'style': 'background-color: #ff9800; color: white;'
        }
    elif state == 3:
        return {
            'status': '準備完了',
            'icon': '🟢',
            'style': 'background-color: #4caf50; color: white;'
        }
    elif state == 4:
        return {
            'status': '実行中',
            'icon': '🟡',
            'style': 'background-color: #ff9800; color: white;'
        }
    else:
        return {
            'status': '不明',
            'icon': '❓',
            'style': 'background-color: #9e9e9e; color: white;'
        }

def format_datetime(dt_value):
    """日時をフォーマットする"""
    if pd.isna(dt_value) or dt_value is None:
        return "未設定"
    try:
        if isinstance(dt_value, str):
            return dt_value
        return dt_value.strftime("%Y/%m/%d %H:%M")
    except:
        return str(dt_value)

def format_trigger_info(trigger_str):
    """トリガー情報をフォーマットする"""
    if not trigger_str or trigger_str == 'null':
        return "未設定"
    
    try:
        # トリガー文字列から主要な情報を抽出
        lines = trigger_str.split('\n')
        
        # 設定時間と繰り返し間隔を抽出
        start_time = None
        days_interval = None
        hours_interval = None
        minutes_interval = None
        
        for line in lines:
            line = line.strip()
            if 'StartBoundary' in line and ':' in line:
                # StartBoundary: 2024-03-09T06:00:00 形式を処理
                start_time = line.split(':', 1)[1].strip()
            elif 'DaysInterval' in line and ':' in line:
                days_interval = line.split(':', 1)[1].strip()
            elif 'HoursInterval' in line and ':' in line:
                hours_interval = line.split(':', 1)[1].strip()
            elif 'MinutesInterval' in line and ':' in line:
                minutes_interval = line.split(':', 1)[1].strip()
        
        # 設定時刻のフォーマット
        time_str = "未設定"
        if start_time:
            try:
                # ISO形式の日時を読みやすい形式に変換
                if 'T' in start_time:
                    # 2024-03-09T06:00:00 形式を処理
                    date_part, time_part = start_time.split('T')
                    time_only = time_part.split(':')[:2]  # 時:分のみ取得
                    time_str = f"{time_only[0]}:{time_only[1]}"
                else:
                    time_str = start_time
            except:
                time_str = start_time
        
        # 頻度のフォーマット（繰り返し表示を削除）
        frequency_str = "未設定"
        interval_parts = []
        if days_interval and days_interval != '0':
            interval_parts.append(f"{days_interval}日")
        if hours_interval and hours_interval != '0':
            interval_parts.append(f"{hours_interval}時間")
        if minutes_interval and minutes_interval != '0':
            interval_parts.append(f"{minutes_interval}分")
        
        if interval_parts:
            frequency_str = " | ".join(interval_parts)
        
        # 頻度が「未設定」の場合は時刻のみを返す
        if frequency_str == "未設定":
            return time_str
        else:
            return f"{time_str} | {frequency_str}"
    except:
        return "トリガーあり" 