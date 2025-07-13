# ==============================================================================
# Streamlitアプリケーション本体 (app.py)
# ==============================================================================
# このファイルを実行することで、タスク管理ダッシュボードが起動します。
# 分割されたモジュールを使用して、より保守性の高い構造になっています。
#
# 起動コマンド:
# streamlit run app.py
# ==============================================================================

import streamlit as st
import pandas as pd
import os
import json
import plotly.express as px
import winrm
import datetime

# --- バックエンドモジュールのインポート ---
from core.config_manager import ConfigManager
from core.db_manager import DBManager
from core.task_manager import TaskManager
from core.notification_manager import NotificationManager
from core.ai_analyzer import AIAnalyzer
from core.error_manager import ErrorManager

# --- UIモジュールのインポート ---
from ui.dashboard import render_dashboard
from ui.logs import render_logs
from ui.pc_info import render_pc_info
from ui.reports import render_reports
from ui.admin import render_admin_settings

# --- ログ設定 ---
import logging
import os
log_dir = os.path.join(os.path.dirname(__file__), 'logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'app.log')
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# --- Streamlit アプリケーション設定 ---
st.set_page_config(
    page_title="タスク管理ダッシュボード", 
    page_icon="🤖", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# カスタムCSSを追加
st.markdown("""
<style>
/* トグルスイッチのスタイル */
.stToggle {
    background-color: #f0f2f6;
    border-radius: 20px;
    padding: 2px;
}

/* 有効状態のトグルスイッチ */
.stToggle > label[data-checked="true"] {
    background-color: #4CAF50;
    color: white;
}

/* 無効状態のトグルスイッチ */
.stToggle > label[data-checked="false"] {
    background-color: #f44336;
    color: white;
}

/* テーブルヘッダーのスタイル */
.table-header {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 12px 8px;
    border-radius: 8px 8px 0 0;
    font-weight: bold;
    text-align: center;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    margin-bottom: 2px;
}

/* テーブル行のスタイル */
.table-row {
    background: white;
    padding: 10px 8px;
    border-radius: 4px;
    margin: 2px 0;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    border-left: 4px solid #667eea;
    transition: all 0.3s ease;
}

.table-row:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 8px rgba(0,0,0,0.15);
    border-left-color: #764ba2;
}

/* テーブルセルのスタイル */
.table-cell {
    padding: 8px;
    border-radius: 4px;
    background: #f8f9fa;
    margin: 1px;
    border: 1px solid #e9ecef;
}

/* ステータス表示のスタイル */
.status-cell {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 4px;
}

/* ボタンのスタイル */
.action-button {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    border: none;
    border-radius: 6px;
    padding: 6px 12px;
    cursor: pointer;
    transition: all 0.3s ease;
    font-size: 12px;
}

.action-button:hover {
    transform: scale(1.05);
    box-shadow: 0 4px 8px rgba(0,0,0,0.2);
}

/* 成功/エラー状態のスタイル */
.status-success {
    color: #28a745;
    font-weight: bold;
}

.status-error {
    color: #dc3545;
    font-weight: bold;
}

.status-warning {
    color: #ffc107;
    font-weight: bold;
}

.status-info {
    color: #17a2b8;
    font-weight: bold;
}
</style>
""", unsafe_allow_html=True)

# --- 初期化処理 ---
if 'initialized' not in st.session_state:
    logging.info("=== アプリケーション初期化開始 ===")
    CONFIG_PATH = 'data/config.json'
    DB_PATH = 'data/logs.db'
    st.session_state.config_manager = ConfigManager(CONFIG_PATH)
    st.session_state.db_manager = DBManager(DB_PATH)
    st.session_state.error_manager = ErrorManager('data/error_codes.json')
    # TODO: 認証情報を安全に取得する
    DUMMY_USER, DUMMY_PASS = "YOUR_USERNAME", "YOUR_PASSWORD"
    st.session_state.task_manager = TaskManager(st.session_state.config_manager, st.session_state.db_manager, DUMMY_USER, DUMMY_PASS)
    st.session_state.current_view = 'pc_info'  # デフォルトをPC情報に変更
    st.session_state.initialized = True
    logging.info("=== アプリケーション初期化完了 ===")

# --- サイドバーと画面切り替え ---
with st.sidebar:
    st.title("メニュー")
    if st.button("PC情報", use_container_width=True): st.session_state.current_view = 'pc_info'
    if st.button("ダッシュボード", use_container_width=True): st.session_state.current_view = 'dashboard'
    if st.button("実行結果ログ", use_container_width=True): st.session_state.current_view = 'logs'
    if st.button("レポート", use_container_width=True): st.session_state.current_view = 'reports'
    if st.button("管理者設定", use_container_width=True): st.session_state.current_view = 'admin'

# --- メインコンテンツの表示 ---
if st.session_state.current_view == 'pc_info':
    render_pc_info()
elif st.session_state.current_view == 'dashboard':
    render_dashboard()
elif st.session_state.current_view == 'logs':
    render_logs()
elif st.session_state.current_view == 'reports':
    render_reports()
elif st.session_state.current_view == 'admin':
    render_admin_settings() 