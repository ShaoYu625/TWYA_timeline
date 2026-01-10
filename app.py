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
import base64
from pathlib import Path


# =============================================================================
# 頁面配置
# =============================================================================

# =============================================================================
# 頁面配置
# =============================================================================

# 設置 favicon 和自定義樣式
def setup_page_config():
    """設置頁面配置、favicon 和自定義樣式"""
    st.set_page_config(
        page_title="TWYA 行動時間線",
        page_icon="./logo/logo.png",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # 嘗試讀取 logo 並轉為 base64 作為 favicon
    try:
        logo_path = Path("./logo/logo.png")
        if logo_path.exists():
            with open(logo_path, "rb") as f:
                logo_data = base64.b64encode(f.read()).decode()
            
            # 注入自定義 HTML 頭部來設置 favicon
            favicon_html = f"""
            <head>
                <link rel="icon" type="image/png" href="data:image/png;base64,{logo_data}">
                <link rel="shortcut icon" type="image/png" href="data:image/png;base64,{logo_data}">
            </head>
            """
            st.markdown(favicon_html, unsafe_allow_html=True)
    except Exception as e:
        pass  # 如果無法讀取 logo，使用默認 favicon
    
    # 自定義 CSS 樣式（使用聯盟 logo 配色）
    custom_css = """
    <style>
        /* 主要配色：品牌藍 #175BA6、品牌黃 #E9E13B */
        
        /* 側邊欄樣式 */
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #175BA6 0%, #124785 100%);
            box-shadow: 2px 0 10px rgba(23, 91, 166, 0.2);
        }
        
        [data-testid="stSidebar"] h1, 
        [data-testid="stSidebar"] h2, 
        [data-testid="stSidebar"] h3,
        [data-testid="stSidebar"] p,
        [data-testid="stSidebar"] label {
            color: white !important;
        }
        
        /* 側邊欄分隔線 */
        [data-testid="stSidebar"] hr {
            border-color: rgba(233, 225, 59, 0.4);
            border-width: 1px;
        }
        
        /* 按鈕樣式 */
        .stButton > button {
            background-color: #E9E13B;
            color: #2C2C2C;
            border: none;
            font-weight: bold;
            transition: all 0.3s ease;
            border-radius: 8px;
            padding: 0.5rem 2rem;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }
        
        .stButton > button:hover {
            background-color: #D4CA35;
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
        }
        
        /* 標題樣式 */
        h1 {
            color: #175BA6 !important;
            font-weight: 700;
        }
        
        h2, h3 {
            color: #2C2C2C !important;
        }
        
        /* Metric 卡片樣式 */
        [data-testid="stMetricValue"] {
            color: #175BA6 !important;
            font-weight: bold;
            font-size: 2rem;
        }
        
        [data-testid="stMetricLabel"] {
            color: #5A5A5A !important;
            font-weight: 500;
        }
        
        /* 分隔線樣式 */
        hr {
            border-color: rgba(233, 225, 59, 0.3);
            border-width: 2px;
            margin: 1.5rem 0;
        }
        
        /* 多選框樣式 */
        .stMultiSelect [data-baseweb="tag"] {
            background-color: #175BA6;
            color: white;
        }
        
        .stMultiSelect [data-baseweb="tag"] span[role="button"] {
            color: white;
        }
        
        /* 擴展區塊樣式 */
        .streamlit-expanderHeader {
            background-color: rgba(233, 225, 59, 0.15);
            color: #2C2C2C;
            font-weight: bold;
            border-left: 4px solid #175BA6;
            border-radius: 4px;
        }
        
        .streamlit-expanderHeader:hover {
            background-color: rgba(233, 225, 59, 0.25);
        }
        
        /* 主內容區背景 */
        .main {
            background-color: #FAFAFA;
        }
        
        /* 卡片樣式優化 */
        [data-testid="stMetric"] {
            background-color: white;
            padding: 1rem;
            border-radius: 8px;
            border-left: 4px solid #175BA6;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
        }
        
        /* Spinner 樣式 */
        .stSpinner > div {
            border-top-color: #E9E13B !important;
        }
    </style>
    """
    st.markdown(custom_css, unsafe_allow_html=True)

setup_page_config()


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
    """為不同團隊分配顏色（使用聯盟 logo 色系）"""
    # 主色系：品牌藍 #175BA6、品牌黃 #E9E13B
    default_colors = {
        '行政組': '#175BA6',  # 品牌藍
        '活動組': '#E9E13B',  # 品牌黃
        '公關組': '#2A7FC1',  # 亮藍
        '財務組': '#D4CA35',  # 橄欖金
        '教育組': '#124785',  # 深藍
        '資訊組': '#3D93D2',  # 天藍
        '企劃組': '#F4E96D',  # 淺黃
        '研發組': '#0E3A5F',  # 墨藍
    }
    
    # 使用 logo 色系的擴展配色（藍色和黃色系列）
    plotly_colors = [
        '#175BA6',  # 品牌藍
        '#E9E13B',  # 品牌黃
        '#2A7FC1',  # 亮藍
        '#D4CA35',  # 橄欖金
        '#124785',  # 深藍
        '#F4E96D',  # 淺黃
        '#3D93D2',  # 天藍
        '#C5BC33',  # 深金
        '#0E3A5F',  # 墨藍
        '#FFF8B3',  # 奶油黃
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
    
    # 設定圖表佈局（使用聯盟 logo 配色）
    fig.update_layout(
        title={
            'text': '臺灣華德福青年運動聯盟行動時間線<br><sub>Taiwan Waldorf Youth Alliance Timeline</sub>',
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 24, 'color': '#175BA6', 'family': 'Arial, sans-serif'}  # 品牌藍標題
        },
        xaxis=dict(
            title=dict(text='時間軸', font=dict(color='#2C2C2C', size=14)),
            showgrid=True, 
            gridcolor='rgba(23, 91, 166, 0.1)',  # 淡藍色網格
            type='date',
            zeroline=False
        ),
        yaxis=dict(
            title=dict(text='行動項目', font=dict(color='#2C2C2C', size=14)),
            showticklabels=False, 
            showgrid=True, 
            gridcolor='rgba(233, 225, 59, 0.1)',  # 淡黃色網格
            zeroline=False
        ),
        hovermode='closest',
        plot_bgcolor='#FDFDF8',  # 極淺的暖白色背景
        paper_bgcolor='white',
        height=max(600, len(df_filtered) * 40),
        margin=dict(l=100, r=300, t=100, b=80),
        legend=dict(
            title=dict(text='團隊分組', font=dict(size=14, color='#175BA6', weight='bold')),  # 品牌藍圖例標題
            orientation='v',
            yanchor='top', y=1,
            xanchor='left', x=1.02,
            bgcolor='rgba(255,255,255,0.95)',
            bordercolor='#175BA6',  # 品牌藍邊框
            borderwidth=2,
            font=dict(color='#2C2C2C')
        )
    )
    
    return fig


# =============================================================================
# 主應用程式
# =============================================================================

def main():
    # 在頁面頂部顯示 logo 和標題
    col1, col2 = st.columns([1, 4])
    with col1:
        logo_path = Path("./logo/logo.png")
        if logo_path.exists():
            st.image(str(logo_path), width=150)
        else:
            # 如果找不到 logo，顯示佔位符
            st.markdown("""<div style='width:150px;height:150px;background:linear-gradient(135deg, #175BA6 0%, #124785 100%);border-radius:10px;display:flex;align-items:center;justify-content:center;box-shadow:0 4px 8px rgba(23,91,166,0.3);'><span style='color:#E9E13B;font-size:28px;font-weight:bold;text-shadow:1px 1px 2px rgba(0,0,0,0.3);'>TWYA</span></div>""", unsafe_allow_html=True)
    with col2:
        st.title("臺灣華德福青年運動聯盟行動時間線")
        st.markdown("### Taiwan Waldorf Youth Alliance Timeline")
    
    st.markdown("---")
    
    # 側邊欄
    with st.sidebar:
        st.header("⚙️ 設定")
        
        # 重新整理按鈕
        if st.button("🔄 重新載入資料", width="stretch"):
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
    
    st.plotly_chart(fig, width="stretch")
    
    # 顯示資料表
    with st.expander("📋 查看原始資料"):
        display_df = df_clean.copy()
        if selected_teams:
            display_df = display_df[display_df['Team'].isin(selected_teams)]
        if selected_status:
            display_df = display_df[display_df['Status'].isin(selected_status)]
        
        st.dataframe(
            display_df[['Team', 'EventName', 'Level', 'Status', 'StartDate', 'EndDate', 'Notes']],
            width="stretch"
        )


if __name__ == "__main__":
    main()
