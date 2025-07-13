# ==============================================================================
# 管理者設定画面のレンダリング関数
# ==============================================================================

import streamlit as st
import pandas as pd

def render_admin_settings():
    st.header("管理者設定")
    password = st.text_input("管理者パスワードを入力してください", type="password")
    if password != "admin": st.warning("パスワードが違います。"); st.stop()
    st.success("認証成功")
    
    # タブの作成
    tab1, tab2, tab3 = st.tabs(["PC設定", "通知設定", "エラーコード管理"])
    
    with tab1:
        config_manager = st.session_state.config_manager
        config_data = config_manager.get_config()
        with st.form("admin_settings_form"):
            st.subheader("管理対象PC設定")
            edited_pcs = st.data_editor(pd.DataFrame(config_data.get('pcs', [])), num_rows="dynamic", use_container_width=True)
            
            st.subheader("PCグループ設定")
            edited_pc_groups = st.data_editor(pd.DataFrame(config_data.get('pc_groups', [])), num_rows="dynamic", use_container_width=True)
            
            submitted = st.form_submit_button("設定を保存")
            if submitted:
                config_data['pcs'] = edited_pcs.to_dict('records')
                config_data['pc_groups'] = edited_pc_groups.to_dict('records')
                config_manager.update_config(config_data)
                st.success("設定を保存しました。")
    
    with tab2:
        config_data = config_manager.get_config()
        with st.form("notification_settings_form"):
            st.subheader("通知設定")
            notification_enabled = st.checkbox("Google Chat通知を有効にする", value=config_data['notification']['enabled'])
            webhook_url = st.text_input("Webhook URL", value=config_data['notification']['google_chat_webhook_url'])
            submitted = st.form_submit_button("通知設定を保存")
            if submitted:
                config_data['notification']['enabled'] = notification_enabled
                config_data['notification']['google_chat_webhook_url'] = webhook_url
                config_manager.update_config(config_data)
                st.success("通知設定を保存しました。")
    
    with tab3:
        st.subheader("エラーコード管理")
        
        # 現在のエラーコード一覧を表示
        st.write("**現在のエラーコード一覧:**")
        error_manager = st.session_state.error_manager
        error_codes_df = pd.DataFrame([
            {"エラーコード": code, "説明": message}
            for code, message in error_manager.error_codes.items()
        ])
        st.dataframe(error_codes_df, use_container_width=True)
        
        # 新しいエラーコードの追加
        with st.form("add_error_code_form"):
            st.write("**新しいエラーコードを追加:**")
            col1, col2 = st.columns(2)
            with col1:
                new_error_code = st.text_input("エラーコード", placeholder="例: 0x00041306 または 124")
            with col2:
                new_error_message = st.text_input("エラーメッセージ", placeholder="例: タスクがタイムアウトにより停止されました")
            
            is_timeout_error = st.checkbox("タイムアウトエラーとして登録")
            
            if st.form_submit_button("エラーコードを追加"):
                if new_error_code and new_error_message:
                    error_manager.add_error_code(new_error_code, new_error_message)
                    if is_timeout_error:
                        # タイムアウトエラーコードに追加
                        if new_error_code.startswith('0x'):
                            try:
                                decimal_code = int(new_error_code, 16)
                                error_manager.timeout_error_codes.append(decimal_code)
                            except ValueError:
                                st.error("無効な16進数コードです")
                        else:
                            try:
                                decimal_code = int(new_error_code)
                                error_manager.timeout_error_codes.append(decimal_code)
                            except ValueError:
                                st.error("無効なエラーコードです")
                    
                    error_manager.save_error_codes()
                    st.success("エラーコードを追加しました")
                    st.rerun()
                else:
                    st.warning("エラーコードとメッセージを入力してください")
        
        # 設定の再読み込み
        if st.button("設定を再読み込み"):
            error_manager.reload_error_codes()
            st.success("エラーコード設定を再読み込みしました") 