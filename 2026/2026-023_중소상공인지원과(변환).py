from impala.dbapi import connect
import pandas as pd
import geopandas as gpd
import glob
from tqdm import tqdm
import warnings
warnings.filterwarnings('ignore')

conn = connect(host="172.20.192.154", port=10000, user="datawave", database="purchase_data", auth_mechanism="PLAIN")
data_path = r"D:\\02_사업관리\\2026년\\데이터 분석 컨설팅\\20260609_중소상공인지원과\\02_데이터\\DAT\\"
output_path = r"D:\\02_사업관리\\2026년\\데이터 분석 컨설팅\\20260609_중소상공인지원과\\03_집계결과\\"
data_lists = glob.glob(data_path + "*.dat", recursive=True)
grid50 = gpd.read_file(r"D:\\02_사업관리\\자체분석\\04_공간DB\\griddata\\busan_50cell_v15.shp").to_crs(5179)
grid50['x'] = grid50.geometry.centroid.x.round(3)
grid50['y'] = grid50.geometry.centroid.y.round(3)
grid50_pt = gpd.GeoDataFrame(grid50, geometry=gpd.points_from_xy(grid50.x, grid50.y))
grid100 = gpd.read_file(r"D:\\02_사업관리\\자체분석\\04_공간DB\\griddata\\ngii_100m_busan.shp").to_crs(5179)
ngii_sgg = gpd.read_file(r"D:\\02_사업관리\\2026년\\데이터 분석 컨설팅\\20260609_중소상공인지원과\\부산광역시 행정경계.gpkg",
                                                       layer="NGII_SGG", driver="GPKG")
ngii_hjd = gpd.read_file(r"D:\\02_사업관리\\2026년\\데이터 분석 컨설팅\\20260609_중소상공인지원과\\부산광역시 행정경계.gpkg",
                                                      layer="NGII_EMD", driver="GPKG")
census_sgg = gpd.read_file(r"D:\\02_사업관리\\2026년\\데이터 분석 컨설팅\\20260609_중소상공인지원과\\부산광역시 행정경계.gpkg", 
                                          layer="센서스구군", driver="GPKG")
census_hjd = gpd.read_file(r"D:\\02_사업관리\\2026년\\데이터 분석 컨설팅\\20260609_중소상공인지원과\\부산광역시 행정경계.gpkg",
                                          layer="센서스행정동", driver="GPKG")
census = gpd.overlay(census_hjd, census_sgg, how="intersection", keep_geom_type=True)
census_merged = gpd.overlay(census, ngii_hjd, how="intersection", keep_geom_type=True)
census_merged['hcode'] = census_merged['EMD_CD'].str[:5] + census_merged['ADM_DR_CD'].str[-2:] + "000"
bccd_sec_code = pd.read_csv(r"D:\\02_사업관리\\코드자료\\bccd_sec_code.csv", sep="|", encoding="utf-8")
shcd_sec_code = pd.read_sql("SELECT ry_l_cd, ry_l_nm, ry_m_cd, ry_m_nm FROM purchase_data.l0csv_shcd_ry_code", conn)

def aggregate_shcd100(conn, pt1, grid2, sec):
    values = []
    months = [f"{year}{month:02d}" for year in range(2022, 2023) for month in range(1, 13)]
    for month in tqdm(months):
        sql = f"""
        SELECT std_ymd, hcode, id, ry_l_cd, ry_m_cd, CAST(amt AS BIGINT), CAST(cnt AS BIGINT)
        FROM l0csv_shcd_blk_sec WHERE SUBSTR(std_ymd,1,6) = '{month}'"""
        df = pd.read_sql(sql, conn)
        df['거래연도'] = df['std_ymd'].astype(str).str[:4] + "년"
        df['거래월'] = df['std_ymd'].astype(str).str[4:6] + "월"
        df = pd.merge(df, sec, on="ry_m_cd", how="left")
        df = pd.merge(df, pt1, on='id', how="inner")
        gdf = gpd.GeoDataFrame(df, geometry = gpd.points_from_xy(df.x, df.y))
        gdf = gpd.sjoin(grid2, gdf, how="inner", predicate="intersects") 
        values.append(gdf.groupby(['gid','거래연도','거래월','ry_m_cd','ry_m_nm'],
                                  as_index=False).agg({'amt': 'sum', 'cnt': 'sum'}).sort_values(['거래연도','거래월'], ascending=True))
    concated = pd.concat(values, ignore_index=True)
    concated.rename(columns={'gid': '100m격자코드','ry_m_cd': '업종중분류코드', 'ry_m_nm': '업종중분류명',
                             'amt': '합계_매출금액(원)', 'cnt': '합계_매출건수(건)'}, inplace=True)
    conn.close()
    return concated

def aggregate_bccd100(conn, sec):
    values = []
    months = [f"{year}{month:02d}" for year in range(2026, 2027) for month in range(1, 13)]
    for month in tqdm(months):
        sql = f"""
        SELECT std_ymd, hcode, id, ry_l_cd, ry_m_cd, CAST(amt AS BIGINT), CAST(cnt AS BIGINT)
        FROM l0bcc_bccd_d_sec_p2 WHERE SUBSTR(std_ymd,1,6) = '{month}'"""
        df = pd.read_sql(sql, conn)
        df['거래연도'] = df['std_ymd'].astype(str).str[:4] + "년"
        df['거래월'] = df['std_ymd'].astype(str).str[4:6] + "월"
        df = pd.merge(df, sec, on="ry_m_cd", how="left")
        values.append(df.groupby(['id','거래연도','거래월','ry_m_cd','ry_m_nm'],
                                 as_index=False).agg({'amt': 'sum', 'cnt': 'sum'}).sort_values(['거래연도','거래월'], ascending=True))
    concated = pd.concat(values)
    concated.rename(columns={'id': '100m격자코드','ry_m_cd': '업종중분류코드', 'ry_m_nm': '업종중분류명',
                             'amt': '합계_매출금액(원)', 'cnt': '합계_매출건수(건)'}, inplace=True)
    conn.close()
    return concated

def aggregate_shcdhjd(conn, hjd, sec):
    values = []
    months = [f"{year}{month:02d}" for year in range(2022, 2023) for month in range(1, 13)]
    for month in tqdm(months):
        sql = f"""
        SELECT std_ym, hcode, ry_l_cd, ry_m_cd, ry_s_cd, CAST(amt AS BIGINT), CAST(cnt AS BIGINT)
        FROM l0csv_shcd_rys_emd WHERE std_ym = '{month}'"""
        df = pd.read_sql(sql, conn)
        df['거래연도'] = df['std_ym'].astype(str).str[:4] + "년"
        df['거래월'] = df['std_ym'].astype(str).str[4:6] + "월"
        df = pd.merge(df, hjd, on="hcode", how="inner")
        df = pd.merge(df, sec, on="ry_m_cd", how="left")
        df['행정읍면동코드'] = df['ADM_DR_CD'] + "0"
        values.append(df.groupby(['행정읍면동코드','거래연도','거래월','ry_m_cd','ry_m_nm'],
                                 as_index=False).agg({'amt': 'sum', 'cnt': 'sum'}).sort_values(['거래연도','거래월'], ascending=True))
    concated = pd.concat(values)
    concated.rename(columns={'ry_m_cd': '업종중분류코드', 'ry_m_nm': '업종중분류명', 'amt': '합계_매출금액(원)', 'cnt': '합계_매출건수(건)'}, inplace=True)
    conn.close()
    return concated

def aggregate_bccdhjd(conn, hjd, sec):
    values = []
    months = [f"{year}{month:02d}" for year in range(2026, 2027) for month in range(1, 13)]
    for month in tqdm(months):
        sql = f"""
        SELECT std_ymd, hcode, ry_l_cd, ry_m_cd, CAST(amt AS BIGINT), CAST(cnt AS BIGINT)
        FROM l0bcc_bccd_d_sec WHERE SUBSTR(std_ymd,1,6) = '{month}'"""
        df = pd.read_sql(sql, conn)
        df['거래연도'] = df['std_ymd'].astype(str).str[:4] + "년"
        df['거래월'] = df['std_ymd'].astype(str).str[4:6] + "월"
        df = pd.merge(df, hjd, on="hcode", how="inner")
        df = pd.merge(df, sec, on="ry_m_cd", how="left")
        df['행정읍면동코드'] = df['ADM_DR_CD'] + "0"
        values.append(df.groupby(['행정읍면동코드','거래연도','거래월','ry_m_cd','ry_m_nm'],
                                 as_index=False).agg({'amt': 'sum', 'cnt': 'sum'}).sort_values(['거래연도','거래월'], ascending=True))
    concated = pd.concat(values)
    concated.rename(columns={'ry_m_cd': '업종중분류코드', 'ry_m_nm': '업종중분류명', 'amt': '합계_매출금액(원)', 'cnt': '합계_매출건수(건)'}, inplace=True)
    conn.close()
    return concated

def extract_grid100(data, grid100):
    df = pd.read_csv(data, sep="|", dtype={'MCNT_NO': str, '거래일자': str, '업종코드': str}, encoding="utf-8")
    gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.LNG, df.LAT, crs=4326)).to_crs(5179)
    sjoined = gpd.sjoin(grid100, gdf, how="left", predicate="intersects")
    sjoined['거래연도'] = sjoined['거래일자'].astype(str).str[:4] + "년"
    sjoined['거래월'] = sjoined['거래일자'].astype(str).str[4:6] + "월"
    sjoined['요일별'] = sjoined['거래일자'].astype('datetime64[ns]').dt.day_name('ko_KR')
    return sjoined

def extract_hjd_sgg(data, census):
    df = pd.read_csv(data, sep="|", dtype={'MCNT_NO': str, '거래일자': str, '업종코드': str}, encoding="utf-8")
    gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.LNG, df.LAT, crs=4326)).to_crs(5179)
    sjoined = gpd.sjoin(gdf, census, how="inner", predicate="intersects")
    sjoined['거래연도'] = sjoined['거래일자'].astype(str).str[:4] + "년"
    sjoined['거래월'] = sjoined['거래일자'].astype(str).str[4:6] + "월"
    sjoined['요일별'] = sjoined['거래일자'].astype('datetime64[ns]').dt.day_name('ko_KR')
    sjoined['행정읍면동코드'] = sjoined['ADM_DR_CD'] + "0"
    return sjoined

print("100m 격자기준 동백전 집계")
def dongback_gender(grid100):
    values = []
    for data in data_lists:
        sjoined = extract_grid100(data, grid100)
        values.append(sjoined.groupby(['gid','거래연도','거래월','성별'],
                                      as_index=False).agg({'AUTH_AMT': 'sum', 'MCNT_NO': 'count'
                                                          }).sort_values(['거래연도','거래월'], ascending=True))
    concated = pd.concat(values)
    concated.rename(columns={'gid': '100m격자코드', 'AUTH_AMT': '합계_거래금액(원)', 'MCNT_NO': '합계_거래건수(건)'}, inplace=True)
    concated = concated[['100m격자코드','거래연도','거래월','합계_거래금액(원)','합계_거래건수(건)','요일별']]
    return concated

def dongback_age(grid100):
    values = []
    for data in data_lists:
        sjoined = extract_grid100(data, grid100) 
        values.append(sjoined.groupby(['gid','거래연도','거래월','연령대'],
                                      as_index=False).agg({'AUTH_AMT': 'sum', 'MCNT_NO': 'count'
                                                          }).sort_values(['거래연도','거래월'], ascending=True))
    concated = pd.concat(values)
    concated.rename(columns={'gid': '100m격자코드', 'AUTH_AMT': '합계_거래금액(원)', 'MCNT_NO': '합계_거래건수(건)'}, inplace=True)
    concated = concated[['100m격자코드','거래연도','거래월','합계_거래금액(원)','합계_거래건수(건)','연령대']]
    return concated

def dongback_dayname(grid100):
    values = []
    for data in data_lists:
        sjoined = extract_grid100(data, grid100)
        values.append(sjoined.groupby(['gid','거래연도','거래월','요일별'],
                                      as_index=False).agg({'AUTH_AMT': 'sum', 'MCNT_NO': 'count'
                                                          }).sort_values(['거래연도','거래월'], ascending=True))
    concated = pd.concat(values)
    concated.rename(columns={'gid': '100m격자코드', 'AUTH_AMT': '합계_거래금액(원)', 'MCNT_NO': '합계_거래건수(건)'}, inplace=True)
    concated = concated[['100m격자코드','거래연도','거래월','합계_거래금액(원)','합계_거래건수(건)','요일별']]
    return concated

def dongback_sec(grid100):
    values = []
    for data in data_lists:
        sjoined = extract_grid100(data, grid100)
        values.append(sjoined.groupby(['gid','거래연도','거래월','업종코드','업종명'],
                                      as_index=False).agg({'AUTH_AMT': 'sum', 'MCNT_NO': 'count'
                                                          }).sort_values(['거래연도','거래월'], ascending=True))
    concated = pd.concat(values)
    concated.rename(columns={'gid': '100m격자코드', 'AUTH_AMT': '합계_거래금액(원)', 'MCNT_NO': '합계_거래건수(건)'}, inplace=True)
    concated = concated[['100m격자코드','거래연도','거래월','합계_거래금액(원)','합계_거래건수(건)','업종코드','업종명']]
    return concated

print("행정구역별 동백전 집계현황")
def dongback_hjd_gender(census):
    values = []
    for data in tqdm(data_lists):
        sjoined = extract_hjd_sgg(data, census)
        values.append(sjoined.groupby(['SIGUNGU_CD','행정읍면동코드','거래연도','거래월','성별','SIGUNGU_NM','ADM_DR_NM'],
                                      as_index=False).agg({'AUTH_AMT': 'sum', 'MCNT_NO': 'count'
                                                          }).sort_values(['SIGUNGU_CD','행정읍면동코드','거래연도','거래월'],ascending=True))
    concated=pd.concat(values)
    concated.rename(columns={'SIGUNGU_NM': '시군구', 'ADM_DR_NM': '읍면동', 'AUTH_AMT': '합계_거래금액(원)', 'MCNT_NO': '합계_거래건수(건)'}, inplace=True)
    concated = concated[['행정읍면동코드','거래연도','거래월','합계_거래금액(원)','합계_거래건수(건)','성별','시군구','읍면동']]
    return concated

def dongback_hjd_ages(census):
    values = []
    for data in tqdm(data_lists):
        sjoined = extract_hjd_sgg(data, census)
        values.append(sjoined.groupby(['SIGUNGU_CD','행정읍면동코드','거래연도','거래월','연령대','SIGUNGU_NM','ADM_DR_NM'],
                                      as_index=False).agg({'AUTH_AMT': 'sum', 'MCNT_NO': 'count'
                                                          }).sort_values(['SIGUNGU_CD','행정읍면동코드','거래연도','거래월'],ascending=True))
    concated=pd.concat(values)
    concated.rename(columns={'AUTH_AMT': '합계_거래금액(원)', 'MCNT_NO': '합계_거래건수(건)'}, inplace=True)
    concated = concated[['행정읍면동코드','거래연도','거래월','합계_거래금액(원)','합계_거래건수(건)','연령대']]
    return concated

def dongback_hjd_dayname(census):
    values = []
    for data in tqdm(data_lists):
        sjoined = extract_hjd_sgg(data, census)
        values.append(sjoined.groupby(['SIGUNGU_CD','행정읍면동코드','거래연도','거래월','요일별','SIGUNGU_NM','ADM_DR_NM'],
                                      as_index=False).agg({'AUTH_AMT': 'sum', 'MCNT_NO': 'count'
                                                          }).sort_values(['SIGUNGU_CD','행정읍면동코드','거래연도','거래월','요일별'],ascending=True))
    concated=pd.concat(values)
    concated.rename(columns={'AUTH_AMT': '합계_거래금액(원)', 'MCNT_NO': '합계_거래건수(건)'}, inplace=True)
    concated = concated[['행정읍면동코드','거래연도','거래월','합계_거래금액(원)','합계_거래건수(건)','요일별']]
    return concated

def dongback_hjd_sec(census):
    values = []
    for data in tqdm(data_lists):
        sjoined = extract_hjd_sgg(data, census)
        values.append(sjoined.groupby(['SIGUNGU_CD','행정읍면동코드','거래연도','거래월','업종코드','업종명','SIGUNGU_NM','ADM_DR_NM'],
                                      as_index=False).agg({'AUTH_AMT': 'sum', 'MCNT_NO': 'count'
                                                          }).sort_values(['SIGUNGU_CD','행정읍면동코드','거래연도','거래월'],ascending=True))
    concated=pd.concat(values)
    concated.rename(columns={'AUTH_AMT': '합계_거래금액(원)', 'MCNT_NO': '합계_거래건수(건)'}, inplace=True)
    concated = concated[['행정읍면동코드','거래연도','거래월','합계_거래금액(원)','합계_거래건수(건)','업종코드','업종명']]
    return concated

# dongback_gender(grid100).to_csv(output_path + "격자단위_거래연월_성별_동백전_사용현황.csv", sep="|", encoding="utf-8", index=False)
# dongback_age(grid100).to_csv(output_path + "격자단위_거래연월_연령_동백전_사용현황.csv", sep="|", encoding="utf-8", index=False)
# dongback_dayname(grid100).to_csv(output_path + "격자단위_거래연월_요일_동백전_사용현황.csv", sep="|", encoding="utf-8", index=False)
# pd.merge(aggregate_shcd100(conn, grid50_pt, grid100, shcd_sec_code)[['100m격자코드','거래연도','거래월','업종중분류코드','업종중분류명']],
#          dongback_sec(grid100), on=['100m격자코드','거래연도','거래월'], how="left"
#         ).fillna(0).to_csv(output_path + "격자단위_거래연월_업종_동백전_사용현황_신한.csv", sep="|", encoding="utf-8", index=False)
pd.merge(aggregate_bccd100(conn, bccd_sec_code)[['100m격자코드','거래연도','거래월','업종중분류코드','업종중분류명']], dongback_sec(grid100), 
         on=['100m격자코드','거래연도','거래월'], how="left"
        ).fillna(0).to_csv(output_path + "격자단위_거래연월_업종_동백전_사용현황_비씨_26년.csv", sep="|", encoding="utf-8", index=False)

# dongback_hjd_gender(census).to_csv(output_path + "행정동단위_거래연월_성별_동백전_사용현황.csv", sep="|", encoding="utf-8", index=False)
# dongback_hjd_ages(census).to_csv(output_path + "행정동단위_거래연월_연령_동백전_사용현황.csv", sep="|", encoding="utf-8", index=False)  
# dongback_hjd_dayname(census).to_csv(output_path + "행정동단위_거래연월_요일_동백전_사용현황.csv", sep="|", encoding="utf-8", index=False)
# pd.merge(aggregate_shcdhjd(conn, census_merged, shcd_sec_code)[['행정읍면동코드','거래연도','거래월','업종중분류코드','업종중분류명']],
#          dongback_hjd_sec(census), on=['행정읍면동코드','거래연도','거래월'], how="left"
#         ).fillna(0).to_csv(output_path + "행정동단위_거래연월_업종_동백전_사용현황_신한.csv", sep="|", encoding="utf-8", index=False)
pd.merge(aggregate_bccdhjd(conn, census_merged, bccd_sec_code)[['행정읍면동코드','거래연도','거래월','업종중분류코드','업종중분류명']],
         dongback_hjd_sec(census), on=['행정읍면동코드','거래연도','거래월'], how="left"
        ).fillna(0).to_csv(output_path + "행정동단위_거래연월_업종_동백전_사용현황_비씨_26년.csv", sep="|", encoding="utf-8", index=False)
