
import pandas as pd
import geopandas as gpd
import glob

data_path = glob.glob("02_집계결과/*.csv")
output_files = "(2025-034) 데이터 분석 컨설팅 데이터.gpkg"
centroids = gpd.read_file("(2025-034) 데이터 분석 컨설팅 데이터.gpkg", layer='centroids', driver="GPKG").drop(columns=['pop'])
centroids['x'] = centroids.geometry.centroid.x.round(3)
centroids['y'] = centroids.geometry.centroid.y.round(3)

for data in data_path:
    print(f"{data[8:].split('.')[0]} 전처리 시작")
    df = pd.read_csv(data, encoding="utf-8", dtype={'std_yr': str, 'hcode': str, 'id': str}, low_memory=False)
    df = df.loc[df['pop'] > 0.4].copy()
    df['pop2'] = round(df['pop'])
    merged = df.merge(centroids, how="left", on="id")
    merged = merged[['std_yr', 'id', 'times2', 'pop2', 'geometry']]
    gdf = gpd.GeoDataFrame(merged, geometry='geometry', crs=5179).to_file(output_files, layer=data[8:].split('.')[0], driver="GPKG")
    print(f"{data[8:].split('.')[0]} 전처리 완료")

