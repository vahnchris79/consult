from impala.dbapi import connect
from tqdm import tqdm
import pandas as pd
import geopandas as gpd
import warnings
warnings.filterwarnings('ignore')

DATA_PATH = r"D:\\02_사업관리\\2026년\\데이터 분석 컨설팅\\20260729_중소상공인지원과\\"
OUTPUT_PATH = r"D:\\02_사업관리\\2026년\\데이터 분석 컨설팅\\20260729_중소상공인지원과\\02_집계결과\\"

conn = connect(host="172.20.192.154", port=10000, user="datawave", database="purchase_data", auth_mechanism="PLAIN")
grid50_pg = gpd.read_file(r"D:\\02_사업관리\\자체분석\\04_공간DB\\griddata\\busan_50cell_v15.shp", crs=5179)
grid50_pg['x'] = grid50_pg.geometry.centroid.x.round(3)
grid50_pg['y'] = grid50_pg.geometry.centroid.y.round(3)
grid50_pt = gpd.GeoDataFrame(grid50_pg, geometry=gpd.points_from_xy(grid50_pg.x, grid50_pg.y))
grid100_pg = gpd.read_file(r"D:\\02_사업관리\\자체분석\\04_공간DB\\griddata\\ngii_100m_busan.shp", crs=5179)
grid100_pg['x'] = grid100_pg.geometry.centroid.x.round(3)
grid100_pg['y'] = grid100_pg.geometry.centroid.y.round(3)
grid100_pt = gpd.GeoDataFrame(grid100_pg, geometry=gpd.points_from_xy(grid100_pg.x, grid100_pg.y))
grid100_mrkt = gpd.read_file(DATA_PATH + r"01_신청내용\\(동남지방데이터청)골목상권25개\\골목상권25개.shp", crs=5179)
weekday_order = ['월', '화', '수', '목', '금', '토', '일']

# 2021년~2025년 성연령 생활인구를 골목상권 25개 영역기준으로 추출
# 연도와 테이블 이름 변경
# 2021, 2022: l0csv_kt_d_lifepop_sex_age_p, l0csv_kt_d_lifepop_time_p
# 2023, 2024, 2025: l0kte_kt_d_living_emd_p2, l0csv_kt_d_living_tme_p2

# 대상기간 리스트 생성
months1 = [f"{y}{month:02d}" for y in range(2021, 2023) for month in range(1, 13)]
months2 = [f"{y}{month:02d}" for y in range(2023, 2026) for month in range(1, 13)]
excluded = ('26170','26200','26440','26710')

# 성, 연령, 요일, 시간 집계함수
def aggregate_gender1(conn, pt1, grid):
    print("2021년~2022년 상권별 성별 생활인구 집계시작")
    values = []
    for ym in tqdm(months1):
        query= f"""SELECT * FROM purchase_data.l0csv_kt_d_lifepop_sex_age_p
                         WHERE SUBSTR(std_ymd, 1, 6) IN ('{ym}') AND SUBSTR(hcode,1,5) NOT IN {excluded}"""
        df = pd.read_sql(query, conn)
        df.columns = [col.split('.')[1] for col in df.columns]
        df.drop(['dat_flow_id','part_batchdate'], axis=1, inplace=True)
        cols = [col for col in df.columns if '_m_' in col or '_w_' in col or '_t_' in col]
        df[cols] = df[cols].astype(float)
        df['year'] = df['std_ymd'].astype('datetime64[ns]').astype(str).str[:4] + "년"
        df = pd.merge(pt1, df, on="id", how="left")
        gdf = gpd.GeoDataFrame(df, geometry="geometry")
        sjoined = gpd.sjoin(grid, gdf, how="inner", predicate="intersects")
        gender_dict = {
            '남성': [col for col in sjoined.columns if '_m_' in col],
            '여성': [col for col in sjoined.columns if '_w_' in col]}
        for key, value in gender_dict.items():
            sjoined[key] = sjoined.loc[:, value].sum(axis=1) / 24
        keys = [key for key in gender_dict.keys()]
        values.append(sjoined.groupby(['saup_yr','상권명','year'],
                                      as_index=False)[keys].sum().round().sort_values(['saup_yr','year'], ascending=True))
    concated = pd.concat(values, ignore_index=True)
    concated.columns = ['사업연도','상권명','기준연도','남성','여성']
    print("2021년~2022년 상권별 성별 생활인구 집계완료")
    conn.close()
    return concated

def aggregate_ages1(conn, pt1, grid):
    print("2021년~2022년 상권별 연령 생활인구 집계시작")
    values = []
    for ym in tqdm(months1):
        query= f"""SELECT * FROM purchase_data.l0csv_kt_d_lifepop_sex_age_p
        WHERE SUBSTR(std_ymd, 1, 6) IN ('{ym}') AND SUBSTR(hcode,1,5) NOT IN {excluded}"""
        df = pd.read_sql(query, conn)
        df.columns = [col.split('.')[1] for col in df.columns]
        df.drop(['dat_flow_id','part_batchdate'], axis=1, inplace=True)
        cols = [col for col in df.columns if '_m_' in col or '_w_' in col or '_t_' in col]
        df[cols] = df[cols].astype(float)
        df['year'] = df['std_ymd'].astype('datetime64[ns]').astype(str).str[:4] + "년"
        df = pd.merge(pt1, df, on="id", how="left")
        gdf = gpd.GeoDataFrame(df, geometry="geometry")
        sjoined = gpd.sjoin(grid, gdf, how="inner", predicate="intersects")
        ages_dict = {
            '10대이하': [col for col in sjoined.columns if col.endswith(('_0009','_1014','_1519'))],
            '20대': [col for col in sjoined.columns if col.endswith(('_2024','_2529'))],
            '30대': [col for col in sjoined.columns if col.endswith(('_3034','_3539'))],
            '40대': [col for col in sjoined.columns if col.endswith(('_4044','_4549'))],
            '50대': [col for col in sjoined.columns if col.endswith(('_5054','_5559'))],
            '60대이상': [col for col in sjoined.columns if col.endswith(('_6064','_6569','_7000'))],}
        for key, value in ages_dict.items():
            sjoined[key] = sjoined.loc[:, value].sum(axis=1) / 24
        keys = [key for key in ages_dict.keys()]
        values.append(sjoined.groupby(['saup_yr','상권명','year'],
                                    as_index=False)[keys].sum().round().sort_values(['saup_yr','year'], ascending=True))
    concated = pd.concat(values, ignore_index=True)
    concated.columns = ['사업연도','상권명','기준연도','10대이하','20대','30대','40대','50대','60대이상']
    print("2021년~2022년 상권별 연령 생활인구 집계완료")
    conn.close()
    return concated

def aggregate_daynm1(conn, pt1, grid):
    print("2021년~2022년 상권별 요일별 생활인구 집계시작")
    values = []
    for ym in tqdm(months1):
        query = f"""SELECT * FROM purchase_data.l0csv_kt_d_lifepop_time_p
                          WHERE SUBSTR(std_ymd, 1, 6) IN ('{ym}') AND SUBSTR(hcode,1,5) NOT IN {excluded}"""
        df = pd.read_sql(query, conn)
        df.columns = [col.split('.')[1] for col in df.columns]
        df.drop(['dat_flow_id','part_batchdate'], axis=1, inplace=True)
        cols = [col for col in df.columns if '_m_' in col or '_w_' in col or '_t_' in col]
        df[cols] = df[cols].astype(float)
        df['year'] = df['std_ymd'].astype('datetime64[ns]').dt.year.astype(str) + "년"
        # 요일: dayofweek(0=월 … 6=일) → 축약형으로 통일 (로케일 불필요)
        df['weekday'] = df['std_ymd'].astype('datetime64[ns]').dt.dayofweek.map(dict(enumerate(weekday_order)))
        df = pd.merge(pt1, df, on="id", how="left")
        gdf = gpd.GeoDataFrame(df, geometry="geometry")
        sjoined = gpd.sjoin(grid, gdf, how="inner", predicate="intersects")
        times_dict = {
            '05~08시': [col for col in sjoined.columns if col.endswith(tuple(f"_{h:02d}" for h in range(5, 9)))],
            '09~11시': [col for col in sjoined.columns if col.endswith(tuple(f"_{h:02d}" for h in range(9, 12)))],
            '12~14시': [col for col in sjoined.columns if col.endswith(tuple(f"_{h:02d}" for h in range(12, 15)))],
            '15~17시': [col for col in sjoined.columns if col.endswith(tuple(f"_{h:02d}" for h in range(15, 18)))],
            '18~22시': [col for col in sjoined.columns if col.endswith(tuple(f"_{h:02d}" for h in range(18, 22)))],
            '23~04시': [col for col in sjoined.columns if col.endswith(("_23", "_00", "_01", "_02", "_03", "_04"))],}
        for key, value in times_dict.items():
            sjoined[key] = sjoined.loc[:, value].sum(axis=1)
        sjoined['일계'] = sjoined[list(times_dict.keys())].sum(axis=1)
        values.append(sjoined.groupby(['saup_yr', '상권명', 'year', 'weekday'], as_index=False)['일계'].sum())
    concated = pd.concat(values, ignore_index=True)
    pivoted = (
        pd.pivot_table(concated, index=['saup_yr', '상권명', 'year'],
                       columns='weekday', values='일계', aggfunc='sum'
                       ).reindex(columns=weekday_order)   # 없는 요일도 컬럼 유지
                        .round()
                        .reset_index())
    pivoted.columns.name = None
    pivoted.columns = ['사업연도', '상권명', '기준연도', '월', '화', '수', '목', '금', '토', '일']
    print("2021년~2022년 상권별 요일별 생활인구 집계완료")
    conn.close()
    return pivoted

def aggregate_tmes1(conn, pt1, grid):
    print("2021년~2022년 상권별 시간대 생활인구 집계시작")
    values = []
    for ym in tqdm(months1):
        query = f"""SELECT * FROM purchase_data.l0csv_kt_d_lifepop_time_p
                          WHERE SUBSTR(std_ymd, 1, 6) IN ('{ym}') AND SUBSTR(hcode,1,5) NOT IN {excluded}"""
        df = pd.read_sql(query, conn)
        df.columns = [col.split('.')[1] for col in df.columns]
        df.drop(['dat_flow_id','part_batchdate'], axis=1, inplace=True)
        cols = [col for col in df.columns if '_m_' in col or '_w_' in col or '_t_' in col]
        df[cols] = df[cols].astype(float)
        df['year'] = df['std_ymd'].astype('datetime64[ns]').astype(str).str[:4] + "년"
        df = pd.merge(pt1, df, on="id", how="left")
        gdf = gpd.GeoDataFrame(df, geometry="geometry")
        sjoined = gpd.sjoin(grid, gdf, how="inner", predicate="intersects")
        times_dict = {
            '05~08시': [col for col in sjoined.columns if col.endswith(tuple(f"_{h:02d}" for h in range(5, 9)))],
            '09~11시': [col for col in sjoined.columns if col.endswith(tuple(f"_{h:02d}" for h in range(9, 12)))],
            '12~14시': [col for col in sjoined.columns if col.endswith(tuple(f"_{h:02d}" for h in range(12, 15)))],
            '15~17시': [col for col in sjoined.columns if col.endswith(tuple(f"_{h:02d}" for h in range(15, 18)))],
            '18~22시': [col for col in sjoined.columns if col.endswith(tuple(f"_{h:02d}" for h in range(18, 22)))],
            '23~04시': [col for col in sjoined.columns if col.endswith(("_23", "_00", "_01", "_02", "_03", "_04"))],}
        for key, value in times_dict.items():
            sjoined[key] = sjoined.loc[:, value].sum(axis=1)
        keys = [key for key in times_dict.keys()]
        values.append(
            sjoined.groupby(['saup_yr','상권명','year'], 
                            as_index=False)[keys].sum().round().sort_values(['saup_yr','year'], ascending=True))
    concated = pd.concat(values, ignore_index=True)
    concated.columns = ['사업연도','상권명','기준연도','05~08시','09~11시','12~14시','15~17시','18~22시','23~04시']
    print("2021년~2022년 상권별 시간대 생활인구 집계완료")
    conn.close()
    return concated

def aggregate_gender2(conn, pt2, grid):
    print("2023년~2025년 상권별 성별 생활인구 집계시작")
    values = []
    for ym in tqdm(months2):
        query = f"""SELECT * FROM purchase_data.l0kte_kt_d_living_emd_p2
                          WHERE SUBSTR(std_ymd, 1, 6) IN ('{ym}') AND SUBSTR(hcode,1,5) NOT IN {excluded}"""
        df = pd.read_sql(query, conn)
        df.columns = [col.split('.')[1] for col in df.columns]
        df.drop(['dat_flow_id','part_batchdate'], axis=1, inplace=True)
        cols = [col for col in df.columns if '_m_' in col or '_w_' in col or '_t_' in col]
        df[cols] = df[cols].astype(float)
        df['year'] = df['std_ymd'].astype('datetime64[ns]').astype(str).str[:4] + "년"
        df = pd.merge(pt2, df, left_on="gid", right_on="id", how="left")
        gdf = gpd.GeoDataFrame(df, geometry="geometry")
        sjoined = gpd.sjoin(grid, gdf, how="inner", predicate="intersects")
        gender_dict = {
            '남성': [col for col in sjoined.columns if '_m_' in col],
            '여성': [col for col in sjoined.columns if '_w_' in col]}
        for key, value in gender_dict.items():
            sjoined[key] = sjoined.loc[:, value].sum(axis=1) / 24
        keys = [key for key in gender_dict.keys()]
        values.append(sjoined.groupby(['saup_yr','상권명','year'],
                                      as_index=False)[keys].sum().round().sort_values(['saup_yr','year'], ascending=True))
    concated = pd.concat(values, ignore_index=True)
    concated.columns = ['사업연도','상권명','기준연도','남성','여성']
    print("2023년~2025년 상권별 성별 생활인구 집계완료")
    conn.close()
    return concated

def aggregate_ages2(conn, pt2, grid):
    print("2023년~2025년 상권별 연령 생활인구 집계시작")
    values = []
    for ym in tqdm(months2):
        query = f"""SELECT * FROM purchase_data.l0kte_kt_d_living_emd_p2
                          WHERE SUBSTR(std_ymd, 1, 6) IN ('{ym}') AND SUBSTR(hcode,1,5) NOT IN {excluded}"""
        df = pd.read_sql(query, conn)
        df.columns = [col.split('.')[1] for col in df.columns]
        df.drop(['dat_flow_id','part_batchdate'], axis=1, inplace=True)
        cols = [col for col in df.columns if '_m_' in col or '_w_' in col or '_t_' in col]
        df[cols] = df[cols].astype(float)
        df['year'] = df['std_ymd'].astype('datetime64[ns]').astype(str).str[:4] + "년"
        df = pd.merge(df, pt2, left_on="id", right_on="gid", how="left")
        gdf = gpd.GeoDataFrame(df, geometry="geometry")
        sjoined = gpd.sjoin(grid, gdf, how="inner", predicate="intersects")
        ages_dict = {
            '10대이하': [col for col in sjoined.columns if col.endswith(('_0009','_1014','_1519'))],
            '20대': [col for col in sjoined.columns if col.endswith(('_2024','_2529'))],
            '30대': [col for col in sjoined.columns if col.endswith(('_3034','_3539'))],
            '40대': [col for col in sjoined.columns if col.endswith(('_4044','_4549'))],
            '50대': [col for col in sjoined.columns if col.endswith(('_5054','_5559'))],
            '60대이상': [col for col in sjoined.columns if col.endswith(('_6064','_6569','_7000'))],}
        for key, value in ages_dict.items():
            sjoined[key] = sjoined.loc[:, value].sum(axis=1) / 24
        keys = [key for key in ages_dict.keys()]
        values.append(sjoined.groupby(['saup_yr','상권명','year'], 
                                      as_index=False)[keys].sum().round().sort_values(['saup_yr','year'], ascending=True))
    concated = pd.concat(values, ignore_index=True)
    concated.columns = ['사업연도','상권명','기준연도','10대이하','20대','30대','40대','50대','60대이상']
    print("2023년~2025년 상권별 연령 생활인구 집계완료")
    conn.close()
    return concated

def aggregate_daynm2(conn, pt2, grid):
    print("2023년~2025년 상권별 요일별 생활인구 집계시작")
    values = []
    for ym in tqdm(months2):
        query = f"""SELECT * FROM purchase_data.l0kte_kt_d_living_tme_p2
                          WHERE SUBSTR(std_ymd, 1, 6) IN ('{ym}') AND SUBSTR(hcode,1,5) NOT IN {excluded}"""
        df = pd.read_sql(query, conn)
        df.columns = [col.split('.')[1] for col in df.columns]
        df.drop(['dat_flow_id','part_batchdate'], axis=1, inplace=True)
        cols = [col for col in df.columns if '_m_' in col or '_w_' in col or '_t_' in col]
        df[cols] = df[cols].astype(float)
        df['year'] = df['std_ymd'].astype('datetime64[ns]').dt.year.astype(str) + "년"
        # 요일: dayofweek(0=월 … 6=일) → 축약형으로 통일 (로케일 불필요)
        df['weekday'] = df['std_ymd'].astype('datetime64[ns]').dt.dayofweek.map(dict(enumerate(weekday_order)))
        df = pd.merge(pt2, df, left_on="gid", right_on="id", how="left")
        gdf = gpd.GeoDataFrame(df, geometry="geometry")
        sjoined = gpd.sjoin(grid, gdf, how="inner", predicate="intersects")
        times_dict = {
            '05~08시': [col for col in sjoined.columns if col.endswith(tuple(f"_{h:02d}" for h in range(5, 9)))],
            '09~11시': [col for col in sjoined.columns if col.endswith(tuple(f"_{h:02d}" for h in range(9, 12)))],
            '12~14시': [col for col in sjoined.columns if col.endswith(tuple(f"_{h:02d}" for h in range(12, 15)))],
            '15~17시': [col for col in sjoined.columns if col.endswith(tuple(f"_{h:02d}" for h in range(15, 18)))],
            '18~22시': [col for col in sjoined.columns if col.endswith(tuple(f"_{h:02d}" for h in range(18, 22)))],
            '23~04시': [col for col in sjoined.columns if col.endswith(("_23", "_00", "_01", "_02", "_03", "_04"))],}
        for key, value in times_dict.items():
            sjoined[key] = sjoined.loc[:, value].sum(axis=1)
        sjoined['일계'] = sjoined[list(times_dict.keys())].sum(axis=1)
        values.append(sjoined.groupby(['saup_yr', '상권명', 'year', 'weekday'], as_index=False)['일계'].sum())
    concated = pd.concat(values, ignore_index=True)
    pivoted = (
        pd.pivot_table(concated, index=['saup_yr', '상권명', 'year'], 
                       columns='weekday', values='일계', aggfunc='sum'
                    ).reindex(columns=weekday_order)   # 없는 요일도 컬럼 유지
                     .round()
                     .reset_index())
    pivoted.columns.name = None
    pivoted.columns = ['사업연도', '상권명', '기준연도', '월', '화', '수', '목', '금', '토', '일']
    print("2023년~2025년 상권별 요일별 생활인구 집계완료")
    conn.close()
    return pivoted

def aggregate_tmes2(conn, pt2, grid):
    print("2023년~2025년 상권별 시간대 생활인구 집계시작")
    values = []
    for ym in tqdm(months2):
        query = f"""SELECT * FROM purchase_data.l0kte_kt_d_living_tme_p2
                          WHERE SUBSTR(std_ymd, 1, 6) IN ('{ym}') AND SUBSTR(hcode,1,5) NOT IN {excluded}"""
        df = pd.read_sql(query, conn)
        df.columns = [col.split('.')[1] for col in df.columns]
        df.drop(['dat_flow_id','part_batchdate'], axis=1, inplace=True)
        cols = [col for col in df.columns if '_m_' in col or '_w_' in col or '_t_' in col]
        df[cols] = df[cols].astype(float)
        df['year'] = df['std_ymd'].astype('datetime64[ns]').astype(str).str[:4] + "년"
        df = pd.merge(pt2, df, left_on="gid", right_on="id", how="left")
        gdf = gpd.GeoDataFrame(df, geometry="geometry")
        sjoined = gpd.sjoin(grid, gdf, how="inner", predicate="intersects")
        times_dict = {
            '05~08시': [col for col in sjoined.columns if col.endswith(tuple(f"_{h:02d}" for h in range(5, 9)))],
            '09~11시': [col for col in sjoined.columns if col.endswith(tuple(f"_{h:02d}" for h in range(9, 12)))],
            '12~14시': [col for col in sjoined.columns if col.endswith(tuple(f"_{h:02d}" for h in range(12, 15)))],
            '15~17시': [col for col in sjoined.columns if col.endswith(tuple(f"_{h:02d}" for h in range(15, 18)))],
            '18~22시': [col for col in sjoined.columns if col.endswith(tuple(f"_{h:02d}" for h in range(18, 22)))],
            '23~04시': [col for col in sjoined.columns if col.endswith(("_23", "_00", "_01", "_02", "_03", "_04"))],}
        for key, value in times_dict.items():
            sjoined[key] = sjoined.loc[:, value].sum(axis=1)
        keys = [key for key in times_dict.keys()]
        values.append(
            sjoined.groupby(['saup_yr','상권명','year'], 
                            as_index=False)[keys].sum().round().sort_values(['saup_yr','year'], ascending=True))
    concated = pd.concat(values, ignore_index=True)
    concated.columns = ['사업연도','상권명','기준연도','05~08시','09~11시','12~14시','15~17시','18~22시','23~04시']
    print("2023년~2025년 상권별 시간대 생활인구 집계완료")
    conn.close()
    return concated

# pd.concat([aggregate_gender1(conn, grid50_pt, grid100_mrkt), 
#            aggregate_gender2(conn, grid100_pt, grid100_mrkt)
#            ], ignore_index=True
#           ).sort_values(['사업연도','기준연도'], ascending=True
#                         ).to_csv(OUTPUT_PATH + "사업연도_상권별_성별_생활인구_현황.csv", 
#                                  sep="|", encoding="utf-8", index=False)
# pd.concat([aggregate_ages1(conn, grid50_pt, grid100_mrkt),
#            aggregate_ages2(conn, grid100_pt, grid100_mrkt)
#            ], ignore_index=True
#           ).sort_values(['사업연도','기준연도'], ascending=True
#                         ).to_csv(OUTPUT_PATH + "사업연도_상권별_연령_생활인구_현황.csv",
#                                  sep="|", encoding="utf-8", index=False)
pd.concat([aggregate_daynm1(conn, grid50_pt, grid100_mrkt),
           aggregate_daynm2(conn, grid100_pt, grid100_mrkt)
           ], ignore_index=True
          ).sort_values(['사업연도','기준연도'], ascending=True
                        ).to_csv(OUTPUT_PATH + "사업연도_상권별_요일_생활인구_현황.csv",
                                 sep="|", encoding="utf-8", index=False)
# pd.concat([aggregate_tmes1(conn, grid50_pt, grid100_mrkt),
#            aggregate_tmes2(conn, grid100_pt, grid100_mrkt)
#            ], ignore_index=True
#           ).sort_values(['사업연도','기준연도'], ascending=True
#                         ).to_csv(OUTPUT_PATH + "사업연도_상권별_시간_생활인구_현황.csv",
#                                  sep="|", encoding="utf-8", index=False)
