# ==============================================================================
# PC情報画面のレンダリング関数
# ==============================================================================

import streamlit as st
import pandas as pd
import datetime
import os
import json
import logging

def render_pc_info():
    st.header("PC情報")
    
    # 認証情報の読み込み
    from utils.auth import load_credentials, get_pc_credentials
    credentials = load_credentials()
    if not credentials:
        st.error("認証情報が設定されていません。credentials.jsonを作成してください。")
        return
    
    # 設定からPC一覧とPCグループを取得
    config_manager = st.session_state.config_manager
    pcs = config_manager.get_config().get('pcs', [])
    pc_groups = config_manager.get_config().get('pc_groups', [])
    
    if not pcs:
        st.warning("管理対象PCが設定されていません。")
        return
    
    # PCグループ情報の表示
    if pc_groups:
        st.subheader("PCグループ一覧")
        for group in pc_groups:
            st.info(f"**{group['name']}**: {group['description']}")
        
        st.write("---")
    
    # PC情報の取得
    st.subheader("PC一覧")
    
    # 進捗バー
    progress_bar = st.progress(0, text="PC情報を取得中...")
    
    pc_info_list = []
    for i, pc in enumerate(pcs):
        progress_bar.progress((i + 1) / len(pcs), text=f"{pc['name']}...")
        
        # PCごとの認証情報を取得
        username, password = get_pc_credentials(credentials, pc['name'])
        if not username or not password:
            # 認証情報が取得できない場合はスキップ
            pc_info = {
                'name': pc['name'],
                'ip': pc['ip'],
                'group': pc.get('group', '未分類'),
                'status': 'Error',
                'error': f'認証情報が見つかりません: {pc["name"]}'
            }
            pc_info_list.append(pc_info)
            continue
        
        # PCごとにTaskManagerを初期化
        from core.task_manager import TaskManager
        pc_task_manager = TaskManager(
            st.session_state.config_manager, 
            st.session_state.db_manager, 
            username, 
            password
        )
        
        pc_info = get_pc_info(pc_task_manager, pc['ip'], pc['name'])
        pc_info['group'] = pc.get('group', '未分類')
        pc_info_list.append(pc_info)
    
    progress_bar.empty()
    
    # PC情報を表示
    for pc_info in pc_info_list:
        group_info = f" [{pc_info['group']}]" if pc_info.get('group') else ""
        with st.expander(f"{pc_info['name']} ({pc_info['ip']}){group_info} - {pc_info['status']}", expanded=True):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("ステータス", pc_info['status'])
                if pc_info['status'] == 'Online':
                    st.metric("最終確認", pc_info.get('last_seen', 'Unknown'))
                st.metric("タスク数", pc_info['tasks_count'])
                if pc_info.get('group'):
                    st.metric("グループ", pc_info['group'])
            
            with col2:
                st.subheader("システム情報")
                if pc_info['system_info'] and 'error' not in pc_info['system_info']:
                    st.write(f"**OS:** {pc_info['system_info'].get('WindowsProductName', 'Unknown')}")
                    st.write(f"**バージョン:** {pc_info['system_info'].get('WindowsVersion', 'Unknown')}")
                    if pc_info['system_info'].get('TotalPhysicalMemory'):
                        memory_gb = pc_info['system_info']['TotalPhysicalMemory'] / (1024**3)
                        st.write(f"**メモリ:** {memory_gb:.1f} GB")
                else:
                    st.write("システム情報の取得に失敗しました")
            
            with col3:
                st.subheader("リソース情報")
                if pc_info['disk_info']:
                    for disk in pc_info['disk_info']:
                        if disk.get('Size') and disk.get('FreeSpace'):
                            total_gb = disk['Size'] / (1024**3)
                            free_gb = disk['FreeSpace'] / (1024**3)
                            used_gb = total_gb - free_gb
                            usage_percent = (used_gb / total_gb) * 100
                            
                            st.write(f"**{disk.get('DeviceID', 'Unknown')}:**")
                            st.progress(usage_percent / 100)
                            st.caption(f"{used_gb:.1f}GB / {total_gb:.1f}GB ({usage_percent:.1f}%)")
                
                if pc_info['memory_info'] and 'error' not in pc_info['memory_info']:
                    total_mb = pc_info['memory_info'].get('TotalVisibleMemorySize', 0) / 1024
                    free_mb = pc_info['memory_info'].get('FreePhysicalMemory', 0) / 1024
                    used_mb = total_mb - free_mb
                    memory_usage = (used_mb / total_mb) * 100 if total_mb > 0 else 0
                    
                    st.write("**メモリ使用率:**")
                    st.progress(memory_usage / 100)
                    st.caption(f"{used_mb:.1f}GB / {total_mb:.1f}GB ({memory_usage:.1f}%)")
            
            # エラー情報の表示
            if pc_info['status'] == 'Error' and 'error' in pc_info:
                st.error(f"エラー: {pc_info['error']}")

def get_pc_info(task_manager, pc_ip, pc_name):
    """PCの詳細情報を取得する"""
    info = {
        'name': pc_name,
        'ip': pc_ip,
        'status': 'Unknown',
        'system_info': {},
        'disk_info': {},
        'memory_info': {},
        'tasks_count': 0
    }
    
    try:
        # 1. 基本接続確認
        success, result = task_manager._execute_ps_command(pc_ip, "Get-Date -Format 'yyyy/MM/dd HH:mm:ss'")
        if success:
            info['status'] = 'Online'
            # 日付文字列をクリーンアップ
            cleaned_date = result.strip().replace('\r', '').replace('\n', '')
            info['last_seen'] = cleaned_date
        else:
            info['status'] = 'Offline'
            return info
        
        # 2. システム情報取得
        success, result = task_manager._execute_ps_command(pc_ip, "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; Get-ComputerInfo | Select-Object WindowsProductName, WindowsVersion, TotalPhysicalMemory | ConvertTo-Json -Compress")
        if success:
            try:
                # 改行文字を除去してからJSON解析
                cleaned_result = result.strip().replace('\r', '').replace('\n', '')
                system_data = json.loads(cleaned_result)
                info['system_info'] = system_data
            except:
                info['system_info'] = {'error': 'JSON parse failed'}
        
        # 3. ディスク情報取得
        success, result = task_manager._execute_ps_command(pc_ip, "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; Get-WmiObject -Class Win32_LogicalDisk | Select-Object DeviceID, Size, FreeSpace | ConvertTo-Json -Compress")
        if success:
            try:
                # 改行文字を除去してからJSON解析
                cleaned_result = result.strip().replace('\r', '').replace('\n', '')
                disk_data = json.loads(cleaned_result)
                info['disk_info'] = disk_data if isinstance(disk_data, list) else [disk_data]
            except:
                info['disk_info'] = []
        
        # 4. メモリ情報取得
        success, result = task_manager._execute_ps_command(pc_ip, "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; Get-WmiObject -Class Win32_OperatingSystem | Select-Object TotalVisibleMemorySize, FreePhysicalMemory | ConvertTo-Json -Compress")
        if success:
            try:
                # 改行文字を除去してからJSON解析
                cleaned_result = result.strip().replace('\r', '').replace('\n', '')
                memory_data = json.loads(cleaned_result)
                info['memory_info'] = memory_data
            except:
                info['memory_info'] = {'error': 'JSON parse failed'}
        
        # 5. タスク数取得
        tasks = task_manager.get_tasks_from_pc(pc_ip)
        info['tasks_count'] = len(tasks) if tasks else 0
        
    except Exception as e:
        info['status'] = 'Error'
        info['error'] = str(e)
    
    return info 