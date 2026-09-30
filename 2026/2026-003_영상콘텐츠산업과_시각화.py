import pandas as pd
import geopandas as gpd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import warnings

# 지리적 경고 및 권장 경고 무시
warnings.filterwarnings('ignore')

# 1. 경로 및 키 설정
data_path = r"D:\02_사업관리\2026년\05_사업관리\데이터 분석 컨설팅\20260119_영상콘텐츠산업과\\"
vworld_key = "326A4FCA-0A3C-3CD1-83FD-A30126D77357".strip()
gpkg_file = "2026-001_데이터 분석 컨설팅 데이터.gpkg"

# 2. 데이터 로드 및 전처리 함수
def load_and_filter(layer_name, target_loc, target_month):
    gdf = gpd.read_file(data_path + gpkg_file, layer=layer_name)
    
    # 기준연월에서 월 추출
    gdf['기준연월'] = gdf['기준연월'].astype(str)
    gdf['월'] = gdf['기준연월'].str[-2:] + "월"
    
    # 필터링: 위치와 월 기준
    filtered = gdf[(gdf['위치'] == target_loc) & (gdf['월'] == target_month)].copy()
    
    if filtered.empty:
        return filtered, None

    # 중심점 좌표 추출 (상시 숫자 표시용)
    temp_gdf = filtered.to_crs(epsg=3857)
    filtered['longitude'] = temp_gdf.geometry.centroid.to_crs(epsg=4326).x
    filtered['latitude'] = temp_gdf.geometry.centroid.to_crs(epsg=4326).y
    
    # gid 문자열 변환 및 GeoJSON 생성
    filtered['gid'] = filtered['gid'].astype(str)
    
    # 지도용 집계 (월/격자 기준 -> 24시간 평균)
    map_data = filtered.groupby(['gid']).agg({
        '유입인구수': 'sum',
        'longitude': 'first',
        'latitude': 'first',
        'geometry': 'first'
    }).reset_index()
    
    map_data = gpd.GeoDataFrame(map_data, geometry='geometry', crs=4326)
    map_data['avg_val'] = (map_data['유입인구수'] / 24).round()
    map_data['pop_label'] = map_data['avg_val'].apply(lambda x: f"{int(x):,}")
    
    # GeoJSON ID 매핑
    geo_json = json.loads(map_data.to_json())
    for feature in geo_json['features']:
        feature['id'] = feature['properties']['gid']
        
    return filtered, (map_data, geo_json)

# 3. 메인 시각화 생성 함수
def create_combined_dashboard(target_loc, target_month):
    # 레이어 로드
    df_other, map_info_other = load_and_filter("월별_100m_시간대_유입인구_타시도", target_loc, target_month)
    df_local, map_info_local = load_and_filter("월별_100m_시간대_유입인구_부울경", target_loc, target_month)

    # 2행 2열 서브플롯 설정
    fig = make_subplots(
        rows=2, cols=2,
        column_widths=[0.5, 0.5],
        row_heights=[0.5, 0.5],
        specs=[[{"type": "map"}, {"type": "xy"}],
               [{"type": "map"}, {"type": "xy"}]],
        subplot_titles=(
            f"타시도 유입 공간분포 ({target_loc}, {target_month})", "타시도 시간대별 유입추이",
            f"부울경 유입 공간분포 ({target_loc}, {target_month})", "부울경 시간대별 유입추이"
        ),
        vertical_spacing=0.12,
        horizontal_spacing=0.08
    )

    def add_layers_to_subplot(df, map_info, row):
        if df.empty or map_info is None:
            return
        
        map_data, geo_json = map_info
        
        # [좌측] 격자 히트맵
        fig.add_trace(go.Choroplethmap(
            geojson=geo_json, locations=map_data['gid'], z=map_data['avg_val'],
            colorscale='Reds', marker_opacity=0.35, marker_line_width=0.6,
            showscale=True,
            colorbar=dict(title='인구', x=0.46, len=0.4, y=0.78 if row==1 else 0.22),
            hoverinfo='skip'), row=row, col=1)

        # [좌측] 격자 위 숫자 상시 표시
        fig.add_trace(go.Scattermap(
            lat=map_data['latitude'], lon=map_data['longitude'],
            mode='text',
            text=map_data['pop_label'],
            textfont=dict(size=10, color='black', family="Arial Black"),
            hoverinfo='skip'
        ), row=row, col=1)

        # [우측] 선형 그래프
        chart_data = df.groupby(['시간대', '유입지명'])['유입인구수'].sum().reset_index().sort_values('시간대')
        for origin in chart_data['유입지명'].unique():
            sub = chart_data[chart_data['유입지명'] == origin]
            fig.add_trace(go.Scatter(
                x=sub['시간대'], y=sub['유입인구수'],
                mode='lines+markers',
                name=origin,
                legendgroup=f"row{row}",
                legendgrouptitle_text="유입지" if row==1 else "유입지(부울경)"
            ), row=row, col=2)

    # 상단 및 하단 레이어 추가
    add_layers_to_subplot(df_other, map_info_other, 1)
    add_layers_to_subplot(df_local, map_info_local, 2)

    # 레이아웃 및 배경지도 설정
    vworld_url = f"https://api.vworld.kr/req/wmts/1.0.0/{vworld_key}/Base/{{z}}/{{y}}/{{x}}.png"
    
    # 맵 설정 업데이트
    map_config = {
        "style": "white-bg",
        "layers": [{"below": 'traces', "sourcetype": "raster", "source": [vworld_url]}],
        "zoom": 14.5
    }

    fig.update_layout(
        height=1000,
        width=1500,
        template="plotly_white",
        map=dict(**map_config, center=dict(lat=map_info_other[0]['latitude'].mean(), lon=map_info_other[0]['longitude'].mean()) if map_info_other else dict(lat=35.1, lon=129)),
        map2=dict(**map_config, center=dict(lat=map_info_local[0]['latitude'].mean(), lon=map_info_local[0]['longitude'].mean()) if map_info_local else dict(lat=35.1, lon=129)),
        margin=dict(t=20, b=20, l=20, r=20),
        legend=dict(groupclick="togglegroup")
    )
    
    fig.update_xaxes(title_text="시간대", dtick=2, row=1, col=2)
    fig.update_xaxes(title_text="시간대", dtick=2, row=2, col=2)
    fig.update_yaxes(title_text="유입인구 합계", tickformat=",", row=1, col=2)
    fig.update_yaxes(title_text="유입인구 합계", tickformat=",", row=2, col=2)

    return fig

# 4. 분석 실행 (원하는 위치와 월 설정)
target_location = "부산영화체험박물관" # 부산영화체험박물관, 상상마당, 유라시아플랫폼, 해운대플랫폼 중 선택
target_month = "01월" # 01월 ~ 12월 중 선택

final_fig = create_combined_dashboard(target_location, target_month)

# 결과 출력 (브라우저)
final_fig.show()

# 이미지 파일로 저장 (kaleido 라이브러리 필요: pip install kaleido)
# final_fig.write_image(f"analysis_{target_location}_{target_month}.png")