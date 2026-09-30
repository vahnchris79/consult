
# 유동인구 집계

import pandas as pd
import geopandas as gpd
from impala.dbapi import connect
from tqdm import tqdm
import calendar
import warnings
warnings.filterwarnings('ignore')

GPKG_PATH = r"02_자료수집\\2026-018_도시계획과.gpkg"
FILES_PATH = r"D:\\02_사업관리\\자체분석\\"
OUTPUT_PATH = r"03_집계결과\\"
conn = connect(host="172.20.192.154", port=10000, user="datawave", database="purchase_data", 
               auth_mechanism="PLAIN")
months1 = [f"{y}{month:02d}" for y in range(2021, 2023) for month in range(1, 13)]
months2 = [f"{y}{month:02d}" for y in range(2025, 2026) for month in range(1, 13)]
ten_sectors = gpd.read_file(GPKG_PATH, layer="10개_중심지_생활권")
gugun = gpd.read_file(GPKG_PATH, layer="NGII_SIG_26")
역세권350 = gpd.read_file(GPKG_PATH, layer="역세권350_74EA")
역세권500 = gpd.read_file(GPKG_PATH, layer="역세권500_58EA")
grid50_pg = gpd.read_file(FILES_PATH + r"04_공간DB\\griddata\\busan_50cell_v15.shp", crs=5179)
grid50_pg['x'] = grid50_pg.geometry.centroid.x.round(3)
grid50_pg['y'] = grid50_pg.geometry.centroid.y.round(3)
grid50_pt = gpd.GeoDataFrame(grid50_pg, geometry=gpd.points_from_xy(grid50_pg.x, grid50_pg.y))
grid100_pg = gpd.read_file(FILES_PATH + r"04_공간DB\\griddata\\ngii_100m_busan.shp", crs=5179)
grid100_pg['x'] = grid100_pg.geometry.centroid.x.round(3)
grid100_pg['y'] = grid100_pg.geometry.centroid.y.round(3)
grid100_pt = gpd.GeoDataFrame(grid100_pg, geometry=gpd.points_from_xy(grid100_pg.x, grid100_pg.y))
ranges = ['심야2','오전1','오전2','오후1','오후2','심야1']
hour_to_range = {h: ranges[h // 4] for h in range(24)}

# 연도별 일수 데이터 프레임 생성
results = []
for year in range(2019, 2026):
    for month in range(1, 13):
        std_ym = str(year) + f"{month:02d}"
        daycnt = calendar.monthrange(year, month)[1]
        results.append({'기준연월': std_ym, '월별일수': daycnt})
monthly = pd.DataFrame(results)
monthly['기준연도'] = monthly['기준연월'].str[:4] + "년"
yearly = monthly.groupby('기준연도')['월별일수'].sum().reset_index(name='연별일수')

# 10개 중심지 생활권별 생활인구(2021년~2022년)
def sectors_lifepop(conn, grid1, gdf2):
    values = []
    for ym in tqdm(months1):
        query = f"""SELECT * FROM purchase_data.l0csv_kt_d_lifepop_time_p WHERE SUBSTR(std_ymd, 1, 6) = '{ym}'"""
        df = pd.read_sql(query, conn)
        df.columns = [col.split('.')[1] for col in df.columns]
        df.drop(['dat_flow_id','part_batchdate'], axis=1, inplace=True)
        cols = [col for col in df.columns if '_t_' in col]
        df[cols] = df[cols].astype(float)
        df['기준연도'] = df['std_ymd'].str[:4] + "년"
        df = pd.merge(df, grid1, on="id", how="inner")
        gdf = gpd.GeoDataFrame(df, geometry="geometry")
        gdf['주거'] = gdf.loc[:, 'h_t_00':'h_t_23'].sum(axis=1) / 24
        gdf['직장'] = gdf.loc[:, 'w_t_00':'w_t_23'].sum(axis=1) / 24
        gdf['방문'] = gdf.loc[:, 'v_t_00':'v_t_23'].sum(axis=1) / 24
        gdf['생활'] = gdf['주거'] + gdf['직장'] + gdf['방문']
        sjoined = gpd.sjoin(gdf2, gdf, how="inner", predicate="intersects")
        values.append(sjoined.groupby(['기준연도','CNAME'], as_index=False)['생활'].sum().round())
    concated = pd.concat(values, ignore_index=True)
    pivoted = concated.pivot_table(index='기준연도', columns='CNAME', values='생활', aggfunc='sum').reset_index()
    conn.close()
    return pivoted

# 10개 중심지 생활권 생활인구(2023년~2025년)
def sectors_livingpop(conn, grid1, gdf2):
    values = []
    for ym in tqdm(months2):
        query = f"""SELECT * FROM purchase_data.l0kte_kt_d_living_tme_p2 WHERE SUBSTR(std_ymd, 1, 6) = '{ym}'"""
        df = pd.read_sql(query, conn)
        df.columns = [col.split('.')[1] for col in df.columns]
        df.drop(['dat_flow_id','part_batchdate'], axis=1, inplace=True)
        cols = [col for col in df.columns if '_t_' in col]
        df[cols] = df[cols].astype(float)
        df['기준연도'] = df['std_ymd'].str[:4] + "년"
        df = pd.merge(df, grid1, left_on="id", right_on="gid", how="inner")
        gdf = gpd.GeoDataFrame(df, geometry="geometry")
        gdf['주거'] = gdf.loc[:, 'h_t_00':'h_t_23'].sum(axis=1) / 24
        gdf['직장'] = gdf.loc[:, 'w_t_00':'w_t_23'].sum(axis=1) / 24
        gdf['방문'] = gdf.loc[:, 'v_t_00':'v_t_23'].sum(axis=1) / 24
        gdf['생활'] = gdf['주거'] + gdf['직장'] + gdf['방문']
        sjoined = gpd.sjoin(gdf2, gdf, how="inner", predicate="intersects")
        values.append(sjoined.groupby(['기준연도','CNAME'], as_index=False)['생활'].sum().round())
    concated = pd.concat(values, ignore_index=True)
    pivoted = concated.pivot_table(index='기준연도', columns='CNAME', values='생활', aggfunc='sum').reset_index()
    conn.close()
    return pivoted

# 구군별 생활인구(2019년~2022년)
def gugun_lifepop(conn, gdf2):
    values = []
    for ym in tqdm(months1):
        query = f"""SELECT * FROM purchase_data.l0csv_kt_d_lifepop_time WHERE SUBSTR(std_ymd, 1, 6) = '{ym}'"""
        df = pd.read_sql(query, conn)
        df.columns = [col.split('.')[1] for col in df.columns]
        df.rename(columns={'time': '시간'}, inplace=True)
        df.drop(['dat_flow_id','part_batchdate'], axis=1, inplace=True)
        cols = [col for col in df.columns if '_pop' in col]
        df[cols] = df[cols].astype(float)
        df['기준연도'] = df['std_ymd'].str[:4] + "년"
        df['시간대'] = df['시간'].astype(int).map(hour_to_range)
        df['SIG_CD'] = df['hcode'].str[:5]
        df = pd.merge(df, gdf2[['SIG_CD','SIG_KOR_NM']], on="SIG_CD", how="left")
        df['생활(일합계)'] = df.loc[:, 'h_pop':'v_pop'].sum(axis=1)
        values.append(df.groupby(['기준연도','SIG_CD','SIG_KOR_NM','시간','시간대']
                                 )['생활(일합계)'].sum().round().reset_index(name="생활(연합계)").sort_values(['기준연도','SIG_CD','시간'], ascending=True))
    concated = pd.concat(values, ignore_index=True)
    concated = pd.merge(concated, yearly, on="기준연도")
    concated['생활(연평균)'] = (concated['생활(연합계)'] / concated['연별일수']).round()
    pivoted = concated.pivot_table(index=['기준연도','시간','시간대'], columns='SIG_KOR_NM', values='생활(연평균)').reset_index()
    conn.close()
    return pivoted

# 구군별 생활인구(2023년~2025년)
def gugun_livingpop(conn, gdf2):
    values = []
    for ym in tqdm(months2):
        query = f"""SELECT * FROM purchase_data.l0kte_kt_d_living_tme WHERE SUBSTR(std_ymd, 1, 6) = '{ym}'"""
        df = pd.read_sql(query, conn)
        df.columns = [col.split('.')[1] for col in df.columns]
        df.rename(columns={'tme': '시간'}, inplace=True)
        df.drop(['dat_flow_id','part_batchdate'], axis=1, inplace=True)
        cols = [col for col in df.columns if '_pop' in col]
        df[cols] = df[cols].astype(float)
        df['기준연도'] = df['std_ymd'].str[:4] + "년"
        df['SIG_CD'] = df['hcode'].str[:5]
        df['시간대'] = df['시간'].astype(int).map(hour_to_range)
        df = pd.merge(df, gdf2[['SIG_CD','SIG_KOR_NM']], on="SIG_CD", how="left")
        df['생활(일합계)'] = df.loc[:, 'h_pop':'v_pop'].sum(axis=1)
        values.append(df.groupby(['기준연도','SIG_CD','SIG_KOR_NM','시간','시간대']
                                 )['생활(일합계)'].sum().round().reset_index(name='생활(연합계)').sort_values(['기준연도','SIG_CD','시간'], ascending=True))
    concated = pd.concat(values, ignore_index=True)
    concated = pd.merge(concated, yearly, on="기준연도")
    concated['생활(연평균)'] = (concated['생활(연합계)'] / concated['연별일수']).round()
    pivoted = concated.pivot_table(index=['기준연도','시간','시간대'], columns='SIG_KOR_NM', values='생활(연평균)').reset_index()
    conn.close()
    return pivoted

# 역세권 생활인구(2019년~2022년)
def station_lifepop(conn, grid1, gdf2):
    values = []
    for ym in tqdm(months1):
        query = f"""SELECT * FROM purchase_data.l0csv_kt_d_lifepop_time_p WHERE SUBSTR(std_ymd, 1, 6) = '{ym}'"""
        df = pd.read_sql(query, conn)
        df.columns = [col.split('.')[1] for col in df.columns]
        df.drop(['dat_flow_id','part_batchdate'], axis=1, inplace=True)
        cols = [col for col in df.columns if '_t_' in col]
        df[cols] = df[cols].astype(float)
        df['기준연도'] = df['std_ymd'].str[:4] + "년"
        df = pd.merge(df, grid1, on="id", how="inner")
        gdf = gpd.GeoDataFrame(df, geometry="geometry")
        gdf['주거'] = gdf.loc[:, 'h_t_00':'h_t_23'].sum(axis=1) / 24
        gdf['직장'] = gdf.loc[:, 'w_t_00':'w_t_23'].sum(axis=1) / 24
        gdf['방문'] = gdf.loc[:, 'v_t_00':'v_t_23'].sum(axis=1) / 24
        gdf['생활(일합계)'] = gdf['주거'] + gdf['직장'] + gdf['방문']
        sjoined = gpd.sjoin(gdf2, gdf, how="inner", predicate="intersects")
        values.append(sjoined.groupby(['기준연도','역세권','역명']
                                      )['생활(일합계)'].sum().round().reset_index(name="생활(연합계)").sort_values(['기준연도'], ascending=True))
    concated = pd.concat(values, ignore_index=True)
    pivoted = concated.pivot_table(index=['기준연도','역세권'], columns='역명', values='생활(연합계)').reset_index()
    conn.close()
    return pivoted

# 역세권 생활인구(2023년~2025년)
def station_livingpop(conn, grid1, gdf2):
    values = []
    for ym in tqdm(months2):
        query = f"""SELECT * FROM purchase_data.l0kte_kt_d_living_tme_p2 WHERE SUBSTR(std_ymd, 1, 6) = '{ym}'"""
        df = pd.read_sql(query, conn)
        df.columns = [col.split('.')[1] for col in df.columns]
        df.drop(['dat_flow_id','part_batchdate'], axis=1, inplace=True)
        cols = [col for col in df.columns if '_t_' in col]
        df[cols] = df[cols].astype(float)
        df['기준연도'] = df['std_ymd'].str[:4] + "년"
        df = pd.merge(df, grid1, left_on="id", right_on="gid", how="inner")
        gdf = gpd.GeoDataFrame(df, geometry="geometry")
        gdf['주거'] = gdf.loc[:, 'h_t_00':'h_t_23'].sum(axis=1) / 24
        gdf['직장'] = gdf.loc[:, 'w_t_00':'w_t_23'].sum(axis=1) / 24
        gdf['방문'] = gdf.loc[:, 'v_t_00':'v_t_23'].sum(axis=1) / 24
        gdf['생활(일합계)'] = gdf['주거'] + gdf['직장'] + gdf['방문']
        sjoined = gpd.sjoin(gdf2, gdf, how="inner", predicate="intersects")
        values.append(sjoined.groupby(['기준연도','역세권','역명']
                                      )['생활(일합계)'].sum().round().reset_index(name='생활(연합계)').sort_values(['기준연도'], ascending=True))
    concated = pd.concat(values, ignore_index=True)
    pivoted = concated.pivot_table(index=['기준연도','역세권'], columns='역명', values='생활(연합계)').reset_index()
    conn.close()
    return pivoted

# pd.concat([sectors_lifepop(conn, grid50_pt, ten_sectors),
#            sectors_livingpop(conn, grid100_pt, ten_sectors)],
#            ignore_index=True).to_excel(OUTPUT_PATH + "3_기준연도_10개 중심지 생활권_생활인구 현황.xlsx", engine="openpyxl", index=False)

# pd.concat([gugun_lifepop(conn, gugun),
#            gugun_livingpop(conn, gugun)],
#            ignore_index=True).to_excel(OUTPUT_PATH + "3_기준연도_구군_생활인구 현황.xlsx", engine="openpyxl", index=False)

# station_lifepop(conn, grid50_pt, 역세권350).to_excel(OUTPUT_PATH + "3_기준연도_역세권350_생활인구 현황_2021-2022.xlsx", 
#                                                      engine="openpyxl", index=False)
# station_livingpop(conn, grid100_pt, 역세권350).to_excel(OUTPUT_PATH + "3_기준연도_역세권350_생활인구 현황_2025.xlsx",
#                                                         engine="openpyxl", index=False)

station_lifepop(conn, grid50_pt, 역세권500).to_excel(OUTPUT_PATH + "3_기준연도_역세권500_생활인구 현황_2021-2022.xlsx",
                                                     engine="openpyxl", index=False)
# station_livingpop(conn, grid100_pt, 역세권500).to_excel(OUTPUT_PATH + "3_기준연도_역세권500_생활인구 현황_2023-2024.xlsx",
#                                                         engine="openpyxl", index=False)
station_livingpop(conn, grid100_pt, 역세권500).to_excel(OUTPUT_PATH + "3_기준연도_역세권500_생활인구 현황_2025.xlsx",
                                                        engine="openpyxl", index=False)
