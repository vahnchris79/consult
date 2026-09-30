import geopandas as gpd
import pandas as pd
from shapely import wkt

inputDataframe = inputs[0]
g050 = inputs[1]
g100 = inputs[2]

result = inputDataframe
result['std_ymd'] = pd.to_datetime(result['std_ymd'], format="%Y-%m-%d").astype(str)
result['std_ym'] = result['std_ymd'].str[:7]

g050['geometry'] = g050['geometry'].apply(wkt.loads)
grid050 = gpd.GeoDataFrame(g050, geometry='geometry', crs="EPSG:5179")
grid050['x'] = grid050.geometry.centroid.x
grid050['y'] = grid050.geometry.centroid.y
g100['geometry'] = g100['geometry'].apply(wkt.loads)
grid100 = gpd.GeoDataFrame(g100, geometry='geometry', crs="EPSG:5179")

result = pd.merge(result, grid050[['id', 'x', 'y']], how="left", on="id").drop(columns=['dat_flow_id','part_batchdate'])
gdf = gpd.GeoDataFrame(result, geometry=gpd.points_from_xy(result['x'], result['y'], crs="EPSG:5179"))
df = pd.DataFrame(gpd.sjoin(gdf, grid100, how="inner", predicate="intersects")).drop(columns=['id','geometry','x','y'])

cols = [col for col in df.columns if 'h_m' in col or 'h_w' in col or 'w_m' in col or 'w_w' in col or 'v_m' in col or 'v_w' in col]
df[cols] = df[cols].astype('float32')

age_bins = {'0009': '0009', '1014': '1019', '1519': '1019', '2024': '2029', '2529': '2029',
            '3034': '3039', '3539': '3039', '4044': '4049', '4549': '4049', '5054': '5059',
            '5559': '5059', '6064': '6069', '6569': '6069', '7000': '70up'}
age_groups_10 = ['0009', '1019', '2029', '3039', '4049', '5059', '6069', '70up']
prefixes = ['h_m', 'h_w', 'w_m', 'w_w', 'v_m', 'v_w']
for p in prefixes:
    for new_age in age_groups_10:
        cols_sum = [f'{p}_{age}' for age, bin_label in age_bins.items() if bin_label == new_age]
        df[f'{p}_{new_age}'] = df[cols_sum].sum(axis=1)
        df[f'{p}_{new_age}_sum'] = df[f'{p}_{new_age}']

# 집계 연산 최적화
agg_dict = {f"{p}_{new_age}_sum": "sum" for p in prefixes for new_age in age_groups_10}
agg_dict.update({"std_ymd": "nunique"})

grouped = df.groupby(['std_ym','hcode','gid']).agg(agg_dict).reset_index()
grouped = grouped.rename(columns={'std_ymd': 'day_cnt'})
    
# 일평균 계산
for p in prefixes:
    for new_age in age_groups_10:
        grouped[f'{p}_{new_age}'] = grouped[f"{p}_{new_age}_sum"] / grouped["day_cnt"]

grouped = grouped.drop(columns=[f"{p}_{new_age}_sum" for p in prefixes for new_age in age_groups_10] + ['day_cnt'])
grouped = grouped.sort_values(by=['std_ym','hcode','gid'])