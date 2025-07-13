# ==============================================================================
# レポート画面のレンダリング関数
# ==============================================================================

import streamlit as st
import pandas as pd
import plotly.express as px

def render_reports():
    st.header("サマリーレポート")
    db_manager = st.session_state.db_manager
    logs = db_manager.search_execution_logs()
    if not logs:
        st.warning("分析対象のログデータがありません。")
        return
    df = pd.DataFrame(logs)
    df['result_code'] = pd.to_numeric(df['result_code'], errors='coerce')
    df['recorded_at'] = pd.to_datetime(df['recorded_at'], errors='coerce')
    st.subheader("タスク実行状況")
    col1, col2 = st.columns(2)
    with col1:
        status_counts = df['result_code'].apply(lambda x: '成功' if x == 0 else '失敗').value_counts()
        fig_pie = px.pie(status_counts, values=status_counts.values, names=status_counts.index, title='タスク成功率', color=status_counts.index, color_discrete_map={'成功':'#2ca02c', '失敗':'#d62728'})
        st.plotly_chart(fig_pie, use_container_width=True)
    with col2:
        df_errors = df[df['result_code'] != 0].copy()
        df_errors['date'] = df_errors['recorded_at'].dt.date
        error_counts_by_day = df_errors.groupby('date').size().reset_index(name='counts')
        fig_bar = px.bar(error_counts_by_day, x='date', y='counts', title='日別エラー発生件数', labels={'date': '日付', 'counts': 'エラー数'})
        st.plotly_chart(fig_bar, use_container_width=True) 