#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
勤怠PC（EPS50）専用接続テストスクリプト
EPS50とのWinRM接続をテストします。
"""

import json
import sys
import os

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.task_manager import TaskManager
from core.config_manager import ConfigManager
from core.db_manager import DBManager

def test_eps50_connection():
    """EPS50との接続をテストする"""
    
    print("=== EPS50（勤怠PC）接続テスト開始 ===")
    
    # 設定ファイルを読み込み
    config_manager = ConfigManager('data/config.json')
    config = config_manager.get_config()
    
    # データベースマネージャーを初期化
    db_manager = DBManager('data/logs.db')
    
    # 認証情報を読み込み
    try:
        with open('credentials.json', 'r', encoding='utf-8') as f:
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
    
    # EPS50の情報を取得
    eps50_pc = None
    for pc in config.get('pcs', []):
        if pc.get('name') == 'EPS50':
            eps50_pc = pc
            break
    
    if not eps50_pc:
        print("❌ EPS50の設定が見つかりません。")
        return
    
    pc_name = eps50_pc.get('name')
    pc_ip = eps50_pc.get('ip')
    
    print(f"対象PC: {pc_name} ({pc_ip})")
    
    try:
        # TaskManagerを初期化
        task_manager = TaskManager(config_manager, db_manager, username, password)
        
        # 1. 基本的な疎通確認
        print(f"\n1. 基本疎通確認...")
        success, result = task_manager._execute_ps_command(pc_ip, "Get-Date")
        if success:
            print(f"✅ 基本接続成功: {result.strip()}")
        else:
            print(f"❌ 基本接続失敗: {result}")
            return
        
        # 2. システム情報取得
        print(f"\n2. システム情報取得...")
        success, result = task_manager._execute_ps_command(pc_ip, "Get-ComputerInfo | Select-Object WindowsProductName, WindowsVersion, TotalPhysicalMemory")
        if success:
            print(f"✅ システム情報取得成功:")
            print(f"   {result.strip()}")
        else:
            print(f"❌ システム情報取得失敗: {result}")
        
        # 3. タスクスケジューラ一覧取得
        print(f"\n3. タスクスケジューラ一覧取得...")
        tasks = task_manager.get_tasks_from_pc(pc_ip)
        print(f"✅ 取得したタスク数: {len(tasks)}")
        
        if tasks:
            print("   取得したタスク一覧:")
            for i, task in enumerate(tasks[:5], 1):  # 最初の5件のみ表示
                task_name = task.get('TaskName', 'Unknown')
                state = task.get('State', 'Unknown')
                print(f"   {i}. {task_name} - {state}")
            if len(tasks) > 5:
                print(f"   ... 他 {len(tasks) - 5} 件")
        
        # 4. 特定のタスク詳細確認
        print(f"\n4. 特定タスクの詳細確認...")
        if tasks:
            first_task = tasks[0]
            task_name = first_task.get('TaskName', 'Unknown')
            print(f"   タスク名: {task_name}")
            print(f"   状態: {first_task.get('State', 'Unknown')}")
            print(f"   次回実行: {first_task.get('NextRunTime', 'Unknown')}")
            print(f"   最終実行: {first_task.get('LastRunTime', 'Unknown')}")
            print(f"   最終結果: {first_task.get('LastTaskResult', 'Unknown')}")
        
        # 5. ディスク容量確認
        print(f"\n5. ディスク容量確認...")
        success, result = task_manager._execute_ps_command(pc_ip, "Get-WmiObject -Class Win32_LogicalDisk | Select-Object DeviceID, Size, FreeSpace | Format-Table -AutoSize")
        if success:
            print(f"✅ ディスク情報取得成功:")
            print(f"   {result.strip()}")
        else:
            print(f"❌ ディスク情報取得失敗: {result}")
        
        # 6. メモリ使用状況確認
        print(f"\n6. メモリ使用状況確認...")
        success, result = task_manager._execute_ps_command(pc_ip, "Get-WmiObject -Class Win32_OperatingSystem | Select-Object TotalVisibleMemorySize, FreePhysicalMemory | Format-Table -AutoSize")
        if success:
            print(f"✅ メモリ情報取得成功:")
            print(f"   {result.strip()}")
        else:
            print(f"❌ メモリ情報取得失敗: {result}")
        
        print(f"\n=== EPS50接続テスト完了 ===")
        print(f"✅ すべてのテストが正常に完了しました。")
        
    except Exception as e:
        print(f"❌ テスト実行中にエラーが発生しました: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("EPS50（勤怠PC）接続テストスクリプトを開始します...")
    
    # 設定ファイルの存在確認
    if not os.path.exists('data/config.json'):
        print("❌ 設定ファイルが見つかりません: data/config.json")
        sys.exit(1)
    
    # 認証情報ファイルの存在確認
    if not os.path.exists('credentials.json'):
        print("❌ 認証情報ファイルが見つかりません: credentials.json")
        print("python setup_credentials.py を実行して認証情報を設定してください。")
        sys.exit(1)
    
    # EPS50接続テスト実行
    test_eps50_connection() 