#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
異なるユーザー名形式で認証テスト
"""

import json
import winrm

def test_auth_forms():
    """異なるユーザー名形式で認証をテスト"""
    
    # 認証情報を読み込み
    try:
        with open('credentials.json', 'r', encoding='utf-8') as f:
            credentials = json.load(f)
            base_username = credentials.get('username')
            password = credentials.get('password')
    except Exception as e:
        print(f"認証情報読み込みエラー: {e}")
        return
    
    # テストするユーザー名形式
    username_forms = [
        base_username,  # EPS50
        f"{base_username}\\Administrator",  # EPS50\Administrator
        f"{base_username}\\{base_username}",  # EPS50\EPS50
        "Administrator",  # Administrator
        f"192.168.1.57\\{base_username}",  # 192.168.1.57\EPS50
        f"192.168.1.57\\Administrator",  # 192.168.1.57\Administrator
    ]
    
    for username in username_forms:
        print(f"\n--- テスト: {username} ---")
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
                return username  # 成功したユーザー名を返す
            else:
                print("❌ 認証失敗")
                print(f"エラー: {result.std_err.decode('utf-8')}")
                
        except Exception as e:
            print(f"❌ 接続エラー: {e}")
    
    return None

if __name__ == "__main__":
    successful_username = test_auth_forms()
    if successful_username:
        print(f"\n🎉 成功したユーザー名: {successful_username}")
    else:
        print("\n❌ すべての形式で認証に失敗しました") 