#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
認証情報設定スクリプト
実際の環境に合わせて認証情報を設定します。
"""

import getpass
import json
import os

def setup_credentials():
    """認証情報を設定する"""
    
    print("=== 認証情報設定 ===")
    print("管理対象PCへの接続に使用する認証情報を設定します。")
    
    # ユーザー名入力
    username = input("ユーザー名を入力してください (例: administrator): ").strip()
    if not username:
        print("❌ ユーザー名が入力されていません。")
        return False
    
    # パスワード入力（非表示）
    password = getpass.getpass("パスワードを入力してください: ")
    if not password:
        print("❌ パスワードが入力されていません。")
        return False
    
    # 認証情報を保存
    credentials = {
        "username": username,
        "password": password
    }
    
    # 認証情報ファイルに保存（プロジェクトルートからの相対パス）
    with open('../credentials.json', 'w', encoding='utf-8') as f:
        json.dump(credentials, f, indent=2, ensure_ascii=False)
    
    print("✅ 認証情報を保存しました: ../credentials.json")
    print("注意: このファイルは機密情報を含むため、.gitignoreに追加することを推奨します。")
    
    return True

def load_credentials():
    """保存された認証情報を読み込む"""
    if os.path.exists('../credentials.json'):
        with open('../credentials.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

if __name__ == "__main__":
    setup_credentials() 