# ==============================================================================
# 実行結果ログ画面のレンダリング関数
# ==============================================================================

import streamlit as st
import pandas as pd
import datetime
import os
import json
import logging

def render_logs():
    st.header("実行結果ログ")
    
    # 検索条件の設定
    with st.expander("🔍 ログ検索・フィルター", expanded=True):
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            # PC名の選択（ドロップダウン）
            config_manager = st.session_state.config_manager
            config = config_manager.get_config()
            pc_list = [pc['name'] for pc in config.get('pcs', [])]
            pc_list.insert(0, "全てのPC")
            selected_pc = st.selectbox("PC名", options=pc_list, key="log_pc_filter")
            pc_name = None if selected_pc == "全てのPC" else selected_pc
        
        with col2:
            # タスク名の入力
            task_name = st.text_input("タスク名", placeholder="タスク名で絞り込み", key="log_task_filter")
        
        with col3:
            # 結果コードでの絞り込み
            result_filter = st.selectbox(
                "実行結果", 
                ["全て", "成功", "エラー"], 
                key="log_result_filter"
            )
        
        with col4:
            # エラーコードでの絞り込み
            error_code = st.text_input("エラーコード", placeholder="例: 0x00041306", key="log_error_filter")
        
        # 期間指定
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("期間 (開始)", value=None, key="log_start_date")
        with col2:
            end_date = st.date_input("期間 (終了)", value=None, key="log_end_date")
        
        # 検索ボタン
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            if st.button("🔍 検索", type="primary", use_container_width=True):
                # 検索条件を構築
                search_params = {}
                if pc_name:
                    search_params['pc_name'] = pc_name
                if task_name:
                    search_params['task_name'] = task_name
                if start_date:
                    search_params['start_date'] = start_date
                if end_date:
                    search_params['end_date'] = end_date
                
                # 結果コードの変換
                if result_filter == "成功":
                    search_params['result_code'] = 0
                elif result_filter == "エラー":
                    search_params['result_code_not'] = 0
                
                # エラーコード指定
                if error_code:
                    search_params['error_code'] = error_code
                
                st.session_state.log_search_results = st.session_state.db_manager.search_execution_logs(**search_params)
                st.session_state.log_search_params = search_params
                st.rerun()
        
        with col2:
            if st.button("🔄 リセット", use_container_width=True):
                st.session_state.log_search_results = None
                st.session_state.log_search_params = None
                st.rerun()
    
    # 検索結果の表示
    if 'log_search_results' in st.session_state and st.session_state.log_search_results:
        logs = st.session_state.log_search_results
        df = pd.DataFrame(logs)
        
        # 統計情報の表示
        st.subheader("📊 検索結果統計")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_count = len(df)
            st.metric("総ログ数", total_count)
        
        with col2:
            success_count = len(df[df['result_code'] == 0]) if 'result_code' in df.columns else 0
            st.metric("成功", success_count, delta=f"{success_count - (total_count - success_count)}")
        
        with col3:
            error_count = total_count - success_count
            st.metric("エラー", error_count, delta=f"-{error_count}" if error_count > 0 else None)
        
        with col4:
            pc_count = df['pc_name'].nunique() if 'pc_name' in df.columns else 0
            st.metric("対象PC数", pc_count)
        
        st.write("---")
        
        # エクスポート機能
        col1, col2 = st.columns([1, 3])
        with col1:
            # CSVデータを生成
            csv_data = df.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                label="📥 CSVエクスポート",
                data=csv_data,
                file_name=f"execution_logs_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        with col2:
            st.write(f"**検索条件:** {st.session_state.get('log_search_params', {})}")
        
        # ページネーション
        items_per_page = 50
        if 'log_current_page' not in st.session_state:
            st.session_state.log_current_page = 0
        
        total_pages = (len(df) - 1) // items_per_page + 1
        start_idx = st.session_state.log_current_page * items_per_page
        end_idx = min(start_idx + items_per_page, len(df))
        
        # ページネーションコントロール
        col1, col2, col3 = st.columns([1, 2, 1])
        with col1:
            if st.button("← 前のページ", disabled=st.session_state.log_current_page == 0, key="log_prev_page"):
                st.session_state.log_current_page = max(0, st.session_state.log_current_page - 1)
                st.rerun()
        with col2:
            st.write(f"ページ {st.session_state.log_current_page + 1} / {total_pages} ({start_idx + 1}-{end_idx} / {len(df)}件)")
        with col3:
            if st.button("次のページ →", disabled=st.session_state.log_current_page >= total_pages - 1, key="log_next_page"):
                st.session_state.log_current_page = min(total_pages - 1, st.session_state.log_current_page + 1)
                st.rerun()
        
        # 現在のページのログを表示
        current_page_df = df.iloc[start_idx:end_idx]
        
        # ログテーブルの表示
        st.subheader("📋 実行ログ詳細")
        
        # テーブルヘッダー
        col1, col2, col3, col4, col5, col6, col7 = st.columns((1, 1, 1, 1, 1, 1, 0.5))
        col1.markdown("<div style='text-align: center; background: #3498db; color: white; padding: 8px; border-radius: 4px; font-weight: bold;'><strong>実行日時</strong></div>", unsafe_allow_html=True)
        col2.markdown("<div style='text-align: center; background: #3498db; color: white; padding: 8px; border-radius: 4px; font-weight: bold;'><strong>PC名</strong></div>", unsafe_allow_html=True)
        col3.markdown("<div style='text-align: center; background: #3498db; color: white; padding: 8px; border-radius: 4px; font-weight: bold;'><strong>タスク名</strong></div>", unsafe_allow_html=True)
        col4.markdown("<div style='text-align: center; background: #3498db; color: white; padding: 8px; border-radius: 4px; font-weight: bold;'><strong>結果</strong></div>", unsafe_allow_html=True)
        col5.markdown("<div style='text-align: center; background: #3498db; color: white; padding: 8px; border-radius: 4px; font-weight: bold;'><strong>エラーコード</strong></div>", unsafe_allow_html=True)
        col6.markdown("<div style='text-align: center; background: #3498db; color: white; padding: 8px; border-radius: 4px; font-weight: bold;'><strong>AI分析</strong></div>", unsafe_allow_html=True)
        col7.markdown("<div style='text-align: center; background: #3498db; color: white; padding: 8px; border-radius: 4px; font-weight: bold;'><strong>詳細</strong></div>", unsafe_allow_html=True)
        
        # ヘッダーとボディの間にマージンを追加
        st.markdown("<div style='margin: 10px 0;'></div>", unsafe_allow_html=True)
        
        # ログ行の表示
        for idx, log in current_page_df.iterrows():
            # 結果コードに応じた表示
            result_code = log.get('result_code', 0)
            is_success = result_code == 0
            
            # エラーコードの詳細情報を取得
            error_info = get_log_error_info(result_code)
            
            # 日時フォーマット
            from utils.task_helpers import format_datetime
            recorded_at = format_datetime(log.get('recorded_at'))
            
            # 各行の列を作成
            col1, col2, col3, col4, col5, col6, col7 = st.columns((1, 1, 1, 1, 1, 1, 0.5))
            
            # 実行日時
            col1.markdown(f"<div style='text-align: center; padding: 8px;'>{recorded_at}</div>", unsafe_allow_html=True)
            
            # PC名
            col2.markdown(f"<div style='text-align: center; padding: 8px;'><strong>{log.get('pc_name', 'Unknown')}</strong></div>", unsafe_allow_html=True)
            
            # タスク名
            col3.markdown(f"<div style='text-align: center; padding: 8px;'>{log.get('task_name', 'Unknown')}</div>", unsafe_allow_html=True)
            
            # 結果
            if is_success:
                col4.markdown(f"<div style='text-align: center; padding: 8px; color: #28a745; font-weight: bold;'>✅ 成功</div>", unsafe_allow_html=True)
            else:
                col4.markdown(f"<div style='text-align: center; padding: 8px; color: #dc3545; font-weight: bold;'>❌ エラー</div>", unsafe_allow_html=True)
            
            # エラーコード
            if is_success:
                col5.markdown(f"<div style='text-align: center; padding: 8px;'>-</div>", unsafe_allow_html=True)
            else:
                error_display = f"{result_code} ({error_info['code']})" if error_info['code'] else str(result_code)
                col5.markdown(f"<div style='text-align: center; padding: 8px; color: #dc3545;'>{error_display}</div>", unsafe_allow_html=True)
            
            # AI分析
            ai_analysis = log.get('ai_analysis', '')
            if ai_analysis:
                col6.markdown(f"<div style='text-align: center; padding: 8px;'>🤖 あり</div>", unsafe_allow_html=True)
            else:
                col6.markdown(f"<div style='text-align: center; padding: 8px;'>-</div>", unsafe_allow_html=True)
            
            # 詳細ボタン
            with col7:
                if st.button(f"📋", key=f"log_detail_{idx}", help="詳細を表示", use_container_width=True):
                    show_log_detail_dialog(log.to_dict())
        
        # エラー詳細の表示（エラーがある場合）
        error_logs = current_page_df[current_page_df['result_code'] != 0]
        if not error_logs.empty:
            st.write("---")
            st.subheader("⚠️ エラー詳細")
            
            for idx, error_log in error_logs.iterrows():
                result_code = error_log.get('result_code', 0)
                error_info = get_log_error_info(result_code)
                
                with st.expander(f"❌ {error_log.get('task_name', 'Unknown')} - {error_log.get('pc_name', 'Unknown')} ({result_code})", expanded=False):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write("**エラー情報:**")
                        st.write(f"**エラーコード:** {result_code}")
                        if error_info['code']:
                            st.write(f"**コード:** {error_info['code']}")
                        st.write(f"**説明:** {error_info['message']}")
                        if error_info['is_timeout']:
                            st.warning("⚠️ タイムアウトエラーです")
                    
                    with col2:
                        st.write("**実行情報:**")
                        st.write(f"**実行日時:** {format_datetime(error_log.get('recorded_at'))}")
                        st.write(f"**PC名:** {error_log.get('pc_name', 'Unknown')}")
                        st.write(f"**タスク名:** {error_log.get('task_name', 'Unknown')}")
                        if error_log.get('result_message'):
                            st.write(f"**メッセージ:** {error_log.get('result_message')}")
                    
                    # AI分析結果の表示
                    ai_analysis = error_log.get('ai_analysis', '')
                    if ai_analysis:
                        st.write("---")
                        st.write("**🤖 AI分析結果:**")
                        st.info(ai_analysis)
    
    elif 'log_search_results' in st.session_state:
        st.info("検索条件に一致するログが見つかりませんでした。")
    else:
        st.info("検索条件を設定して「検索」ボタンを押してください。")

def get_log_error_info(result_code):
    """ログのエラーコードから詳細情報を取得する"""
    try:
        result_code_int = int(result_code)
        error_manager = st.session_state.error_manager
        error_message = error_manager.get_error_message(result_code_int)
        is_timeout = error_manager.is_timeout_error(result_code_int)
        
        return {
            'code': f"0x{result_code_int:08X}" if result_code_int != 0 else None,
            'message': error_message,
            'is_timeout': is_timeout
        }
    except (ValueError, TypeError):
        return {
            'code': None,
            'message': f"不明なエラーコード: {result_code}",
            'is_timeout': False
        }

@st.dialog("ログ詳細")
def show_log_detail_dialog(log_data):
    """ログの詳細情報を表示するダイアログ"""
    st.subheader("📋 ログ詳細情報")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**基本情報:**")
        from utils.task_helpers import format_datetime
        st.write(f"**実行日時:** {format_datetime(log_data.get('recorded_at'))}")
        st.write(f"**PC名:** {log_data.get('pc_name', 'Unknown')}")
        st.write(f"**タスク名:** {log_data.get('task_name', 'Unknown')}")
        st.write(f"**タスクパス:** {log_data.get('task_path', 'Unknown')}")
    
    with col2:
        st.write("**実行結果:**")
        result_code = log_data.get('result_code', 0)
        is_success = result_code == 0
        
        if is_success:
            st.success(f"✅ 成功 (コード: {result_code})")
        else:
            st.error(f"❌ エラー (コード: {result_code})")
            error_info = get_log_error_info(result_code)
            st.write(f"**エラー説明:** {error_info['message']}")
            if error_info['is_timeout']:
                st.warning("⚠️ タイムアウトエラーです")
    
    # メッセージの表示
    if log_data.get('result_message'):
        st.write("---")
        st.write("**実行メッセージ:**")
        st.code(log_data.get('result_message'), language="text")
    
    # AI分析結果の表示
    ai_analysis = log_data.get('ai_analysis', '')
    if ai_analysis:
        st.write("---")
        st.write("**🤖 AI分析結果:**")
        st.info(ai_analysis)
    
    # エラーコードの詳細説明（エラーの場合）
    if not is_success:
        st.write("---")
        st.write("**🔧 対処法:**")
        error_info = get_log_error_info(result_code)
        
        if error_info['is_timeout']:
            timeout_solutions = st.session_state.error_manager.get_timeout_solutions()
            st.write(f"**{timeout_solutions['title']}:**")
            for i, step in enumerate(timeout_solutions['steps'], 1):
                st.write(f"{i}. **{step['title']}**")
                st.write(f"   {step['description']}")
                st.write("")
        else:
            st.write("一般的な対処法:")
            st.write("1. **タスクの設定を確認** - 実行パスや引数が正しいか確認")
            st.write("2. **権限を確認** - 実行ユーザーに適切な権限があるか確認")
            st.write("3. **依存関係を確認** - 必要なファイルやサービスが利用可能か確認")
            st.write("4. **ログを確認** - 詳細なエラーログを確認") 