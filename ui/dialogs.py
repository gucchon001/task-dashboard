# ==============================================================================
# ダイアログ関数
# ==============================================================================

import streamlit as st
import pandas as pd
import datetime
import os
import json
import logging

@st.dialog("タスク詳細")
def task_detail_dialog(task, pc_name, pc_ip):
    # ヘッダー部分
    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
    ">
        <h2 style="margin: 0; color: white;">📋 {task['TaskName']}</h2>
        <p style="margin: 5px 0 0 0; opacity: 0.9;">対象PC: {pc_name} ({pc_ip})</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 状態情報の表示
    from utils.task_helpers import get_task_state_info, format_datetime, format_trigger_info
    state_info = get_task_state_info(task['State'])
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("状態", state_info['status'], delta=None)
    with col2:
        next_run = format_datetime(task.get('NextRunTime'))
        st.metric("次回実行", next_run)
    with col3:
        last_run = format_datetime(task.get('LastRunTime'))
        st.metric("最終実行", last_run)
    
    # エラー情報の表示
    if 'LastTaskResult' in task and task['LastTaskResult'] != 0:
        error_code = task['LastTaskResult']
        error_manager = st.session_state.error_manager
        error_message = error_manager.get_error_message(error_code)
        
        st.error(f"⚠️ 最終実行でエラーが発生しました (コード: {error_code})")
        st.error(f"エラー内容: {error_message}")
        
        # タイムアウトエラーの場合の対処法を表示
        if error_manager.is_timeout_error(error_code):
            timeout_solutions = error_manager.get_timeout_solutions()
            with st.expander(f"🔧 {timeout_solutions['title']}", expanded=True):
                st.info("**対処法:**")
                for i, step in enumerate(timeout_solutions['steps'], 1):
                    st.write(f"{i}. **{step['title']}**")
                    st.write(f"   {step['description']}")
                    st.write("")
        
        st.write("---")
    
    # 詳細情報の表示
    with st.expander("📊 タスク詳細情報", expanded=True):
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**基本情報**")
            st.write(f"**タスク名:** {task['TaskName']}")
            st.write(f"**PC名:** {task['PC名']}")
            st.write(f"**状態:** {state_info['status']} {state_info['icon']}")
            if 'Author' in task:
                st.write(f"**作成者:** {task['Author']}")
            if 'Description' in task and task['Description']:
                st.write(f"**説明:** {task['Description']}")
        
        with col2:
            st.write("**実行情報**")
            st.write(f"**次回実行:** {format_datetime(task.get('NextRunTime'))}")
            st.write(f"**最終実行:** {format_datetime(task.get('LastRunTime'))}")
            if 'LastTaskResult' in task:
                if task['LastTaskResult'] == 0:
                    result_text = "成功"
                    result_color = "green"
                else:
                    error_message = error_manager.get_error_message(task['LastTaskResult'])
                    result_text = f"エラー (コード: {task['LastTaskResult']}) - {error_message}"
                    result_color = "red"
                st.write(f"**最終結果:** {result_text}")
            if 'Trigger' in task and task['Trigger']:
                trigger_formatted = format_trigger_info(task['Trigger'])
                st.write(f"**トリガー:** {trigger_formatted}")
                # 詳細なトリガー情報を展開可能なセクションに表示
                with st.expander("詳細トリガー情報"):
                    st.code(task['Trigger'], language="text")
    
    # アクションセクション
    st.write("---")
    st.subheader("🔧 アクション")
    
    # ステータストグルセクション
    st.write("**ステータス切り替え**")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # 現在の状態を表示
        current_state = task['State']
        is_currently_enabled = current_state in [3, 4]  # Ready(3) または Running(4)
        
        if is_currently_enabled:
            st.success(f"✅ 現在: 有効 ({state_info['status']})")
        else:
            st.error(f"🔴 現在: 無効 ({state_info['status']})")
    
    with col2:
        # トグルボタン
        if st.button("🔄 ステータスを切り替え", use_container_width=True, type="primary"):
            # PCの認証情報を取得
            from utils.auth import load_credentials, get_pc_credentials
            credentials = load_credentials()
            username, password = get_pc_credentials(credentials, pc_name)
            if not username or not password:
                st.error(f"❌ {pc_name}の認証情報が見つかりません。")
            else:
                # PCごとにTaskManagerを初期化
                from core.task_manager import TaskManager
                pc_task_manager = TaskManager(
                    st.session_state.config_manager, 
                    st.session_state.db_manager, 
                    username, 
                    password
                )
                
                # 新しい状態を決定
                new_state = "Disabled" if is_currently_enabled else "Ready"
                update_details = {"State": new_state}
                
                success, msg = pc_task_manager.update_task(pc_ip, task['TaskName'], update_details, user_identifier=os.getlogin())
                if success: 
                    st.success(f"✅ ステータスを{'無効' if is_currently_enabled else '有効'}に変更しました")
                    st.rerun()
                else: 
                    st.error(f"❌ ステータス変更に失敗しました: {msg}")
    
    with col3:
        # 手動実行ボタン
        if st.button("▶️ 手動実行", use_container_width=True):
            st.info("🚧 タスク実行機能は今後実装予定です。")
    
    # 編集フォーム
    with st.form("edit_task_form", clear_on_submit=False):
        st.write("**タスク設定の編集**")
        
        col1, col2 = st.columns(2)
        with col1:
            new_description = st.text_area("説明", value=task.get('Description', ''), height=100)
        with col2:
            st.write("**現在の状態:**", state_info['status'])
            st.write("**ステータス変更は上記のトグルボタンを使用してください**")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.form_submit_button("💾 説明を更新", use_container_width=True, type="primary"):
                # PCの認証情報を取得
                credentials = load_credentials()
                username, password = get_pc_credentials(credentials, pc_name)
                if not username or not password:
                    st.error(f"❌ {pc_name}の認証情報が見つかりません。")
                else:
                    # PCごとにTaskManagerを初期化
                    pc_task_manager = TaskManager(
                        st.session_state.config_manager, 
                        st.session_state.db_manager, 
                        username, 
                        password
                    )
                    update_details = {"Description": new_description}
                    
                    success, msg = pc_task_manager.update_task(pc_ip, task['TaskName'], update_details, user_identifier=os.getlogin())
                    if success: 
                        st.success(f"✅ 説明を更新しました")
                        st.rerun()
                    else: 
                        st.error(f"❌ 説明の更新に失敗しました: {msg}")
        
        with col2:
            if st.form_submit_button("🗑️ 削除", use_container_width=True, type="secondary"):
                # 削除確認
                if st.session_state.get("confirm_delete_task", False):
                    # PCの認証情報を取得
                    credentials = load_credentials()
                    username, password = get_pc_credentials(credentials, pc_name)
                    if not username or not password:
                        st.error(f"❌ {pc_name}の認証情報が見つかりません。")
                    else:
                        # PCごとにTaskManagerを初期化
                        pc_task_manager = TaskManager(
                            st.session_state.config_manager, 
                            st.session_state.db_manager, 
                            username, 
                            password
                        )
                        success, msg = pc_task_manager.delete_task(pc_ip, task['TaskName'], user_identifier=os.getlogin())
                        if success: 
                            st.success(f"✅ タスクを削除しました")
                            st.rerun()
                        else: 
                            st.error(f"❌ タスク削除に失敗しました: {msg}")
                else:
                    st.session_state["confirm_delete_task"] = True
                    st.warning("⚠️ 削除を確認するには、もう一度ボタンを押してください。")
    
    # 実行履歴セクション（将来実装）
    st.write("---")
    with st.expander("📈 実行履歴", expanded=False):
        st.info("📊 実行履歴機能は今後実装予定です。")
        # ここに実行履歴の表示を追加予定

@st.dialog("新規タスク作成")
def create_task_dialog():
    # ヘッダー部分
    st.markdown("""
    <div style="
        background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);
        color: white;
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
    ">
        <h2 style="margin: 0; color: white;">➕ 新しいタスクの作成</h2>
        <p style="margin: 5px 0 0 0; opacity: 0.9;">Windowsタスクスケジューラに新しいタスクを追加します</p>
    </div>
    """, unsafe_allow_html=True)
    
    with st.form("create_task_form", clear_on_submit=True):
        # 基本情報セクション
        st.subheader("📋 基本情報")
        
        config_manager = st.session_state.config_manager
        pc_list = {pc['name']: pc['ip'] for pc in config_manager.get_config().get('pcs', [])}
        if not pc_list:
            st.error("❌ 管理対象PCが設定されていません。管理者設定画面からPCを追加・設定してください。")
            st.stop()
        
        col1, col2 = st.columns(2)
        with col1:
            selected_pc_name = st.selectbox("対象PC *", options=list(pc_list.keys()), help="タスクを実行するPCを選択してください")
        with col2:
            task_name = st.text_input("タスク名 *", placeholder="例: データバックアップ", help="一意のタスク名を入力してください")
        
        description = st.text_area("説明", placeholder="タスクの目的や処理内容を記述してください", height=80)
        
        st.write("---")
        
        # 実行設定セクション
        st.subheader("⚙️ 実行設定")
        
        execution_type = st.selectbox(
            "実行タイプ *", 
            ["標準プログラム (.exe, .bat)", "Python スクリプト", "PowerShell スクリプト"],
            help="実行するプログラムの種類を選択してください"
        )
        
        if "Python" in execution_type:
            col1, col2 = st.columns(2)
            with col1:
                program_path = st.text_input(
                    "python.exeのパス *", 
                    placeholder="C:\\Python311\\python.exe",
                    help="Python実行ファイルのフルパス"
                )
            with col2:
                script_path = st.text_input(
                    "スクリプトのパス (.py) *", 
                    placeholder="\\\\nas-server\\scripts\\my_script.py",
                    help="実行するPythonスクリプトのフルパス"
                )
        elif "PowerShell" in execution_type:
            col1, col2 = st.columns(2)
            with col1:
                program_path = st.text_input(
                    "PowerShellのパス *", 
                    placeholder="C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe",
                    help="PowerShell実行ファイルのフルパス"
                )
            with col2:
                script_path = st.text_input(
                    "スクリプトのパス (.ps1) *", 
                    placeholder="\\\\nas-server\\scripts\\my_script.ps1",
                    help="実行するPowerShellスクリプトのフルパス"
                )
        else:
            col1, col2 = st.columns(2)
            with col1:
                program_path = st.text_input(
                    "プログラム/スクリプトのパス *", 
                    placeholder="\\\\nas-server\\batch\\my_task.bat",
                    help="実行するプログラムまたはスクリプトのフルパス"
                )
            with col2:
                script_path = st.text_input(
                    "引数 (オプション)", 
                    placeholder="引数がある場合は入力してください",
                    help="プログラムに渡す引数（オプション）"
                )
        
        st.write("---")
        
        # スケジュール設定セクション
        st.subheader("📅 スケジュール設定")
        
        col1, col2 = st.columns(2)
        with col1:
            schedule_type = st.selectbox(
                "スケジュールタイプ",
                ["毎日", "毎週", "毎月", "一回限り"],
                help="タスクの実行スケジュールを選択してください"
            )
        with col2:
            start_time = st.time_input("開始時刻", value=datetime.time(9, 0), help="タスクの開始時刻を設定してください")
        
        # スケジュールタイプに応じた追加設定
        if schedule_type == "毎週":
            weekdays = st.multiselect(
                "実行曜日",
                ["月曜日", "火曜日", "水曜日", "木曜日", "金曜日", "土曜日", "日曜日"],
                default=["月曜日"],
                help="タスクを実行する曜日を選択してください"
            )
        elif schedule_type == "毎月":
            month_day = st.number_input("実行日", min_value=1, max_value=31, value=1, help="毎月の実行日を設定してください")
        
        st.write("---")
        
        # 確認・実行セクション
        st.subheader("✅ 確認・実行")
        
        # 入力内容の確認表示
        if task_name and program_path:
            st.info("**入力内容の確認:**")
            st.write(f"**対象PC:** {selected_pc_name}")
            st.write(f"**タスク名:** {task_name}")
            st.write(f"**実行タイプ:** {execution_type}")
            st.write(f"**プログラムパス:** {program_path}")
            if script_path:
                st.write(f"**スクリプトパス:** {script_path}")
            st.write(f"**スケジュール:** {schedule_type} {start_time.strftime('%H:%M')}")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.form_submit_button("🚫 キャンセル", use_container_width=True, type="secondary"):
                st.rerun()
        with col2:
            if st.form_submit_button("✅ 作成", use_container_width=True, type="primary"):
                if not task_name or not program_path:
                    st.warning("⚠️ タスク名とプログラムパスは必須です。")
                else:
                    # 選択されたPCの認証情報を取得
                    from utils.auth import load_credentials, get_pc_credentials
                    credentials = load_credentials()
                    username, password = get_pc_credentials(credentials, selected_pc_name)
                    if not username or not password:
                        st.error(f"❌ {selected_pc_name}の認証情報が見つかりません。")
                    else:
                        # PCごとにTaskManagerを初期化
                        from core.task_manager import TaskManager
                        pc_task_manager = TaskManager(
                            st.session_state.config_manager, 
                            st.session_state.db_manager, 
                            username, 
                            password
                        )
                        # 設定されたフォルダパスの最初のフォルダにタスクを作成
                        task_folders = config_manager.get_config().get('task_folders', ['\\CustomTasks\\'])
                        target_folder = task_folders[0] if task_folders else '\\CustomTasks\\'
                        
                        task_details = {
                            "TaskName": task_name, 
                            "Description": description, 
                            "execution_type": execution_type, 
                            "program_path": program_path, 
                            "script_path": script_path,
                            "task_path": target_folder,
                            "schedule_type": schedule_type,
                            "start_time": start_time.strftime('%H:%M')
                        }
                            
                        success, msg = pc_task_manager.create_task(pc_list[selected_pc_name], task_details, user_identifier=os.getlogin())
                        if success: 
                            st.success(f"✅ {msg}")
                            st.rerun()
                        else: 
                            st.error(f"❌ {msg}") 