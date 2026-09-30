import geopandas as gpd
import pandas as pd
from shapely import wkt

inputDataframe = inputs[0]
g050 = inputs[1]
g100 = inputs[2]

result = inputDataframe
result['std_ymd'] = pd.to_datetime(result['std_ymd'], format="%Y-%m-%d").astype(str)
result['std_ym'] = result['std_ymd'].str[:7]

# 연령그룹 및 컬럼정의
age_groups = ['0009','1014','1519','2024','2529','3034','3539',
              '4044','4549','5054','5559','6064','6569','7000']
prefixes = ['h_m', 'h_w', 'w_m', 'w_w', 'v_m', 'v_w']
all_cols = [f"{p}_{age}" for p in prefixes for age in age_groups]

# dtype 변환 최적화
result[all_cols] = result[all_cols].astype('float32')

# 50m, 100m 격자 GeoDataFrame 변환
g050['geometry'] = g050['geometry'].apply(wkt.loads)
grid050 = gpd.GeoDataFrame(g050, geometry='geometry', crs="EPSG:5179")
grid050['x'] = grid050.geometry.centroid.x
grid050['y'] = grid050.geometry.centroid.y
g100['geometry'] = g100['geometry'].apply(wkt.loads)
grid100 = gpd.GeoDataFrame(g100, geometry='geometry', crs="EPSG:5179")

# 50m격자 정보 병합
result = pd.merge(result, grid050[['id', 'x', 'y', 'geometry']], how="left", on="id")
gdf = gpd.GeoDataFrame(result, geometry=gpd.points_from_xy(result['x'], result['y'], crs="EPSG:5179"))

# 100m격자와 공간조인
df = gpd.sjoin(gdf, grid100, how="inner", predicate="intersects").drop(columns='geometry')

# 컬럼별 합산
for p in prefixes:
    df[f"{p}_sum"] = df[[f"{p}_{age}" for age in age_groups]].sum(axis=1)

# 집계 연산 최적화 (오류 해결)
agg_dict = {f"{p}_sum": "sum" for p in prefixes}
agg_dict.update({"std_ymd": "nunique"})
grouped = df.groupby(['std_ym','hcode','gid']).agg(agg_dict).reset_index().rename(columns={'std_ymd': 'day_cnt'})
    
# 일평균 계산
for p in prefixes:
    grouped[p] = grouped[f"{p}_sum"] / grouped["day_cnt"]

grouped = grouped.drop(columns=[f"{p}_sum" for p in prefixes] + ['day_cnt']).sort_values(by=['std_ym', 'hcode', 'gid'])