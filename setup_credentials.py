#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
認証情報設定スクリプト
リモート接続に使用するユーザー名とパスワードを設定します。
"""

import json
import getpass
import os

def setup_credentials():
    """認証情報を設定する"""
    print("=== 認証情報設定 ===")
    print("リモート接続に使用する認証情報を入力してください。")
    print()
    
    # ユーザー名を入力
    username = input("ユーザー名: ").strip()
    if not username:
        print("❌ ユーザー名を入力してください。")
        return False
    
    # パスワードを入力（非表示）
    password = getpass.getpass("パスワード: ")
    if not password:
        print("❌ パスワードを入力してください。")
        return False
    
    # 認証情報を辞書に格納
    credentials = {
        "username": username,
        "password": password
    }
    
    # ファイルに保存
    try:
        with open('credentials.json', 'w', encoding='utf-8') as f:
            json.dump(credentials, f, ensure_ascii=False, indent=2)
        
        print("✅ 認証情報が正常に保存されました。")
        print(f"保存先: {os.path.abspath('credentials.json')}")
        return True
        
    except Exception as e:
        print(f"❌ 認証情報の保存に失敗しました: {e}")
        return False

if __name__ == "__main__":
    setup_credentials() 