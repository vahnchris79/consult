# 데이터 분석 컨설팅(도시공간계획과): 지도시각화

import pandas as pd
import streamlit as st
import plotly.express as px
import folium
from folium.plugins import HeatMap
from streamlit_folium import st_folium
import sqlite3


# 페이지 설정
st.set_page_config(page_title="생활인구 및 카드사용 분석", layout="wide")

# 배경색 흰색으로 변경
st.markdown("""
    <style>
    .main {
        background-color: white;
    }
    .stApp {
        background-color: white;
    }
    </style>
    """, unsafe_allow_html=True)

# 데이터 로드
@st.cache_data
def load_data():
    path = "data/"
    #conn = sqlite3.connect(path + "2025_040_도시공간계획과_20250915.db")
    
    # 생활인구 데이터
    df_pop = pd.read_csv(path + "2024_monthly_servicepop.csv", encoding="utf-8")
    # 카드사용 데이터
    df_card = pd.read_csv(path + "2024_monthly_carduse.csv", encoding="utf-8")

    # conn.close()
    return df_pop, df_card

df_pop, df_card = load_data()

# 사이드바 필터
st.sidebar.header("필터설정")

# 데이터 선택
data_type = st.sidebar.radio("데이터 선택", ["생활인구", "카드사용", "생활인구 + 카드사용"])

# 카드사용 선택 시 지표 선택 추가
if data_type in ["카드사용", "생활인구 + 카드사용"]:
    card_metric = st.sidebar.radio("카드사용 지표", ["금액(amt)", "건수(cnt)"])
else:
    card_metric = "금액(amt)"

select_ym = st.sidebar.selectbox("기준연월", sorted(df_pop['std_ym'].unique()))
select_week = st.sidebar.selectbox("주중주말", df_pop['weeknm'].unique())
select_time = st.sidebar.selectbox('시간선택', sorted(df_pop['times'].unique()))
select_name = st.sidebar.selectbox('중심지선택', sorted(df_pop['name'].unique()))

# 지도 설정
map_tiles = st.sidebar.selectbox(
    "배경맵 선택",
    ["Vworld", "카카오맵", "OpenStreetMap", "CartoDB positron", "CartoDB dark_matter"]
)
opacity_value = st.sidebar.slider('히트맵 투명도', min_value=0.0, max_value=1.0, value=0.6, step=0.1)

# 생활인구 데이터 필터링
filter_df_pop = df_pop[
    (df_pop['std_ym'] == select_ym) & (df_pop['weeknm'] == select_week) & 
    (df_pop['times'] == select_time) & (df_pop['name'] == select_name)
]

bar_df_pop = df_pop[
    (df_pop['std_ym'] == select_ym) & (df_pop['weeknm'] == select_week) & 
    (df_pop['name'] == select_name)].copy()

# 생활인구 천명 단위 변환
bar_df_pop['pop_k'] = bar_df_pop['pop'] / 1000

# 카드사용 데이터 필터링
filter_df_card = df_card[
    (df_card['std_ym'] == select_ym) & (df_card['weeknm'] == select_week) & 
    (df_card['times'] == select_time) & (df_card['name'] == select_name)
]

bar_df_card = df_card[
    (df_card['std_ym'] == select_ym) & (df_card['weeknm'] == select_week) & 
    (df_card['name'] == select_name)].copy()

# 카드사용 금액 백만원 단위 변환
if 'amt' in bar_df_card.columns:
    bar_df_card['amt_m'] = bar_df_card['amt'] / 1000000

# 카드사용 지표 컬럼명 설정
if card_metric == "금액(amt)":
    card_col = 'amt'
    card_col_display = 'amt_m'
    card_label = "카드사용액 (백만원)"
    card_title = "카드사용액"
    card_hover_unit = "백만원"
else:
    card_col = 'cnt'
    card_col_display = 'cnt'
    card_label = "카드사용 건수 (건)"
    card_title = "카드사용 건수"
    card_hover_unit = "건"

# 지도 중심 좌표 - 선택한 중심지의 전체 데이터 기준으로 고정
name_df_pop = df_pop[df_pop['name'] == select_name]
name_df_card = df_card[df_card['name'] == select_name]

if data_type == "생활인구":
    if len(name_df_pop) > 0 and not name_df_pop['y'].isna().all():
        center_lat = name_df_pop['y'].mean()
        center_lon = name_df_pop['x'].mean()
    else:
        center_lat = df_pop['y'].mean()
        center_lon = df_pop['x'].mean()
elif data_type == "카드사용":
    if len(name_df_card) > 0 and not name_df_card['y'].isna().all():
        center_lat = name_df_card['y'].mean()
        center_lon = name_df_card['x'].mean()
    else:
        center_lat = df_card['y'].mean()
        center_lon = df_card['x'].mean()
else:  # 생활인구 + 카드사용
    if len(name_df_pop) > 0 and not name_df_pop['y'].isna().all():
        center_lat = name_df_pop['y'].mean()
        center_lon = name_df_pop['x'].mean()
    else:
        center_lat = df_pop['y'].mean()
        center_lon = df_pop['x'].mean()

# NaN 체크 추가
if pd.isna(center_lat) or pd.isna(center_lon):
    st.error("지도 좌표 데이터에 문제가 있습니다. 데이터를 확인해주세요.")
    st.stop()

# 지도 생성
st.subheader("시간대별 밀도 지도")

# 타일 설정
if map_tiles == "Vworld":
    m = folium.Map(
        location=[center_lat, center_lon], 
        zoom_start=15,
        tiles='http://xdworld.vworld.kr:8080/2d/Base/service/{z}/{x}/{y}.png',
        attr='Vworld',
        dragging=True,
        zoom_control=True,
        scrollWheelZoom=True
    )
elif map_tiles == "카카오맵":
    m = folium.Map(
        location=[center_lat, center_lon], 
        zoom_start=15,
        tiles='http://map{s}.daumcdn.net/map_2d/2106ydg/L{z}/{y}/{x}.png',
        attr='Kakao', 
        subdomains=['0', '1', '2', '3'],
        dragging=True,
        zoom_control=True,
        scrollWheelZoom=True
    )
elif map_tiles == "OpenStreetMap":
    m = folium.Map(
        location=[center_lat, center_lon], 
        zoom_start=15,
        tiles='OpenStreetMap',
        dragging=True,
        zoom_control=True,
        scrollWheelZoom=True
    )
elif map_tiles == "CartoDB positron":
    m = folium.Map(
        location=[center_lat, center_lon], 
        zoom_start=15,
        tiles='CartoDB positron',
        dragging=True,
        zoom_control=True,
        scrollWheelZoom=True
    )
else:  # CartoDB dark_matter
    m = folium.Map(
        location=[center_lat, center_lon], 
        zoom_start=15,
        tiles='CartoDB dark_matter',
        dragging=True,
        zoom_control=True,
        scrollWheelZoom=True
    )

# 히트맵 데이터 추가
if data_type == "생활인구":
    if len(filter_df_pop) > 0:
        heat_data = [[row['y'], row['x'], row['pop']] for idx, row in filter_df_pop.iterrows()]
        HeatMap(heat_data, radius=40, blur=25, max_zoom=13, min_opacity=opacity_value,
            gradient={0.0: 'white', 0.5: 'yellow', 0.7: 'orange', 1.0: 'red'},
            name='생활인구'
        ).add_to(m)
    else:
        st.warning("선택한 조건에 해당하는 생활인구 데이터가 없습니다.")

elif data_type == "카드사용":
    if len(filter_df_card) > 0:
        heat_data = [[row['y'], row['x'], row[card_col]] for idx, row in filter_df_card.iterrows()]
        HeatMap(heat_data, radius=40, blur=25, max_zoom=13, min_opacity=opacity_value,
            gradient={0.0: 'white', 0.5: 'lightblue', 0.7: 'blue', 1.0: 'darkblue'},
            name=f'카드사용({card_metric})'
        ).add_to(m)
    else:
        st.warning("선택한 조건에 해당하는 카드사용 데이터가 없습니다.")

else:  # 생활인구 + 카드사용
    if len(filter_df_pop) > 0:
        heat_data_pop = [[row['y'], row['x'], row['pop']] for idx, row in filter_df_pop.iterrows()]
        HeatMap(heat_data_pop, radius=40, blur=25, max_zoom=13, min_opacity=opacity_value*0.7,
            gradient={0.0: 'white', 0.5: 'yellow', 0.7: 'orange', 1.0: 'red'},
            name='생활인구'
        ).add_to(m)
    
    if len(filter_df_card) > 0:
        heat_data_card = [[row['y'], row['x'], row[card_col]] for idx, row in filter_df_card.iterrows()]
        HeatMap(heat_data_card, radius=40, blur=25, max_zoom=13, min_opacity=opacity_value*0.7,
            gradient={0.0: 'white', 0.5: 'lightblue', 0.7: 'blue', 1.0: 'darkblue'},
            name=f'카드사용({card_metric})'
        ).add_to(m)
    
    if len(filter_df_pop) == 0 and len(filter_df_card) == 0:
        st.warning("선택한 조건에 해당하는 데이터가 없습니다.")
    
    # 레이어 컨트롤 추가
    folium.LayerControl().add_to(m)

# Streamlit에 지도 표시 (key 추가로 상태 초기화)
st_folium(m, width=None, height=550, key=f"{select_name}_{select_ym}_{select_week}_{select_time}")

# 시간대별 변화 그래프
st.subheader("시간대별 변화")

if data_type == "생활인구":
    fig_bar = px.bar(bar_df_pop, x='times', y='pop_k', 
                     title=f"{select_ym} {select_week} {select_name} 생활인구 변화")
    fig_bar.update_traces(
        marker_color='#ff6b6b',
        hovertemplate='<b>%{x}</b><br>인구수: %{y:.2f}천명<extra></extra>'
    )
    fig_bar.update_layout(
        height=450, 
        title_font=dict(size=16, color='black'), 
        font=dict(size=12, color='black'),
        xaxis_title="시간",
        yaxis_title="인구수 (천명)",
        xaxis={'categoryorder': 'array', 'categoryarray': sorted(df_pop["times"].unique())},
        xaxis_tickfont=dict(color='black', size=12),
        yaxis_tickfont=dict(color='black', size=12),
        xaxis_title_font=dict(color='black'),
        yaxis_title_font=dict(color='black'),
        plot_bgcolor='white',
        paper_bgcolor='white',
        margin=dict(l=10, r=10, t=50, b=10)
    )
    fig_bar.update_xaxes(showline=True, linewidth=1, linecolor='black', gridcolor='lightgray')
    fig_bar.update_yaxes(showline=True, linewidth=1, linecolor='black', gridcolor='lightgray')
    st.plotly_chart(fig_bar, use_container_width=True)

elif data_type == "카드사용":
    if card_metric == "금액(amt)":
        hover_template = '<b>%{x}</b><br>금액: %{y:.2f}백만원<extra></extra>'
    else:
        hover_template = '<b>%{x}</b><br>건수: %{y:,.0f}건<extra></extra>'
    
    fig_bar = px.bar(bar_df_card, x='times', y=card_col_display, 
                     title=f"{select_ym} {select_week} {select_name} {card_title} 변화")
    fig_bar.update_traces(
        marker_color='#4dabf7',
        hovertemplate=hover_template
    )
    fig_bar.update_layout(
        height=450, 
        title_font=dict(size=16, color='black'), 
        font=dict(size=12, color='black'),
        xaxis_title="시간",
        yaxis_title=card_label,
        xaxis={'categoryorder': 'array', 'categoryarray': sorted(df_card["times"].unique())},
        xaxis_tickfont=dict(color='black', size=12),
        yaxis_tickfont=dict(color='black', size=12),
        xaxis_title_font=dict(color='black'),
        yaxis_title_font=dict(color='black'),
        plot_bgcolor='white',
        paper_bgcolor='white',
        margin=dict(l=10, r=10, t=50, b=10)
    )
    fig_bar.update_xaxes(showline=True, linewidth=1, linecolor='black', gridcolor='lightgray')
    fig_bar.update_yaxes(showline=True, linewidth=1, linecolor='black', gridcolor='lightgray')
    st.plotly_chart(fig_bar, use_container_width=True)

else:  # 생활인구 + 카드사용
    col1, col2 = st.columns(2)
    
    with col1:
        fig_pop = px.bar(bar_df_pop, x='times', y='pop_k', 
                         title=f"{select_ym} {select_week} {select_name} 생활인구")
        fig_pop.update_traces(
            marker_color='#ff6b6b',
            hovertemplate='<b>%{x}</b><br>인구수: %{y:.2f}천명<extra></extra>'
        )
        fig_pop.update_layout(
            height=400, 
            title_font=dict(size=14, color='black'), 
            font=dict(size=11, color='black'),
            xaxis_title="시간",
            yaxis_title="인구수 (천명)",
            xaxis={'categoryorder': 'array', 'categoryarray': sorted(df_pop["times"].unique())},
            xaxis_tickfont=dict(color='black', size=11),
            yaxis_tickfont=dict(color='black', size=11),
            xaxis_title_font=dict(color='black'),
            yaxis_title_font=dict(color='black'),
            plot_bgcolor='white',
            paper_bgcolor='white',
            margin=dict(l=10, r=10, t=40, b=10)
        )
        fig_pop.update_xaxes(showline=True, linewidth=1, linecolor='black', gridcolor='lightgray')
        fig_pop.update_yaxes(showline=True, linewidth=1, linecolor='black', gridcolor='lightgray')
        st.plotly_chart(fig_pop, use_container_width=True)
    
    with col2:
        if card_metric == "금액(amt)":
            hover_template = '<b>%{x}</b><br>금액: %{y:.2f}백만원<extra></extra>'
        else:
            hover_template = '<b>%{x}</b><br>건수: %{y:,.0f}건<extra></extra>'
        
        fig_card = px.bar(bar_df_card, x='times', y=card_col_display, 
                          title=f"{select_ym} {select_week} {select_name} {card_title}")
        fig_card.update_traces(
            marker_color='#4dabf7',
            hovertemplate=hover_template
        )
        fig_card.update_layout(
            height=400, 
            title_font=dict(size=14, color='black'), 
            font=dict(size=11, color='black'),
            xaxis_title="시간",
            yaxis_title=card_label,
            xaxis={'categoryorder': 'array', 'categoryarray': sorted(df_card["times"].unique())},
            xaxis_tickfont=dict(color='black', size=11),
            yaxis_tickfont=dict(color='black', size=11),
            xaxis_title_font=dict(color='black'),
            yaxis_title_font=dict(color='black'),
            plot_bgcolor='white',
            paper_bgcolor='white',
            margin=dict(l=10, r=10, t=40, b=10)
        )
        fig_card.update_xaxes(showline=True, linewidth=1, linecolor='black', gridcolor='lightgray')
        fig_card.update_yaxes(showline=True, linewidth=1, linecolor='black', gridcolor='lightgray')
        st.plotly_chart(fig_card, use_container_width=True)