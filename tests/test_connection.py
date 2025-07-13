#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
接続テストスクリプト
実際の管理対象PCとのWinRM接続をテストします。
"""

import json
import sys
import os

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.task_manager import TaskManager
from core.config_manager import ConfigManager
from core.db_manager import DBManager

def test_connection():
    """管理対象PCとの接続をテストする"""
    
    # 設定ファイルを読み込み（プロジェクトルートからの相対パス）
    config_manager = ConfigManager('../data/config.json')
    config = config_manager.get_config()
    
    # データベースマネージャーを初期化（プロジェクトルートからの相対パス）
    db_manager = DBManager('../data/logs.db')
    
    # 認証情報を読み込み（プロジェクトルートからの相対パス）
    try:
        with open('../credentials.json', 'r', encoding='utf-8') as f:
            credentials = json.load(f)
            username = credentials.get('username')
            password = credentials.get('password')
    except FileNotFoundError:
        print("❌ 認証情報ファイルが見つかりません。")
        print("python setup_credentials.py を実行して認証情報を設定してください。")
        return
    except Exception as e:
        print(f"❌ 認証情報の読み込みに失敗しました: {e}")
        return
    
    print("=== 接続テスト開始 ===")
    print(f"設定ファイルから読み込んだPC数: {len(config.get('pcs', []))}")
    
    # 各PCとの接続をテスト
    for pc in config.get('pcs', []):
        pc_name = pc.get('name')
        pc_ip = pc.get('ip')
        
        print(f"\n--- {pc_name} ({pc_ip}) のテスト ---")
        
        try:
            # TaskManagerを初期化
            task_manager = TaskManager(config_manager, db_manager, username, password)
            
            # 簡単なPowerShellコマンドで疎通確認
            success, result = task_manager._execute_ps_command(pc_ip, "Get-ComputerInfo | Select-Object WindowsProductName, WindowsVersion")
            
            if success:
                print(f"✅ 接続成功: {pc_name}")
                print(f"   結果: {result.strip()}")
                
                # タスク一覧の取得テスト
                print(f"   タスク一覧取得テスト...")
                tasks = task_manager.get_tasks_from_pc(pc_ip)
                print(f"   取得したタスク数: {len(tasks)}")
                
            else:
                print(f"❌ 接続失敗: {pc_name}")
                print(f"   エラー: {result}")
                
        except Exception as e:
            print(f"❌ 例外発生: {pc_name}")
            print(f"   エラー: {str(e)}")
    
    print("\n=== 接続テスト完了 ===")

def test_simple_command():
    """簡単なコマンド実行テスト"""
    
    # 設定ファイルを読み込み（プロジェクトルートからの相対パス）
    config_manager = ConfigManager('../data/config.json')
    config = config_manager.get_config()
    
    # 最初のPCでテスト
    if config.get('pcs'):
        pc = config['pcs'][0]
        pc_name = pc.get('name')
        pc_ip = pc.get('ip')
        
        print(f"\n=== 簡単なコマンドテスト ({pc_name}) ===")
        
        # 認証情報を読み込み（プロジェクトルートからの相対パス）
        try:
            with open('../credentials.json', 'r', encoding='utf-8') as f:
                credentials = json.load(f)
                username = credentials.get('username')
                password = credentials.get('password')
        except FileNotFoundError:
            print("❌ 認証情報ファイルが見つかりません。")
            print("python setup_credentials.py を実行して認証情報を設定してください。")
            return
        except Exception as e:
            print(f"❌ 認証情報の読み込みに失敗しました: {e}")
            return
        
        try:
            db_manager = DBManager('../data/logs.db')
            task_manager = TaskManager(config_manager, db_manager, username, password)
            
            # システム情報取得
            success, result = task_manager._execute_ps_command(pc_ip, "Get-Date")
            if success:
                print(f"✅ 日時取得成功: {result.strip()}")
            else:
                print(f"❌ 日時取得失敗: {result}")
                
        except Exception as e:
            print(f"❌ テスト実行中にエラー: {str(e)}")

if __name__ == "__main__":
    print("接続テストスクリプトを開始します...")
    
    # 設定ファイルの存在確認（プロジェクトルートからの相対パス）
    if not os.path.exists('../data/config.json'):
        print("❌ 設定ファイルが見つかりません: ../data/config.json")
        sys.exit(1)
    
    # 認証情報ファイルの存在確認（プロジェクトルートからの相対パス）
    if not os.path.exists('../credentials.json'):
        print("❌ 認証情報ファイルが見つかりません: ../credentials.json")
        print("python setup_credentials.py を実行して認証情報を設定してください。")
        sys.exit(1)
    
    # 接続テスト実行
    test_connection()
    test_simple_command() 