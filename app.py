#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
臺灣華德福青年運動聯盟 (TWYA) 行動時間線系統 - Streamlit 雲端版
---------------------------------------------------------------
本系統自動讀取行動資料並生成互動式時間線圖表，供聯盟成員雲端訪問。
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import gspread
from gspread_dataframe import get_as_dataframe
from oauth2client.service_account import ServiceAccountCredentials
import json


# =============================================================================
# 頁面配置
# =============================================================================

st.set_page_config(
    page_title="TWYA 行動時間線",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)


# =============================================================================
# 資料載入函數
# =============================================================================

@st.cache_data(ttl=300)  # 快取 5 分鐘
def load_data_from_google_sheet():
    """從 Google Sheet 讀取資料"""
    try:
        # 從 Streamlit secrets 讀取憑證
        creds_dict = dict(st.secrets["gcp_service_account"])
        
        # 設定 API 範圍
        scope = [
            "https://spreadsheets.google.com/feeds",
            'https://www.googleapis.com/auth/spreadsheets',
            "https://www.googleapis.com/auth/drive.file",
            "https://www.googleapis.com/auth/drive"
        ]
        
        # 使用憑證進行授權
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        
        # 開啟 Google Sheet 並讀取第一個工作表
        sheet_name = st.secrets.get("sheet_name", "TWYA 行動時間線資料")
        sheet = client.open(sheet_name).sheet1
        
        # 將工作表轉換為 DataFrame
        df = get_as_dataframe(sheet)
        
        # 移除所有欄位均為 NaN 的列
        df.dropna(how='all', inplace=True)
        
        # 將中文欄位映射到英文欄位
        column_mapping = {
            '負責組別': 'Team',
            '任務名稱': 'EventName',
            '性質': 'Level',
            '開始日期': 'StartDate',
            '開始時間': 'StartTime',
            '結束日期': 'EndDate',
            '結束時間': 'EndTime',
            '狀態': 'Status',
            '備註': 'Notes'
        }
        
        rename_dict = {k: v for k, v in column_mapping.items() if k in df.columns}
        df = df.rename(columns=rename_dict)
        
        return df, None
        
    except Exception as e:
        return None, str(e)


def clean_and_validate_data(df):
    """清理並驗證資料"""
    df_clean = df.copy()
    
    # 補充選填欄位
    optional_columns = {
        'Level': 'B-專案執行',
        'Status': 'WIP',
        'Notes': '',
        'StartTime': '',
        'EndTime': ''
    }
    
    for col, default_value in optional_columns.items():
        if col not in df_clean.columns:
            df_clean[col] = default_value
    
    # 填補空值
    df_clean['Level'] = df_clean['Level'].fillna('B-專案執行')
    df_clean['Status'] = df_clean['Status'].fillna('WIP')
    df_clean['Notes'] = df_clean['Notes'].fillna('')
    df_clean['StartTime'] = df_clean['StartTime'].fillna('')
    df_clean['EndTime'] = df_clean['EndTime'].fillna('')
    
    # 轉換日期格式
    for col in ['StartDate', 'EndDate']:
        df_clean[col] = pd.to_datetime(df_clean[col], errors='coerce')
    
    # 移除日期不完整的紀錄
    df_clean = df_clean.dropna(subset=['StartDate', 'EndDate'])
    
    # 確保結束日期不早於開始日期
    mask = df_clean['EndDate'] < df_clean['StartDate']
    if mask.any():
        df_clean.loc[mask, ['StartDate', 'EndDate']] = \
            df_clean.loc[mask, ['EndDate', 'StartDate']].values
    
    # 排序
    df_clean = df_clean.sort_values(['Team', 'StartDate'], ascending=[True, True])
    df_clean = df_clean.reset_index(drop=True)
    
    return df_clean


# =============================================================================
# 視覺化函數
# =============================================================================

def get_team_color_mapping(teams):
    """為不同團隊分配顏色"""
    default_colors = {
        '行政組': '#FF6B6B',
        '活動組': '#4ECDC4',
        '公關組': '#FFE66D',
        '財務組': '#95E1D3',
        '教育組': '#A8E6CF',
        '資訊組': '#667BC6',
        '企劃組': '#FDA7DF',
        '研發組': '#C6A5FC',
    }
    
    plotly_colors = [
        '#636EFA', '#EF553B', '#00CC96', '#AB63FA', '#FFA15A',
        '#19D3F3', '#FF6692', '#B6E880', '#FF97FF', '#FECB52'
    ]
    
    color_mapping = {}
    for i, team in enumerate(sorted(teams.unique())):
        if team in default_colors:
            color_mapping[team] = default_colors[team]
        else:
            color_mapping[team] = plotly_colors[i % len(plotly_colors)]
    
    return color_mapping


def get_status_marker(status):
    """根據狀態返回標記符號"""
    status_markers = {
        'Done': '✓',
        'WIP': '⟳',
        'Todo': '○',
        'Blocked': '⊗',
        'Pending': '⏸'
    }
    return status_markers.get(status, '')


def create_timeline_chart(df, selected_teams=None, selected_status=None):
    """生成互動式時間線圖表"""
    # 篩選資料
    df_filtered = df.copy()
    if selected_teams:
        df_filtered = df_filtered[df_filtered['Team'].isin(selected_teams)]
    if selected_status:
        df_filtered = df_filtered[df_filtered['Status'].isin(selected_status)]
    
    if df_filtered.empty:
        return None
    
    # 獲取團隊配色
    color_mapping = get_team_color_mapping(df['Team'])
    
    # 建立圖表
    fig = go.Figure()
    
    # 為每個事件添加時間線條
    for idx, row in df_filtered.iterrows():
        start_display = row['StartDate'].strftime('%Y-%m-%d')
        if row.get('StartTime') and str(row['StartTime']).strip():
            start_display += f" {row['StartTime']}"
        
        end_display = row['EndDate'].strftime('%Y-%m-%d')
        if row.get('EndTime') and str(row['EndTime']).strip():
            end_display += f" {row['EndTime']}"
        
        hover_text = (
            f"<b>{row['EventName']}</b><br>"
            f"負責組別：{row['Team']}<br>"
            f"性質：{row['Level']}<br>"
            f"狀態：{row['Status']}<br>"
            f"開始：{start_display}<br>"
            f"結束：{end_display}<br>"
            f"備註：{row['Notes'] if row['Notes'] else '無'}"
        )
        
        status_marker = get_status_marker(row['Status'])
        display_text = f"{status_marker} {row['EventName']}" if status_marker else row['EventName']
        
        fig.add_trace(go.Scatter(
            x=[row['StartDate'], row['EndDate']],
            y=[idx, idx],
            mode='lines+markers+text',
            name=row['Team'],
            line=dict(color=color_mapping[row['Team']], width=8),
            marker=dict(size=10, symbol='circle', color=color_mapping[row['Team']]),
            text=[display_text, ''],
            textposition='middle right',
            textfont=dict(size=10),
            hovertemplate=hover_text + '<extra></extra>',
            showlegend=False
        ))
    
    # 添加團隊圖例
    added_teams = set()
    for team in df_filtered['Team'].unique():
        if team not in added_teams:
            fig.add_trace(go.Scatter(
                x=[None], y=[None],
                mode='markers',
                name=team,
                marker=dict(size=12, color=color_mapping[team], symbol='square'),
                showlegend=True
            ))
            added_teams.add(team)
    
    # 設定圖表佈局
    fig.update_layout(
        title={
            'text': '臺灣華德福青年運動聯盟行動時間線<br><sub>Taiwan Waldorf Youth Alliance Timeline</sub>',
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 24, 'color': '#2C3E50'}
        },
        xaxis=dict(title='時間軸', showgrid=True, gridcolor='#E8E8E8', type='date'),
        yaxis=dict(title='行動項目', showticklabels=False, showgrid=True, gridcolor='#E8E8E8'),
        hovermode='closest',
        plot_bgcolor='#FAFAFA',
        paper_bgcolor='white',
        height=max(600, len(df_filtered) * 40),
        margin=dict(l=100, r=300, t=100, b=80),
        legend=dict(
            title=dict(text='團隊分組', font=dict(size=14, color='#2C3E50')),
            orientation='v',
            yanchor='top', y=1,
            xanchor='left', x=1.02,
            bgcolor='rgba(255,255,255,0.8)',
            bordercolor='#CCCCCC',
            borderwidth=1
        )
    )
    
    return fig


# =============================================================================
# 主應用程式
# =============================================================================

def main():
    # 標題
    st.title("📊 臺灣華德福青年運動聯盟行動時間線")
    st.markdown("### Taiwan Waldorf Youth Alliance Timeline")
    
    # 側邊欄
    with st.sidebar:
        st.header("⚙️ 設定")
        
        # 重新整理按鈕
        if st.button("🔄 重新載入資料", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        
        st.markdown("---")
        
        st.markdown("""
        ### 📖 使用說明
        - 資料每 5 分鐘自動更新
        - 可使用篩選器查看特定團隊或狀態
        - 懸停在時間線上查看詳細資訊
        - 使用滑鼠滾輪縮放時間軸
        
        ### 📊 狀態圖示說明
        - ✓ Done: 已完成
        - ⟳ WIP: 進行中
        - ○ Todo: 待執行
        - ⊗ Blocked: 受阻
        - ⏸ Pending: 待定
        """)
        
        st.markdown("---")
        st.markdown(f"**更新時間**: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    
    # 載入資料
    with st.spinner("正在載入資料..."):
        df, error = load_data_from_google_sheet()
    
    if error:
        st.error(f"❌ 無法載入資料：{error}")
        st.info("請確認 Streamlit Secrets 已正確設定 Google Service Account 憑證")
        return
    
    if df is None or df.empty:
        st.warning("⚠️ 沒有可用的資料")
        return
    
    # 清理資料
    df_clean = clean_and_validate_data(df)
    
    if df_clean.empty:
        st.warning("⚠️ 清理後沒有有效資料")
        return
    
    # 顯示統計資訊
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("總項目數", len(df_clean))
    with col2:
        st.metric("團隊數量", df_clean['Team'].nunique())
    with col3:
        done_count = len(df_clean[df_clean['Status'] == 'Done'])
        st.metric("已完成", done_count)
    with col4:
        wip_count = len(df_clean[df_clean['Status'] == 'WIP'])
        st.metric("進行中", wip_count)
    
    st.markdown("---")
    
    # 篩選器
    col1, col2 = st.columns(2)
    
    with col1:
        all_teams = sorted(df_clean['Team'].unique())
        selected_teams = st.multiselect(
            "選擇團隊",
            options=all_teams,
            default=all_teams,
            help="可選擇多個團隊"
        )
    
    with col2:
        all_status = sorted(df_clean['Status'].unique())
        selected_status = st.multiselect(
            "選擇狀態",
            options=all_status,
            default=all_status,
            help="可選擇多個狀態"
        )
    
    # 生成並顯示圖表
    with st.spinner("正在生成時間線..."):
        fig = create_timeline_chart(df_clean, selected_teams, selected_status)
    
    if fig is None:
        st.warning("⚠️ 沒有符合篩選條件的資料")
        return
    
    st.plotly_chart(fig, use_container_width=True)
    
    # 顯示資料表
    with st.expander("📋 查看原始資料"):
        display_df = df_clean.copy()
        if selected_teams:
            display_df = display_df[display_df['Team'].isin(selected_teams)]
        if selected_status:
            display_df = display_df[display_df['Status'].isin(selected_status)]
        
        st.dataframe(
            display_df[['Team', 'EventName', 'Level', 'Status', 'StartDate', 'EndDate', 'Notes']],
            use_container_width=True
        )


if __name__ == "__main__":
    main()
