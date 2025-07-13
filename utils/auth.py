# ==============================================================================
# 認証関連のユーティリティ関数
# ==============================================================================

import json
import streamlit as st

def load_credentials():
    """認証情報を読み込む"""
    try:
        with open('data/credentials.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        st.error("認証情報ファイルが見つかりません。data/credentials.jsonを作成してください。")
        return None
    except Exception as e:
        st.error(f"認証情報の読み込みに失敗しました: {e}")
        return None

def get_pc_credentials(credentials, pc_name):
    """指定されたPCの認証情報を取得する"""
    if not credentials:
        return None, None
    
    pc_creds = credentials.get(pc_name)
    if pc_creds:
        return pc_creds.get('username'), pc_creds.get('password')
    else:
        st.warning(f"PC '{pc_name}'の認証情報が見つかりません。")
        return None, None 