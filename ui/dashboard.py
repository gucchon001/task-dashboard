# ==============================================================================
# ダッシュボード画面のレンダリング関数
# ==============================================================================

import streamlit as st
import pandas as pd
import datetime
import os
import json
import logging

def render_dashboard():
    st.header("ダッシュボード")
    
    # 設定からPC一覧を取得
    config_manager = st.session_state.config_manager
    config = config_manager.get_config()
    all_pcs = config.get('pcs', [])
    
    if not all_pcs:
        st.warning("管理対象PCが設定されていません。「管理者設定」画面からPCを追加・設定してください。")
        return
    
    # タブの作成（ALL + 各PC）
    tab_names = ["ALL"] + [pc['name'] for pc in all_pcs]
    tabs = st.tabs(tab_names)
    
    # 各タブの内容を処理
    for tab_idx, (tab, pc_name) in enumerate(zip(tabs, tab_names)):
        with tab:
            if pc_name == "ALL":
                # ALLタブ：全PCのタスクを表示
                render_pc_tasks(all_pcs, f"全PC ({len(all_pcs)}台)")
            else:
                # 個別PCタブ：該当PCのタスクのみを表示
                selected_pc = next((pc for pc in all_pcs if pc['name'] == pc_name), None)
                if selected_pc:
                    render_pc_tasks([selected_pc], f"{pc_name}")

def render_pc_tasks(pcs_to_scan, title):
    """指定されたPCのタスクを表示する関数"""
    st.subheader(f"タスク一覧 ({title} - 手動作成タスク)")
    
    # 新規作成ボタン
    if st.button("＋ 新規タスクを作成", type="primary", use_container_width=True, key=f"create_{title}"):
        from ui.dialogs import create_task_dialog
        create_task_dialog()
    
    # タスク情報の取得
    all_tasks = []
    progress_bar = st.progress(0, text="タスク情報を取得中...")
    
    # 認証情報の読み込み
    from utils.auth import load_credentials, get_pc_credentials
    
    logging.info(f"=== タスク取得処理開始: {title} ===")
    logging.info(f"対象PC数: {len(pcs_to_scan)}")
    
    for i, pc in enumerate(pcs_to_scan):
        progress_bar.progress((i + 1) / len(pcs_to_scan), text=f"{pc['name']}...")
        logging.info(f"=== PC処理開始: {pc['name']} ({pc['ip']}) ===")
        
        # PCごとの認証情報を取得
        credentials = load_credentials()
        username, password = get_pc_credentials(credentials, pc['name'])
        if not username or not password:
            logging.warning(f"{pc['name']}の認証情報が見つかりません。スキップします。")
            st.warning(f"{pc['name']}の認証情報が見つかりません。スキップします。")
            continue
        
        # PCごとにTaskManagerを初期化
        from core.task_manager import TaskManager
        pc_task_manager = TaskManager(
            st.session_state.config_manager, 
            st.session_state.db_manager, 
            username, 
            password
        )
        
        # 手動作成タスクのみを取得（修正済み）
        logging.info(f"=== {pc['name']}からタスク取得開始 ===")
        tasks = pc_task_manager.get_tasks_from_pc(pc['ip'])
        logging.info(f"=== {pc['name']}から取得されたタスク数: {len(tasks)} ===")
        
        for task in tasks:
            task['PC名'] = pc['name']
            task['PC_IP'] = pc['ip']
            all_tasks.append(task)
        
        logging.info(f"=== PC処理完了: {pc['name']}, 累計タスク数: {len(all_tasks)} ===")
    
    progress_bar.empty()
    logging.info(f"=== タスク取得処理完了: {title}, 総タスク数: {len(all_tasks)} ===")

    if not all_tasks:
        st.info("対象のタスクは見つかりませんでした。")
        return

    df = pd.DataFrame(all_tasks)
    
    # デバッグ情報を表示（開発時のみ）
    if st.checkbox("デバッグ情報を表示", key=f"debug_{title}"):
        st.write("**取得されたタスクデータ:**")
        st.write(f"総タスク数: {len(df)}")
        st.write("**State値の分布:**")
        state_counts = df['State'].value_counts()
        st.write(state_counts)
        st.write("**State値の詳細（最初の10件）:**")
        for i, (idx, task) in enumerate(df.head(10).iterrows()):
            st.write(f"{i+1}. {task['TaskName']} - State: {task['State']}")
        st.write("**サンプルデータ:**")
        st.write(df.head(3)[['TaskName', 'State', 'LastTaskResult', 'NextRunTime', 'LastRunTime']])
    
    if df.empty:
        st.info("フィルタ条件に一致するタスクは見つかりませんでした。")
        return
    
    # 統計情報の表示
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        total_tasks = len(df)
        st.metric("総タスク数", total_tasks)
    with col2:
        active_tasks = len(df[df['State'].isin([3, 4])])
        st.metric("アクティブ", active_tasks, delta=f"{active_tasks - (total_tasks - active_tasks)}")
    with col3:
        error_tasks = len(df[df['LastTaskResult'] != 0]) if 'LastTaskResult' in df.columns else 0
        st.metric("エラー", error_tasks, delta=f"-{error_tasks}" if error_tasks > 0 else None)
    with col4:
        pc_count = df['PC名'].nunique()
        st.metric("対象PC数", pc_count)
    
    st.write("---")
    
    # テーブル形式でのタスク表示
    st.subheader("タスク詳細一覧")
    
    # 並び替え機能をヘッダーの上に配置
    col1, col2, col3 = st.columns([2, 1, 0.3])
    with col1:
        st.write("")  # 空のスペース
    with col2:
        if f'sort_order_{title}' not in st.session_state:
            st.session_state[f'sort_order_{title}'] = "次回実行日時順"
        sort_order = st.selectbox("並べ替え", ["次回実行日時順", "作成日時順", "タスク名順"], key=f"sort_{title}", label_visibility="collapsed")
        st.session_state[f'sort_order_{title}'] = sort_order
    with col3:
        if f'sort_direction_{title}' not in st.session_state:
            st.session_state[f'sort_direction_{title}'] = "昇順"
        sort_direction = st.selectbox("順序", ["昇順", "降順"], key=f"direction_{title}", label_visibility="collapsed")
        st.session_state[f'sort_direction_{title}'] = sort_direction
    
    # 並び替え処理
    ascending = st.session_state[f'sort_direction_{title}'] == "昇順"
    
    if st.session_state[f'sort_order_{title}'] == "次回実行日時順":
        df = df.sort_values('NextRunTime', ascending=ascending, na_position='last')
    elif st.session_state[f'sort_order_{title}'] == "作成日時順":
        df = df.sort_values('LastRunTime', ascending=ascending, na_position='last')
    elif st.session_state[f'sort_order_{title}'] == "タスク名順":
        df = df.sort_values('TaskName', ascending=ascending)
    
    # ページネーション（シンプル・右寄せ）
    items_per_page = 100  # 1ページあたりの表示件数
    if f'current_page_{title}' not in st.session_state:
        st.session_state[f'current_page_{title}'] = 0
    total_pages = (len(df) - 1) // items_per_page + 1
    start_idx = st.session_state[f'current_page_{title}'] * items_per_page
    end_idx = min(start_idx + items_per_page, len(df))

    # 右寄せレイアウト
    col_space, col_pager = st.columns([6, 1])
    with col_pager:
        pager_col1, pager_col2, pager_col3 = st.columns([1, 2, 1])
        with pager_col1:
            if st.button("＜", disabled=st.session_state[f'current_page_{title}'] == 0, key=f"prev_{title}"):
                st.session_state[f'current_page_{title}'] = max(0, st.session_state[f'current_page_{title}'] - 1)
                st.rerun()
        with pager_col2:
            st.markdown(f"<div style='text-align:center; padding-top: 6px; font-weight:bold;'>{st.session_state[f'current_page_{title}'] + 1} / {total_pages}</div>", unsafe_allow_html=True)
        with pager_col3:
            if st.button("＞", disabled=st.session_state[f'current_page_{title}'] >= total_pages - 1, key=f"next_{title}"):
                st.session_state[f'current_page_{title}'] = min(total_pages - 1, st.session_state[f'current_page_{title}'] + 1)
                st.rerun()

    # 現在のページのタスクを表示
    current_page_df = df.iloc[start_idx:end_idx]
    
    # テーブルヘッダー
    col1, col2, col3, col4, col5, col6, col7, col8 = st.columns((1, 1, 2, 1, 1, 1, 0.5, 0.5))
    col1.markdown("<div style='text-align: center; background: #3498db; color: white; padding: 12px 8px; border-radius: 4px; font-weight: bold;'><strong>ステータス</strong></div>", unsafe_allow_html=True)
    col2.markdown("<div style='text-align: center; background: #3498db; color: white; padding: 12px 8px; border-radius: 4px; font-weight: bold;'><strong>タスク名</strong></div>", unsafe_allow_html=True)
    col3.markdown("<div style='text-align: center; background: #3498db; color: white; padding: 12px 8px; border-radius: 4px; font-weight: bold;'><strong>実行結果</strong></div>", unsafe_allow_html=True)
    col4.markdown("<div style='text-align: center; background: #3498db; color: white; padding: 12px 8px; border-radius: 4px; font-weight: bold;'><strong>次回実行</strong></div>", unsafe_allow_html=True)
    col5.markdown("<div style='text-align: center; background: #3498db; color: white; padding: 12px 8px; border-radius: 4px; font-weight: bold;'><strong>最終実行</strong></div>", unsafe_allow_html=True)
    col6.markdown("<div style='text-align: center; background: #3498db; color: white; padding: 12px 8px; border-radius: 4px; font-weight: bold;'><strong>⏱ 開始時刻</strong></div>", unsafe_allow_html=True)
    col7.markdown("<div style='text-align: center; background: #3498db; color: white; padding: 12px 8px; border-radius: 4px; font-weight: bold;'><strong>実行</strong></div>", unsafe_allow_html=True)
    col8.markdown("<div style='text-align: center; background: #3498db; color: white; padding: 12px 8px; border-radius: 4px; font-weight: bold;'><strong>詳細</strong></div>", unsafe_allow_html=True)
    
    # 並び替え処理
    if st.session_state[f'sort_order_{title}'] == "次回実行日時順":
        df = df.sort_values('NextRunTime', na_position='last')
    elif st.session_state[f'sort_order_{title}'] == "作成日時順":
        df = df.sort_values('LastRunTime', na_position='last')
    elif st.session_state[f'sort_order_{title}'] == "タスク名順":
        df = df.sort_values('TaskName')
    
    # ヘッダーとボディの間にマージンを追加
    st.markdown("<div style='margin: 20px 0;'></div>", unsafe_allow_html=True)
    
    # テーブルボディ（各行）
    for idx, task in current_page_df.iterrows():
        # 状態に応じたクラスとアイコン
        from utils.task_helpers import get_task_state_info, get_task_result_info, format_datetime, format_trigger_info
        
        state_info = get_task_state_info(task['State'])
        
        # 実行結果の判定と表示
        result_info = get_task_result_info(task)
        
        # 日時フォーマット
        next_run = format_datetime(task.get('NextRunTime'))
        last_run = format_datetime(task.get('LastRunTime'))
        
        # 各行の列を作成
        col1, col2, col3, col4, col5, col6, col7, col8 = st.columns((1, 1, 2, 1, 1, 1, 0.5, 0.5))
        
        # ステータス表示（一番左）
        current_state = task['State']
        is_enabled = current_state in [3, 4]  # Ready(3) または Running(4)
        
        with col1:
            # ステータス表示（中央寄せ、縦も中央寄せ）
            if is_enabled:
                st.markdown(f"<div style='text-align: center; display: flex; align-items: center; justify-content: center; min-height: 50px; color: #28a745; font-weight: bold;'>{state_info['icon']} {state_info['status']}</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div style='text-align: center; display: flex; align-items: center; justify-content: center; min-height: 50px; color: #dc3545; font-weight: bold;'>{state_info['icon']} {state_info['status']}</div>", unsafe_allow_html=True)
        
        # データを表示（中央寄せ、縦も中央寄せ）
        col2.markdown(f"<div style='text-align: center; display: flex; align-items: center; justify-content: center; min-height: 50px;'><strong>{task['TaskName']}</strong></div>", unsafe_allow_html=True)
        col3.markdown(f"<div style='text-align: center; display: flex; align-items: center; justify-content: center; min-height: 50px;'>{result_info['icon']} {result_info['status']}</div>", unsafe_allow_html=True)
        col4.markdown(f"<div style='text-align: center; display: flex; align-items: center; justify-content: center; min-height: 50px;'>{next_run}</div>", unsafe_allow_html=True)
        col5.markdown(f"<div style='text-align: center; display: flex; align-items: center; justify-content: center; min-height: 50px;'>{last_run}</div>", unsafe_allow_html=True)
        
        # 開始時刻の表示（中央寄せ、縦も中央寄せ）
        trigger_info = format_trigger_info(task.get('Trigger', ''))
        col6.markdown(f"<div style='text-align: center; display: flex; align-items: center; justify-content: center; min-height: 50px;'>{trigger_info}</div>", unsafe_allow_html=True)
        
        # 手動実行ボタン（詳細の左）
        with col7:
            if st.button(f"▶️ ", key=f"run_{title}_{idx}", help="タスクを手動実行", use_container_width=True):
                # 手動実行機能（将来実装）
                st.info("🚧 タスク実行機能は今後実装予定です。")
        
        # 詳細ボタン
        with col8:
            if st.button(f"📋", key=f"detail_{title}_{idx}", help="詳細を表示", use_container_width=True):
                from ui.dialogs import task_detail_dialog
                task_detail_dialog(task.to_dict(), task['PC名'], task['PC_IP'])
    
    # 一括操作セクション
    st.write("---")
    st.subheader("🔧 一括操作")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**一括ステータス変更:**")
        bulk_action = st.selectbox(
            "操作を選択",
            ["操作なし", "選択したタスクを有効にする", "選択したタスクを無効にする"],
            key=f"bulk_action_{title}"
        )
        
        if bulk_action != "操作なし":
            # 現在のページのタスクから選択可能なタスクを取得
            available_tasks = [(task[1]['TaskName'], task[1]['PC名']) for task in current_page_df.iterrows()]
            selected_tasks = st.multiselect(
                "対象タスクを選択",
                options=available_tasks,
                format_func=lambda x: f"{x[1]} - {x[0]}",
                key=f"bulk_tasks_{title}"
            )
            
            if st.button("🚀 一括実行", key=f"bulk_execute_{title}", type="primary"):
                if selected_tasks:
                    success_count = 0
                    error_count = 0
                    
                    for task_name, pc_name in selected_tasks:
                        # PCの認証情報を取得
                        credentials = load_credentials()
                        username, password = get_pc_credentials(credentials, pc_name)
                        if not username or not password:
                            st.error(f"❌ {pc_name}の認証情報が見つかりません。")
                            continue
                        
                        # PCのIPアドレスを取得
                        pc_ip = next((task[1]['PC_IP'] for task in current_page_df.iterrows() 
                                    if task[1]['PC名'] == pc_name and task[1]['TaskName'] == task_name), None)
                        if not pc_ip:
                            st.error(f"❌ {pc_name}のIPアドレスが見つかりません。")
                            continue
                        
                        # PCごとにTaskManagerを初期化
                        pc_task_manager = TaskManager(
                            st.session_state.config_manager, 
                            st.session_state.db_manager, 
                            username, 
                            password
                        )
                        
                        # 新しい状態を決定
                        new_state = "Ready" if "有効" in bulk_action else "Disabled"
                        update_details = {"State": new_state}
                        
                        success, msg = pc_task_manager.update_task(pc_ip, task_name, update_details, user_identifier=os.getlogin())
                        if success:
                            success_count += 1
                        else:
                            error_count += 1
                            st.error(f"❌ {pc_name} - {task_name}: {msg}")
                    
                    if success_count > 0:
                        st.success(f"✅ {success_count}件のタスクを{'有効' if '有効' in bulk_action else '無効'}に変更しました")
                    if error_count > 0:
                        st.error(f"❌ {error_count}件のタスクでエラーが発生しました")
                    
                    if success_count > 0:
                        st.rerun()
                else:
                    st.warning("⚠️ 対象タスクを選択してください")
    
    with col2:
        st.write("**削除アクション:**")
        
        # 削除確認状態の表示
        if st.session_state.get("confirm_delete_task", False):
            st.warning("⚠️ 削除確認モードが有効です。削除ボタンを押すとタスクが削除されます。")
            if st.button("❌ 削除確認をキャンセル", key=f"cancel_delete_{title}"):
                st.session_state["confirm_delete_task"] = False
                st.rerun()
        
        # 削除確認の切り替え
        if not st.session_state.get("confirm_delete_task", False):
            if st.button("🗑️ 削除確認を有効にする", key=f"enable_delete_{title}"):
                st.session_state["confirm_delete_task"] = True
                st.rerun()
    
    # 削除フォーム
    with st.form(f"delete_form_{title}"):
        col1, col2, col3 = st.columns(3)
        with col1:
            pc_name = st.selectbox("PC名", options=[task[1]['PC名'] for task in current_page_df.iterrows()], key=f"delete_pc_{title}")
        with col2:
            task_name = st.selectbox("タスク名", options=[task[1]['TaskName'] for task in current_page_df.iterrows() if task[1]['PC名'] == pc_name], key=f"delete_task_{title}")
        with col3:
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
                        # PCのIPアドレスを取得
                        pc_ip = next((task[1]['PC_IP'] for task in current_page_df.iterrows() if task[1]['PC名'] == pc_name and task[1]['TaskName'] == task_name), None)
                        if pc_ip:
                            success, msg = pc_task_manager.delete_task(pc_ip, task_name, user_identifier=os.getlogin())
                        else:
                            st.error(f"❌ {pc_name}のIPアドレスが見つかりません。")
                            return
                        if success:
                            st.success(f"✅ タスク '{task_name}' を削除しました。")
                            st.session_state["confirm_delete_task"] = False
                            st.rerun()
                        else:
                            st.error(f"❌ タスク削除に失敗しました: {msg}")
                else:
                    st.warning("⚠️ 削除確認を有効にしてから削除してください。") 