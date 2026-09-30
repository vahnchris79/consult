import pandas as pd
import geopandas as gpd
from tqdm import tqdm

REF_PATH = r"D:\\02_사업관리\\자체분석\\"

grid50_pg = gpd.read_file(REF_PATH + r"04_공간DB\\griddata\\busan_50cell_v15.shp").set_crs(5179)
grid50_pg['X'] = grid50_pg.geometry.centroid.x.round(3)
grid50_pg['Y'] = grid50_pg.geometry.centroid.y.round(3)
grid50_pt = gpd.GeoDataFrame(grid50_pg, geometry=gpd.points_from_xy(grid50_pg['X'], grid50_pg['Y']))
grid100_pg = gpd.read_file(REF_PATH + r"04_공간DB\\griddata\\ngii_100m_busan.shp").to_crs(5179)
emd26710 = gpd.read_file(r"2026-022_26710_CCTV.gpkg", layer="EMD26710")
grid100pg_26710 = gpd.overlay(grid100_pg, emd26710, how="intersection", keep_geom_type=True)
grid100pg_26710.drop(columns=['EMD_ENG_NM'], inplace=True)
hjdong = pd.read_csv(REF_PATH + r"05_코드자료\\부산행정동코드.csv", dtype={'hcode': str}, encoding="utf-8")
time_dicts = dict((f'{h:02d}H', [f'h_t_{h:02d}', f'w_t_{h:02d}', f'v_t_{h:02d}']) for h in range(24))
keys = [key for key in time_dicts.keys()]
slots = ['심야2','오전1','오전2','오후1','오후2','심야1']
time_ranges = {f'{h:02d}H': slots[h//4] for h in range(24)}

# 전처리 함수 생성
def aggregate_times(grid1, grid2):
    print("2022년~2026년 7월 기장군 시간대 행정동 생활인구 집계시작")
    for year in tqdm(range(2022, 2027)):
        df = pd.read_csv(REF_PATH + f"01_생활인구\\l0kte_kt_d_living_tme_p2_{year}.csv", sep="|", dtype={'std_ymd': str, 'hcode': str}, encoding="utf-8")
        df['std_year'] = df['std_ymd'].str[:4] + "년"
        df = pd.merge(df, hjdong, on="hcode", how="inner")
        if year == 2022 and str(year) in df['std_ymd'].str[:4].unique():
            df['id'] = df['id'].astype(str)
            merged = pd.merge(df, grid1, on="id", how="left")
            merged.drop(columns=['geometry'], inplace=True)
            merged = gpd.GeoDataFrame(merged, geometry=gpd.points_from_xy(merged.X, merged.Y)).set_crs(5179)
            sjoined = gpd.sjoin(grid2, merged, how="inner", predicate="intersects")
            for key, value in time_dicts.items():
                sjoined[key] = sjoined.loc[:, value].sum(axis=1) / 3
            agg_dict = {key: "sum" for key in time_dicts.keys()}
            keys = [key for key in time_dicts.keys()]
            groups = sjoined.dissolve(by=['std_year','hcode','hname','gid'],
                                                     aggfunc=agg_dict).reset_index().sort_values(by=['std_year','hcode'],
                                                                                                 ascending=True)
            melts = groups.melt(id_vars=['std_year','hname','gid','geometry'], value_vars=keys, var_name='times', value_name='pop')
            melts['시간대'] = melts['times'].map(time_ranges)
            melts = melts[['std_year','hname','gid','times','시간대','pop','geometry']]
            melts.rename(columns={'std_year': '기준연도', 'hname': '행정동명', 'gid': '100MGID',
                                  'times': '특정시간', '시간대': '시간분류', 'pop': '생활인구'}, inplace=True)
            melts.to_file(r"2026-022_26710_CCTV.gpkg", layer=f"100m_hjdong_pop_{year}", driver="GPKG")
            
        if  year >= 2023 and str(year) in df['std_ymd'].str[:4].unique():
            print(f"{year}년 기장군 시간대 행정동 생활인구 집계시작")
            merged = pd.merge(df, grid2, left_on="id", right_on="gid", how="left")
            for key, value in time_dicts.items():
                merged[key] = merged.loc[:, value].sum(axis=1) / 3
            agg_dict = {key: "sum" for key in time_dicts.keys()}
            keys = [key for key in time_dicts.keys()]
            groups = sjoined.dissolve(by=['std_year','hcode','hname','gid'],
                                                     aggfunc=agg_dict).reset_index().sort_values(by=['std_year','hcode'],
                                                                                                 ascending=True)
            melts = groups.melt(id_vars=['std_year','hname','gid','geometry'], value_vars=keys, var_name='times', value_name='pop')
            melts['시간대'] = melts['times'].map(time_ranges)
            melts = melts[['std_year','hname','gid','times','시간대','pop','geometry']]
            melts.rename(columns={'std_year': '기준연도', 'hname': '행정동명', 'gid': '100MGID', 
                                  'times': '특정시간', '시간대': '시간분류', 'pop': '생활인구'}, inplace=True)
            melts.to_file(r"2026-022_26710_CCTV.gpkg", layer=f"100m_hjdong_pop_{year}", driver="GPKG")
        print("2022년~2026년 7월 기장군 시간대 행정동 생활인구 집계완료")

aggregate_times(grid50_pt, grid100_pg)