# 버스 이용인구 현황
# 부산빅데이터혁신센터에서 수집 중인 데이터 수령하여 작업
# 저장공간이 부족하여 연도-분기단위로 집계처리

import glob
import pandas as pd
import geopandas as gpd
from tqdm import tqdm
import warnings
warnings.filterwarnings('ignore')

DATA_PATH = r"02_자료수집\\03_교통유동인구\\01_버스\\"
GPKG_PATH = r"2026-018_도시계획과.gpkg"
OUTPUT_PATH = r"03_집계결과\\"
months = [f"{y}{month:02d}" for y in range(2022, 2023) for month in range(1, 2)]
ten_sectors = gpd.read_file(GPKG_PATH, layer="10개_중심지_생활권", driver="GPKG")
gugun = gpd.read_file(GPKG_PATH, layer="NGII_SIG_26", driver="GPKG")
역세권350 = gpd.read_file(GPKG_PATH, layer="역세권350_74EA", driver="GPKG")
역세권500 = gpd.read_file(GPKG_PATH, layer="역세권500_58EA", driver="GPKG")

# 집계처리 함수생성
def sector_bustation(gdf2):
    print("2022년 교통카드(버스) 이용자 현황집계 시작")
    values = []
    for ym in tqdm(months):
        
        gdf1 = gpd.read_file(GPKG_PATH, layer=f"정류장위치정보_{ym[:4]}년", driver="GPKG")
        data_lists = glob.glob(DATA_PATH + rf"{ym}\\*.csv", recursive=True)
        for data in data_lists:
            df = pd.read_csv(data, dtype={'행데이터기준일자': str, '정류장코드': str, '탑승인원': int}, 
                                         encoding="utf-8")
            df['기준연도'] = df['행데이터기준일자'].str[:4] + "년"
            merged = pd.merge(df, gdf1, on='정류장코드', how='left')
            merged = gpd.GeoDataFrame(merged, geometry=gpd.points_from_xy(merged['X'], merged['Y']), crs=5179)
            values.append(gpd.sjoin(gdf2, merged, how="inner", predicate="intersects"))
    concated = pd.concat(values, ignore_index=True)
    pivoted = pd.pivot_table(concated, index=['기준연도','운영기관'], columns='CNAME',
                                         values='탑승인원', aggfunc='sum', fill_value=0).reset_index()
    print("2022년 교통카드(버스) 이용자 현황집계 종료")
    return pivoted

sector_bustation(ten_sectors).to_excel(OUTPUT_PATH + "3_10개 중심지 생활권_버스 이용인구 현황_2022.xlsx",
                                       engine="openpyxl", index=False)
