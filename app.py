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
import json
import base64
from pathlib import Path
import os

# 移除不再需要的 SSL 相關導入
# import ssl
# import certifi
# import httplib2
# import urllib3
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
        initial_sidebar_state="collapsed"  # 默認收起側邊欄，給時間線更多空間
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
    
    # 自定義 CSS 樣式(使用聯盟 logo 配色)
    custom_css = """
    <style>
        /* 主要配色:品牌藍 #175BA6、品牌黃 #E9E13B */
        /* 強制使用淺色主題,覆蓋所有暗色設定 */
        
        /* 強制設定整體背景為白色 */
        .stApp {
            background-color: #FFFFFF !important;
        }
        
        /* 強制主內容區背景為白色 */
        .main .block-container {
            background-color: #FFFFFF !important;
        }
        
        /* 側邊欄樣式 */
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #175BA6 0%, #124785 100%) !important;
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
        
        /* ============================================
           側邊欄 Expander 樣式優化 - 高對比度設計
           ============================================ */
        
        /* 側邊欄所有 expander 標題 - 白色卡片 */
        [data-testid="stSidebar"] details summary,
        [data-testid="stSidebar"] .streamlit-expanderHeader,
        section[data-testid="stSidebar"] details summary {
            background-color: #FFFFFF !important;
            color: #175BA6 !important;
            font-weight: 700 !important;
            font-size: 1.05rem !important;
            border-left: 5px solid #E9E13B !important;
            border-radius: 8px !important;
            padding: 1rem 1.25rem !important;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15) !important;
            margin: 0.5rem 0 !important;
        }
        
        /* 懸停效果 */
        [data-testid="stSidebar"] details summary:hover,
        [data-testid="stSidebar"] .streamlit-expanderHeader:hover {
            background-color: #F8F9FA !important;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2) !important;
            transform: translateY(-1px);
            transition: all 0.2s ease;
        }
        
        /* 側邊欄 expander 內容區塊 */
        [data-testid="stSidebar"] details,
        [data-testid="stSidebar"] .streamlit-expanderContent,
        section[data-testid="stSidebar"] details > div {
            background-color: #FFFFFF !important;
            border-radius: 0 0 8px 8px !important;
            margin-top: -8px !important;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1) !important;
        }
        
        /* 側邊欄內容區所有文字 */
        [data-testid="stSidebar"] details > div,
        [data-testid="stSidebar"] .streamlit-expanderContent,
        section[data-testid="stSidebar"] details p,
        section[data-testid="stSidebar"] details div,
        section[data-testid="stSidebar"] details li,
        section[data-testid="stSidebar"] details h1,
        section[data-testid="stSidebar"] details h2,
        section[data-testid="stSidebar"] details h3,
        section[data-testid="stSidebar"] details h4 {
            background-color: #FFFFFF !important;
            color: #2C2C2C !important;
            padding: 1.25rem !important;
        }
        
        /* 側邊欄標題文字 */
        section[data-testid="stSidebar"] details h4 {
            color: #175BA6 !important;
            font-weight: 700 !important;
            margin-top: 1rem !important;
            margin-bottom: 0.5rem !important;
        }
        
        /* 側邊欄粗體文字 */
        section[data-testid="stSidebar"] details strong,
        section[data-testid="stSidebar"] details b {
            color: #175BA6 !important;
            font-weight: 700 !important;
        }
        
        /* 側邊欄分隔線 */
        section[data-testid="stSidebar"] details hr {
            border-color: rgba(23, 91, 166, 0.2) !important;
            margin: 1rem 0 !important;
        }
        
        /* 主內容區的 expander 保持原樣 */
        .main .streamlit-expanderHeader {
            background-color: rgba(233, 225, 59, 0.15);
            color: #2C2C2C;
            font-weight: bold;
            border-left: 4px solid #175BA6;
            border-radius: 4px;
        }
        
        .main .streamlit-expanderHeader:hover {
            background-color: rgba(233, 225, 59, 0.25);
        }
        
        /* 主內容區背景 - 強制白色 */
        .main {
            background-color: #FFFFFF !important;
        }
        
        /* 卡片樣式優化 - 強制白色背景 */
        [data-testid="stMetric"] {
            background-color: #FFFFFF !important;
            padding: 1rem;
            border-radius: 8px;
            border-left: 4px solid #175BA6;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
        }
        
        /* Spinner 樣式 */
        .stSpinner > div {
            border-top-color: #E9E13B !important;
        }
        
        /* 響應式佈局優化 - 避免元素重疊 */
        .main .block-container {
            padding-top: 1rem;
            padding-bottom: 2rem;
            max-width: 100%;
        }
        
        /* 確保圖表容器自適應 */
        .js-plotly-plot, .plotly {
            width: 100% !important;
        }
        
        /* 多選框容器優化 */
        .stMultiSelect {
            margin-bottom: 0.5rem;
        }
        
        /* Metric 標籤字體大小調整 */
        [data-testid="stMetricLabel"] {
            font-size: 0.9rem !important;
            white-space: nowrap;
        }
        
        [data-testid="stMetricValue"] {
            font-size: 1.5rem !important;
        }
    </style>
    """
    st.markdown(custom_css, unsafe_allow_html=True)

setup_page_config()


# =============================================================================
# 資料載入函數
# =============================================================================

@st.cache_data(ttl=300)  # 快取資料 5 分鐘
def load_data():
    """
    自動偵測環境並載入資料。
    - 如果本地測試檔案存在，從本地 CSV 檔案載入。
    - 否則，從 Google Sheets 載入（Streamlit Cloud 正式環境）。
    """
    # 檢查本地測試檔案是否存在
    local_csv_path = Path("data/TWYA 行動時間線資料_本地測試.csv")
    
    # 優先使用本地 CSV（如果存在）
    if local_csv_path.exists():
        # 本地開發環境，從 CSV 載入
        try:
            with st.spinner(f"📁 本地開發模式：正在從 {local_csv_path} 載入資料..."):
                df = pd.read_csv(local_csv_path)

                # 移除所有欄位均為 NaN 的列
                df.dropna(how='all', inplace=True)

                # 將中文欄位映射到英文欄位 (與 Google Sheet 邏輯保持一致)
                column_mapping = {
                    '負責組別': 'Team', '任務名稱': 'EventName', '性質': 'Level',
                    '開始日期': 'StartDate', '開始時間': 'StartTime', '結束日期': 'EndDate',
                    '結束時間': 'EndTime', '狀態': 'Status', '備註': 'Notes'
                }
                rename_dict = {k: v for k, v in column_mapping.items() if k in df.columns}
                df = df.rename(columns=rename_dict)
                
                # 映射中文狀態到英文
                status_mapping = {
                    '未開始': 'ToDo',
                    '進行中': 'WIP',
                    '已完成': 'Done',
                    '完成': 'Done',
                    '阻塞': 'Blocked',
                    '暫停': 'Pending'
                }
                if 'Status' in df.columns:
                    df['Status'] = df['Status'].map(lambda x: status_mapping.get(x, x) if pd.notna(x) else x)
                
                # 保留原始的性質名稱（籌備、執行）
                # 不做任何映射，直接使用CSV中的值

                return df, None, "本地 CSV 檔案"
        except Exception as e:
            error_msg = f"從本地 CSV 檔案載入資料時發生錯誤: {e}"
            return None, error_msg, "本地 CSV 檔案"
    else:
        # Streamlit Cloud 環境，從 Google Sheets 載入
        try:
            with st.spinner("☁️ 正在從 Google Sheets 載入即時資料..."):
                # 使用 gspread 的現代化驗證方法
                creds = st.secrets["gcp_service_account"]
                gc = gspread.service_account_from_dict(creds)
                
                sheet_name = st.secrets.get("sheet_name", "TWYA 行動時間線資料")
                spreadsheet = gc.open(sheet_name)
                worksheet = spreadsheet.sheet1
                
                df = get_as_dataframe(worksheet)
                
                # 移除所有欄位均為 NaN 的列
                df.dropna(how='all', inplace=True)
                
                # 將中文欄位映射到英文欄位
                column_mapping = {
                    '負責組別': 'Team', '任務名稱': 'EventName', '性質': 'Level',
                    '開始日期': 'StartDate', '開始時間': 'StartTime', '結束日期': 'EndDate',
                    '結束時間': 'EndTime', '狀態': 'Status', '備註': 'Notes'
                }
                rename_dict = {k: v for k, v in column_mapping.items() if k in df.columns}
                df = df.rename(columns=rename_dict)
                
                # 映射中文狀態到英文
                status_mapping = {
                    '未開始': 'ToDo',
                    '進行中': 'WIP',
                    '已完成': 'Done',
                    '完成': 'Done',
                    '阻塞': 'Blocked',
                    '暫停': 'Pending'
                }
                if 'Status' in df.columns:
                    df['Status'] = df['Status'].map(lambda x: status_mapping.get(x, x) if pd.notna(x) else x)
                
                # 保留原始的性質名稱（籌備、執行）
                # 不做任何映射，直接使用CSV中的值
                
                return df, None, "Google Sheets"
        except Exception as e:
            error_msg = f"從 Google Sheets 載入資料時發生錯誤: {e}"
            return None, error_msg, "Google Sheets"



def clean_and_validate_data(df):
    """清理並驗證資料，支持多種日期時間格式"""
    df_clean = df.copy()
    
    # 補充選填欄位
    optional_columns = {
        'Level': '執行',
        'Status': 'ToDo',
        'Notes': '',
        'StartTime': '',
        'EndTime': '',
        'StartDate': None,
        'EndDate': None
    }
    
    for col, default_value in optional_columns.items():
        if col not in df_clean.columns:
            df_clean[col] = default_value
    
    # 填補空值
    df_clean['Level'] = df_clean['Level'].fillna('執行')
    df_clean['Status'] = df_clean['Status'].fillna('ToDo')
    df_clean['Notes'] = df_clean['Notes'].fillna('')
    df_clean['StartTime'] = df_clean['StartTime'].fillna('')
    df_clean['EndTime'] = df_clean['EndTime'].fillna('')
    
    # 轉換日期格式
    for col in ['StartDate', 'EndDate']:
        df_clean[col] = pd.to_datetime(df_clean[col], errors='coerce')
    
    # 處理只有結束日期的情況（deadline）
    # 如果沒有開始日期，則將開始日期設為結束日期前7天（或當天）
    mask_no_start = df_clean['StartDate'].isna() & df_clean['EndDate'].notna()
    if mask_no_start.any():
        df_clean.loc[mask_no_start, 'StartDate'] = df_clean.loc[mask_no_start, 'EndDate'] - pd.Timedelta(days=1)
        # 標記這些為deadline類型
        if 'EventType' not in df_clean.columns:
            df_clean['EventType'] = 'normal'
        df_clean.loc[mask_no_start, 'EventType'] = 'deadline'
    
    # 如果還沒有EventType欄位，添加並設為normal
    if 'EventType' not in df_clean.columns:
        df_clean['EventType'] = 'normal'
    
    # 移除完全沒有日期的記錄（開始和結束都沒有）
    df_clean = df_clean.dropna(subset=['EndDate'])
    
    # 確保結束日期不早於開始日期
    mask = df_clean['EndDate'] < df_clean['StartDate']
    if mask.any():
        df_clean.loc[mask, ['StartDate', 'EndDate']] = \
            df_clean.loc[mask, ['EndDate', 'StartDate']].values
    
    # 分類事項類型
    # 如果有明確的時間，標記為'timed'；只有日期則為'date_only'
    df_clean['HasStartTime'] = df_clean['StartTime'].astype(str).str.strip().ne('') & df_clean['StartTime'].notna()
    df_clean['HasEndTime'] = df_clean['EndTime'].astype(str).str.strip().ne('') & df_clean['EndTime'].notna()
    
    # 排序
    df_clean = df_clean.sort_values(['Team', 'StartDate'], ascending=[True, True])
    df_clean = df_clean.reset_index(drop=True)
    
    return df_clean


# =============================================================================
# 視覺化函數
# =============================================================================

def get_team_color_mapping(teams):
    """為不同團隊分配顏色（使用高對比度色系）"""
    # 使用高對比度、易於區分的顏色
    default_colors = {
        '行政組': '#1E88E5',  # 明亮藍
        '活動組': '#43A047',  # 綠色
        '公關組': '#E53935',  # 紅色
        '財務組': '#FB8C00',  # 橙色
        '教育組': '#8E24AA',  # 紫色
        '資訊組': '#00ACC1',  # 青色
        '企劃組': '#F9A825',  # 金黃
        '研發組': '#5E35B1',  # 深紫
        '理事長': '#C62828',  # 深紅
    }
    
    # 使用高對比度的顏色配色
    plotly_colors = [
        '#1E88E5',  # 明亮藍
        '#43A047',  # 綠色
        '#E53935',  # 紅色
        '#FB8C00',  # 橙色
        '#8E24AA',  # 紫色
        '#00ACC1',  # 青色
        '#F9A825',  # 金黃
        '#5E35B1',  # 深紫
        '#00897B',  # 藍綠
        '#D81B60',  # 粉紅
    ]
    
    color_mapping = {}
    for i, team in enumerate(sorted(teams.unique())):
        if team in default_colors:
            color_mapping[team] = default_colors[team]
        else:
            color_mapping[team] = plotly_colors[i % len(plotly_colors)]
    
    return color_mapping


def get_luminance(hex_color):
    """計算顏色的亮度（0-1之間，越接近1越亮）"""
    # 移除 # 符號
    hex_color = hex_color.lstrip('#')
    # 轉換為 RGB
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    # 計算相對亮度（使用 ITU-R BT.709 標準）
    luminance = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255
    return luminance


def is_dark_color(hex_color):
    """判斷顏色是否為深色（亮度小於0.5視為深色）"""
    return get_luminance(hex_color) < 0.5


def get_status_marker(status):
    """根據狀態返回標記符號"""
    status_markers = {
        'Done': '✓',
        'WIP': '⟳',
        'ToDo': '○',
        'Blocked': '⊗',
        'Pending': '⏸'
    }
    return status_markers.get(status, '')


def create_timeline_chart(df, selected_teams=None, selected_status=None, selected_levels=None):
    """生成互動式時間線圖表"""
    # 篩選資料
    df_filtered = df.copy()
    if selected_teams:
        df_filtered = df_filtered[df_filtered['Team'].isin(selected_teams)]
    if selected_status:
        df_filtered = df_filtered[df_filtered['Status'].isin(selected_status)]
    if selected_levels:
        df_filtered = df_filtered[df_filtered['Level'].isin(selected_levels)]
    
    if df_filtered.empty:
        return None
    
    # 獲取團隊配色
    color_mapping = get_team_color_mapping(df['Team'])
    
    # 建立圖表
    fig = go.Figure()
    
    # 為每個事件添加時間線條
    for idx, row in df_filtered.iterrows():
        # 判斷事項類型
        is_deadline = row.get('EventType') == 'deadline'
        has_start_time = row.get('HasStartTime', False)
        has_end_time = row.get('HasEndTime', False)
        
        # 格式化顯示時間
        if is_deadline:
            start_display = "（無開始時間）"
            end_display = row['EndDate'].strftime('%Y-%m-%d')
            if has_end_time:
                end_display += f" {row['EndTime']}"
        else:
            start_display = row['StartDate'].strftime('%Y-%m-%d')
            if has_start_time:
                start_display += f" {row['StartTime']}"
            
            end_display = row['EndDate'].strftime('%Y-%m-%d')
            if has_end_time:
                end_display += f" {row['EndTime']}"
        
        # 判斷時間精度
        time_precision = "⏰ " if (has_start_time or has_end_time) else "📅 "
        deadline_marker = "🎯 " if is_deadline else ""
        
        hover_text = (
            f"<b>{deadline_marker}{row['EventName']}</b><br>"
            f"負責組別：{row['Team']}<br>"
            f"性質：{row['Level']}<br>"
            f"狀態：{row['Status']}<br>"
        )
        
        if is_deadline:
            hover_text += f"截止期限：{time_precision}{end_display}<br>"
        else:
            hover_text += (
                f"開始：{time_precision}{start_display}<br>"
                f"結束：{time_precision}{end_display}<br>"
            )
        
        hover_text += f"備註：{row['Notes'] if row['Notes'] else '無'}"
        
        status_marker = get_status_marker(row['Status'])
        display_text = f"{deadline_marker}{status_marker} {row['EventName']}" if (status_marker or deadline_marker) else row['EventName']
        
        # 獲取團隊顏色
        team_color = color_mapping[row['Team']]
        
        # 計算時間跨度（天數）
        time_span_days = (row['EndDate'] - row['StartDate']).days
        
        # 判斷文字顏色（根據底色明暗度和時間跨度）
        # 如果時間跨度較長且底色是深色，使用白色文字以提高可讀性
        if time_span_days >= 30 and not is_deadline and is_dark_color(team_color):
            text_color = '#FFFFFF'  # 深色背景用白色文字
        else:
            text_color = '#2C2C2C'  # 其他情況使用黑色文字
        
        # deadline使用不同的視覺樣式
        if is_deadline:
            line_style = dict(color=team_color, width=6, dash='dot')  # 虛線表示deadline
            marker_style = dict(size=16, symbol='diamond', color=team_color, 
                              line=dict(color='white', width=2))  # 菱形標記
        else:
            line_style = dict(color=team_color, width=18)  # 實線表示時間段
            marker_style = dict(size=14, symbol='circle', color=team_color, 
                              line=dict(color='white', width=2))  # 圓形標記
        
        fig.add_trace(go.Scatter(
            x=[row['StartDate'], row['EndDate']],
            y=[idx, idx],
            mode='lines+markers+text',
            name=row['Team'],
            line=line_style,
            marker=marker_style,
            text=[display_text, ''],
            textposition='middle right',  # 統一使用右側位置，保持文字位置一致
            textfont=dict(size=12, color=text_color, family='Arial Black'),  # 根據背景動態調整文字顏色
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
    
    # 添加今天的日期標記線
    from datetime import datetime
    today = datetime.now()
    fig.add_shape(
        type="line",
        x0=today, x1=today,
        y0=-0.5, y1=len(df_filtered) - 0.5,
        line=dict(
            color="#FF6B6B",  # 醒目的紅色
            width=3,
            dash="dash"  # 虛線
        ),
        layer="below"  # 放在事件條下方
    )
    
    # 添加今天的標籤
    fig.add_annotation(
        x=today,
        y=len(df_filtered),
        text=f"📅 今天 ({today.strftime('%Y-%m-%d')})",
        showarrow=False,
        yshift=10,
        font=dict(size=12, color="#FF6B6B", weight="bold"),
        bgcolor="rgba(255, 255, 255, 0.9)",
        bordercolor="#FF6B6B",
        borderwidth=2,
        borderpad=4
    )
    
    # 計算動態高度：項目少時也要有足夠空間
    num_items = len(df_filtered)
    chart_height = max(400, min(800, num_items * 50))  # 最小400, 最大800
    
    # 計算初始顯示範圍：左側為當天前一個月，右側為最遠的活動日期
    from datetime import datetime, timedelta
    today = datetime.now()
    one_month_ago = today - timedelta(days=30)
    max_end_date = df_filtered['EndDate'].max()
    
    # 設定圖表佈局（橫向長方形，啟用滾輪縮放）
    fig.update_layout(
        title={
            'text': '臺灣華德福青年運動聯盟行動時間線<br><sub>Taiwan Waldorf Youth Alliance Timeline</sub>',
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 22, 'color': '#1565C0', 'family': 'Arial, sans-serif', 'weight': 'bold'}
        },
        xaxis=dict(
            title=dict(text='時間軸', font=dict(color='#37474F', size=14, weight='bold')),
            showgrid=True, 
            gridcolor='rgba(0, 0, 0, 0.08)',
            gridwidth=1,
            type='date',
            zeroline=False,
            tickfont=dict(size=12, color='#37474F'),
            tickformat='%Y-%m-%d',
            tickmode='auto',  # 自動調整刻度，根據縮放程度顯示適當的時間間隔
            nticks=15,  # 建議刻度數量，但會根據實際範圍調整
            # 設定初始顯示範圍
            range=[one_month_ago, max_end_date],  # 左側：今天前一個月，右側：最遠的活動日期
            # 啟用縮放和平移
            rangeslider=dict(visible=False),
            fixedrange=False,  # 允許縮放
            # 啟用游標處顯示日期的垂直線
            showspikes=True,
            spikemode='across',
            spikesnap='cursor',
            spikethickness=2,
            spikecolor='#1565C0',
            spikedash='dot'
        ),
        yaxis=dict(
            title=dict(text='行動項目', font=dict(color='#37474F', size=14, weight='bold')),
            showticklabels=False, 
            showgrid=True, 
            gridcolor='rgba(0, 0, 0, 0.05)',
            zeroline=False,
            fixedrange=True,  # Y軸固定，只允許X軸縮放
            showspikes=False  # Y軸不顯示spike line
        ),
        hovermode='x unified',  # 改用 x unified 模式，顯示游標處所有項目
        plot_bgcolor='#FAFAFA',  # 淺灰背景
        paper_bgcolor='white',
        height=chart_height,
        margin=dict(l=30, r=150, t=100, b=50),  # 進一步減少左側邊距，增加圖表橫向空間
        legend=dict(
            title=dict(text='團隊分組', font=dict(size=13, color='#1565C0', weight='bold')),
            orientation='v',
            yanchor='top', y=1,
            xanchor='left', x=1.005,  # 圖例更靠近圖表
            bgcolor='rgba(255,255,255,0.95)',
            bordercolor='#1565C0',
            borderwidth=1,
            font=dict(color='#37474F', size=10)  # 縮小圖例字體
        ),
        # 設定拖拉模式為平移，滾輪用於縮放
        dragmode='pan',  # 鼠標拖拉時平移視圖，滾輪用於縮放
    )
    
    # 配置互動選項，啟用滾輪縮放
    fig.update_xaxes(
        rangeselector=dict(
            buttons=list([
                dict(count=1, label="1個月", step="month", stepmode="backward"),
                dict(count=3, label="3個月", step="month", stepmode="backward"),
                dict(count=6, label="6個月", step="month", stepmode="backward"),
                dict(count=1, label="1年", step="year", stepmode="backward"),
                dict(step="all", label="全部")
            ]),
            bgcolor='#E3F2FD',
            activecolor='#1565C0',
            font=dict(color='#37474F', size=11),
            x=0,
            y=1.12
        )
    )
    
    return fig


# =============================================================================
# 主應用程式
# =============================================================================

def main():
    # 優化頂部佈局，將控制項移到頂部
    header_col1, header_col2, header_col3 = st.columns([1, 8, 2])
    with header_col1:
        logo_path = Path("./logo/logo.png")
        if logo_path.exists():
            st.image(str(logo_path), width=70)
        else:
            st.markdown("""<div style='width:60px;height:60px;background:linear-gradient(135deg, #1565C0 0%, #0D47A1 100%);border-radius:8px;display:flex;align-items:center;justify-content:center;'><span style='color:white;font-size:16px;font-weight:bold;'>TWYA</span></div>""", unsafe_allow_html=True)
    with header_col2:
        st.markdown("<h2 style='margin:0;padding:0;color:#1565C0;'>臺灣華德福青年運動聯盟行動時間線</h2>", unsafe_allow_html=True)
        st.markdown("<p style='margin:0;padding:0;color:#546E7A;font-size:13px;'>Taiwan Waldorf Youth Alliance Timeline</p>", unsafe_allow_html=True)
    with header_col3:
        # 重新載入按鈕移到頂部
        if st.button("🔄 重新載入", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    
    # 側邊欄（簡化內容，默認收起）
    with st.sidebar:
        st.markdown("""
        <div style='
            background: linear-gradient(135deg, #FFFFFF 0%, #F8F9FA 100%);
            padding: 1.5rem;
            border-radius: 12px;
            border-left: 5px solid #E9E13B;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            margin-bottom: 1rem;
        '>
            <h3 style='color: #175BA6; margin: 0 0 1rem 0; font-weight: 700; display: flex; align-items: center;'>
                📖 使用說明
            </h3>
            
            <div style='background: white; padding: 1rem; border-radius: 8px; margin-bottom: 0.75rem; box-shadow: 0 2px 4px rgba(0,0,0,0.05);'>
                <h4 style='color: #175BA6; margin: 0 0 0.5rem 0; font-size: 0.95rem; font-weight: 600;'>🎯 基本功能</h4>
                <p style='color: #2C2C2C; margin: 0.25rem 0; font-size: 0.85rem; line-height: 1.5;'>
                    <strong style='color: #175BA6;'>📊 查看時間線</strong><br>
                    圖表自動顯示所有行動任務，不同團隊使用不同顏色區分
                </p>
                <p style='color: #2C2C2C; margin: 0.5rem 0 0 0; font-size: 0.85rem; line-height: 1.5;'>
                    <strong style='color: #175BA6;'>🔍 篩選功能</strong><br>
                    支援團隊、狀態、性質多重篩選，留空顯示全部資料
                </p>
            </div>
            
            <div style='background: white; padding: 1rem; border-radius: 8px; margin-bottom: 0.75rem; box-shadow: 0 2px 4px rgba(0,0,0,0.05);'>
                <h4 style='color: #175BA6; margin: 0 0 0.5rem 0; font-size: 0.95rem; font-weight: 600;'>🖱️ 互動操作</h4>
                <p style='color: #2C2C2C; margin: 0.25rem 0; font-size: 0.85rem; line-height: 1.5;'>
                    📍 滑鼠移到任務條上查看詳情<br>
                    🔎 滾輪縮放、拖曳移動、雙擊重置<br>
                    📥 點擊📷圖示下載截圖
                </p>
            </div>
            
            <div style='background: white; padding: 1rem; border-radius: 8px; margin-bottom: 0.75rem; box-shadow: 0 2px 4px rgba(0,0,0,0.05);'>
                <h4 style='color: #175BA6; margin: 0 0 0.5rem 0; font-size: 0.95rem; font-weight: 600;'>🎨 圖例說明</h4>
                <p style='color: #2C2C2C; margin: 0.25rem 0; font-size: 0.85rem; line-height: 1.5;'>
                    <strong>狀態：</strong> ⭕ToDo | 🔄WIP | ✅Done<br>
                    <strong>性質：</strong> 🛠️籌備 | 🚀執行
                </p>
            </div>
            
            <div style='background: white; padding: 1rem; border-radius: 8px; margin-bottom: 0.75rem; box-shadow: 0 2px 4px rgba(0,0,0,0.05);'>
                <h4 style='color: #175BA6; margin: 0 0 0.5rem 0; font-size: 0.95rem; font-weight: 600;'>🔄 資料更新</h4>
                <p style='color: #2C2C2C; margin: 0.25rem 0; font-size: 0.85rem; line-height: 1.5;'>
                    ☁️ 每5分鐘自動同步<br>
                    🔃 手動點擊右上角按鈕
                </p>
            </div>
            
            <div style='background: #FFF9E6; padding: 1rem; border-radius: 8px; border-left: 3px solid #E9E13B; box-shadow: 0 2px 4px rgba(0,0,0,0.05);'>
                <h4 style='color: #175BA6; margin: 0 0 0.5rem 0; font-size: 0.95rem; font-weight: 600;'>💡 小技巧</h4>
                <p style='color: #2C2C2C; margin: 0.25rem 0; font-size: 0.85rem; line-height: 1.5;'>
                    • 統計資訊即時更新<br>
                    • 支援多選交叉比對<br>
                    • 先篩選後縮放查看細節
                </p>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    df, error, source = load_data()
    
    if df is not None:
        if source == "Google Sheets":
            st.success("☁️ 已從 Google Sheets 載入即時資料")
        else:
            st.success(f"️本地模式：已從 {source} 載入資料")
    else:
        st.error(f"❌ 無法載入資料")
        st.error(f"**來源：** {source}\n\n**錯誤詳情：** {error}")

    if error:
        # 如果是本地開發且檔案不存在，提供指引
        if source == "本地 CSV 檔案" and "FileNotFoundError" in error:
            st.warning(
                "### 找不到本地測試資料檔案！\n\n"
                "請確認 `data/TWYA 行動時間線資料_本地測試.csv` 檔案存在於您的專案目錄中。\n\n"
                "如果檔案已存在但仍無法載入，可能是以下原因：\n\n"
                "1. **檔案路徑不正確** - 請確認檔案位於 `data/` 資料夾中\n"
                "2. **檔案編碼問題** - 請確認 CSV 檔案使用 UTF-8 編碼\n"
                "3. **檔案權限問題** - 請確認應用程式有讀取權限"
            )
        return
    
    if df is None or df.empty:
        st.warning("⚠️ 沒有可用的資料")
        return
    
    # 清理資料
    df_clean = clean_and_validate_data(df)
    
    if df_clean.empty:
        st.warning("⚠️ 清理後沒有有效資料")
        return
    
    # 統計資訊區（單獨一行）
    stat_col1, stat_col2, stat_col3, stat_col4, stat_col5 = st.columns(5)
    with stat_col1:
        st.metric("📊 總項目", len(df_clean))
    with stat_col2:
        st.metric("👥 團隊數", df_clean['Team'].nunique())
    with stat_col3:
        done_count = len(df_clean[df_clean['Status'] == 'Done'])
        st.metric("✓ Done", done_count)
    with stat_col4:
        wip_count = len(df_clean[df_clean['Status'] == 'WIP'])
        st.metric("⟳ WIP", wip_count)
    with stat_col5:
        todo_count = len(df_clean[df_clean['Status'] == 'ToDo'])
        st.metric("○ ToDo", todo_count)
    
    st.markdown("<div style='margin:8px 0;'></div>", unsafe_allow_html=True)
    
    # 篩選器區（單獨一行）
    filter_col1, filter_col2, filter_col3 = st.columns([3, 3, 3])
    all_teams = sorted(df_clean['Team'].unique())
    all_status = sorted(df_clean['Status'].unique())
    all_levels = sorted(df_clean['Level'].unique())
    with filter_col1:
        selected_teams = st.multiselect(
            "🔍 選擇團隊",
            options=all_teams,
            default=all_teams,
            help="可選擇多個團隊"
        )
    with filter_col2:
        selected_status = st.multiselect(
            "📌 選擇狀態",
            options=all_status,
            default=all_status,
            help="可選擇多個狀態"
        )
    with filter_col3:
        selected_levels = st.multiselect(
            "🎯 選擇性質",
            options=all_levels,
            default=all_levels,
            help="可選擇多個性質"
        )
    
    st.markdown("<hr style='margin:10px 0;border:none;border-top:1px solid #E0E0E0;'>", unsafe_allow_html=True)
    
    # 生成並顯示圖表
    with st.spinner("正在生成時間線..."):
        fig = create_timeline_chart(df_clean, selected_teams, selected_status, selected_levels)
    
    if fig is None:
        st.warning("⚠️ 沒有符合篩選條件的資料")
        return
    
    # 顯示圖表，啟用滾輪縮放功能
    config = {
        'scrollZoom': True,  # 啟用滑鼠滾輪縮放
        'displayModeBar': True,
        'modeBarButtonsToAdd': ['pan2d', 'zoomIn2d', 'zoomOut2d', 'resetScale2d'],
        'displaylogo': False,
        'toImageButtonOptions': {
            'format': 'png',
            'filename': 'twya_timeline',
            'height': 800,
            'width': 1600,
            'scale': 2
        }
    }
    st.plotly_chart(fig, use_container_width=True, config=config)
    
    # 顯示資料表
    with st.expander("📋 查看原始資料"):
        display_df = df_clean.copy()
        if selected_teams:
            display_df = display_df[display_df['Team'].isin(selected_teams)]
        if selected_status:
            display_df = display_df[display_df['Status'].isin(selected_status)]
        if selected_levels:
            display_df = display_df[display_df['Level'].isin(selected_levels)]
        
        # 建立反向映射，將英文欄位名稱轉回中文
        display_columns = {
            'Team': '負責組別',
            'EventName': '任務名稱',
            'Level': '性質',
            'StartDate': '開始日期',
            'StartTime': '開始時間',
            'EndDate': '結束日期',
            'EndTime': '結束時間',
            'Status': '狀態',
            'Notes': '備註'
        }
        
        # 反向映射狀態值為中文
        status_reverse_mapping = {
            'ToDo': 'ToDo',
            'WIP': 'WIP',
            'Done': 'Done',
            'Blocked': 'Blocked',
            'Pending': 'Pending'
        }
        
        # 準備顯示用的資料框
        show_df = display_df[['Team', 'EventName', 'Level', 'StartDate', 'StartTime', 'EndDate', 'EndTime', 'Status', 'Notes']].copy()
        
        # 將日期格式化為易讀格式
        show_df['StartDate'] = show_df['StartDate'].dt.strftime('%Y/%m/%d').fillna('')
        show_df['EndDate'] = show_df['EndDate'].dt.strftime('%Y/%m/%d').fillna('')
        
        # 將欄位名稱改為中文
        show_df = show_df.rename(columns=display_columns)
        
        st.dataframe(
            show_df,
            width="stretch",
            hide_index=True
        )


if __name__ == "__main__":
    main()
