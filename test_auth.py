#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
認証情報テストスクリプト
"""

import json
import winrm

def test_auth():
    """認証情報をテストする"""
    
    # 認証情報を読み込み
    try:
        with open('credentials.json', 'r', encoding='utf-8') as f:
            credentials = json.load(f)
            username = credentials.get('username')
            password = credentials.get('password')
    except Exception as e:
        print(f"認証情報読み込みエラー: {e}")
        return
    
    print(f"ユーザー名: {username}")
    print(f"パスワード: {'*' * len(password) if password else 'None'}")
    
    # 接続テスト
    try:
        session = winrm.Session(
            'http://192.168.1.57:5985/wsman',
            auth=(username, password),
            transport='ntlm',
            server_cert_validation='ignore'
        )
        
        result = session.run_ps('Get-Date')
        if result.status_code == 0:
            print("✅ 認証成功!")
            print(f"結果: {result.std_out.decode('utf-8')}")
        else:
            print("❌ 認証失敗")
            print(f"エラー: {result.std_err.decode('utf-8')}")
            
    except Exception as e:
        print(f"❌ 接続エラー: {e}")

if __name__ == "__main__":
    test_auth() 