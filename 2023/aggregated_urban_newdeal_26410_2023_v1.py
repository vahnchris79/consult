from sqlalchemy import create_engine
import geopandas as gpd
import pandas as pd
import numpy as np
import psycopg2
import calendar
import glob
import sys

class Connect:
    
    def data():
        engine=0
        try:
            engine = create_engine("postgresql://busanbig:qntksqlr7531@210.103.81.13:7531/bsbp_purchs")
        except (Exception, psycopg2.DatabaseError) as Error:
            print("Error: %s" % Error)
        return engine

    def result():
        engine=0
        try:
            engine = create_engine("postgresql://busanbig:qntksqlr7531@210.103.81.13:7531/bsbp_analysis")
        except (Exception, psycopg2.DatabaseError) as Error:
            print("Error: %s" % Error)
        return engine

data = Connect.data()
result = Connect.result()
gen_lists = glob.glob("../../../../../data/01_lifepop/03_imsi/*_sex_age_p_*.txt", recursive=True)
time_lists = glob.glob("../../../../../data/01_lifepop/03_imsi/*_time_p_*.txt", recursive=True)
grid = gpd.read_postgis("SELECT * FROM code.busan_kt_50cell", con=data, geom_col="geom", crs="epsg:5179")
kt_hcode = pd.read_sql_query("SELECT * FROM code.kt_hcode_10", con=data)
sh_hcode = pd.read_sql_query("SELECT * FROM code.shcard_hcode_bcode", con=data)
sh_hcode.columns = ['hcode', 'sname', 'gname', 'bname', 'hname']
sh_rycode = pd.read_sql_query("SELECT * FROM code.shcard_ry_code", con=data)
area = gpd.read_postgis("SELECT * FROM geumjeonggu_26410.study_area", con=result, geom_col="geom", crs="epsg:5179")
study_grid = gpd.sjoin(grid, area, "inner", "intersects")
study_grid = gpd.sjoin(grid, area, "inner", "intersects")
study_grid = study_grid[['id', 'areanm', 'geom']]
#study_grid.columns=['id', 'geom', 'areanm']


class Aggregated:
    
    def __init__(self, year, month, ym):
        self._year = year
        self._month = month
        self._ym = ym
        
    def genpop(self):
        for data in gen_lists:
            if data[39:].split('.')[0][-6:] == str(self._ym):
                print(f" ========== Start aggregate {data[39:].split('.')[0][:-7]} {self._year}. {self._month}. ========")
                df = pd.read_csv(data, sep="|", encoding="utf-8").rename(columns=str.lower)
                df['std_ymd'] = df['std_ymd'].astype(str)
                df['hcode'] = df['hcode'].astype(str)
                df['std_year'] = [df.loc[i,'std_ymd'][:6] + "년" for i in df.index]
                df['std_month'] = [df.loc[i,'std_ymd'][4:6] + "월" for i in df.index]
                df = df.loc[df['hcode'].str.startswith('26410')].copy()
                df = pd.merge(df, kt_hcode, "inner", "hcode")
                geom = gpd.points_from_xy(df['x_coord'].round(3), df['y_coord'].round(3), crs="epsg:5179")
                gdf = gpd.GeoDataFrame(df, geometry=geom)
                gdf = gpd.overlay(gdf, study_grid, "intersection")

                gdf['h_m_sum'] = gdf.iloc[:, 5:19].sum(axis=1) / 24 / calendar.monthrange(int(self._year), int(self._month))[1]
                gdf['h_w_sum'] = gdf.iloc[:, 19:33].sum(axis=1) / 24 / calendar.monthrange(int(self._year), int(self._month))[1]
                gdf['w_m_sum'] = gdf.iloc[:, 33:47].sum(axis=1) / 24 / calendar.monthrange(int(self._year), int(self._month))[1]
                gdf['w_w_sum'] = gdf.iloc[:, 47:61].sum(axis=1) / 24 / calendar.monthrange(int(self._year), int(self._month))[1]
                gdf['v_m_sum'] = gdf.iloc[:, 61:75].sum(axis=1) / 24 / calendar.monthrange(int(self._year), int(self._month))[1]
                gdf['v_w_sum'] = gdf.iloc[:, 75:89].sum(axis=1) / 24 / calendar.monthrange(int(self._year), int(self._month))[1]

                gdf['m_sum'] = gdf['h_m_sum'] + gdf['w_m_sum'] + gdf['v_m_sum']
                gdf['w_sum'] = gdf['h_w_sum'] + gdf['w_w_sum'] + gdf['v_w_sum']

                gdf['10_sum'] = gdf.iloc[:, [6,7,20,21,34,35,48,49,62,63,76,77]].sum(axis=1) / 24 / calendar.monthrange(int(self._year), int(self._month))[1]
                gdf['20_sum'] = gdf.iloc[:, [8,9,22,23,36,37,50,51,64,65,78,79]].sum(axis=1) / 24 / calendar.monthrange(int(self._year), int(self._month))[1]
                gdf['30_sum'] = gdf.iloc[:, [10,11,24,25,38,39,52,53,66,67,80,81]].sum(axis=1) / 24 / calendar.monthrange(int(self._year), int(self._month))[1]
                gdf['40_sum'] = gdf.iloc[:, [12,13,26,27,40,41,54,55,68,69,82,83]].sum(axis=1) / 24 / calendar.monthrange(int(self._year), int(self._month))[1]
                gdf['50_sum'] = gdf.iloc[:, [14,15,28,29,42,43,56,57,70,71,84,85]].sum(axis=1) / 24 / calendar.monthrange(int(self._year), int(self._month))[1]
                gdf['60_sum'] = gdf.iloc[:, [16,17,30,31,44,45,58,59,72,73,86,87]].sum(axis=1) / 24 / calendar.monthrange(int(self._year), int(self._month))[1]
                gdf['70_sum'] = gdf.iloc[:, [18,32,46,60,74,88]].sum(axis=1) / 24

                agg_gen = gdf.groupby(['std_year', 'std_month', 'id', 'hname', 'areanm']).agg({'m_sum': np.sum, 'w_sum': np.sum
                                                                                             }).round(0).reset_index().sort_values(by='std_month')
                agg_age = gdf.groupby(['std_year','std_month','id','hname','areanm']).agg({'10_sum': np.sum, '20_sum': np.sum, '30_sum': np.sum,
                                                                                           '40_sum': np.sum, '50_sum': np.sum, '60_sum': np.sum,
                                                                                           '70_sum': np.sum}).round(0).reset_index().sort_values(by='std_month')
                
                agg_gen_t = agg_gen.melt(id_vars=['std_year','std_month','id','hname','areanm'], value_vars=['m_sum','w_sum'])
                agg_gen_t.columns=['std_year', 'std_month', 'id', 'hname', 'areanm','gender','pop']
                agg_age_t = agg_age.melt(id_vars=['std_year','std_month','id','hname','areanm'],
                                         value_vars=['10_sum','20_sum','30_sum','40_sum','50_sum','60_sum','70_sum'])
                agg_age_t.columns=['std_year', 'std_month', 'id', 'hname', 'areanm','ages','pop']
                
                agg_gen_t.to_sql("m_mean_gen_pop", con=result, schema="geumjeonggu_26410", if_exists="append", index=False)
                agg_age_t.to_sql("m_mean_age_pop", con=result, schema="geumjeonggu_26410", if_exists="append", index=False)
                
                print(f" ========== Finish aggregate {data[39:].split('.')[0][:-7]} {self._year}. {self._month}. ========")
                
            else:
                pass
            
        return print()

    def timepop(self):
        for data in time_lists:
            if data[39:].split('.')[0][-6:] == str(self._ym):
                print(f" ========== Start aggregate {data[39:].split('.')[0][:-7]} {self._year}. {self._month}. ========")
                df = pd.read_csv(data, sep="|", encoding="utf-8").rename(columns=str.lower)
                df['std_ymd'] = df['std_ymd'].astype(str)
                df['hcode'] = df['hcode'].astype(str)
                df['std_year'] = [df.loc[i,'std_ymd'][:6] + "년" for i in df.index]
                df['std_month'] = [df.loc[i,'std_ymd'][4:6] + "월" for i in df.index]
                df = df.loc[df['hcode'].str.startswith('26410')].copy()
                df = pd.merge(df, kt_hcode, "inner", "hcode")
                geom = gpd.points_from_xy(df['x_coord'].round(3), df['y_coord'].round(3), crs="epsg:5179")
                gdf = gpd.GeoDataFrame(df, geometry=geom)
                gdf = gpd.overlay(gdf, study_grid, "intersection")

                gdf['t_00'] = gdf.iloc[:, [4,28,52]].sum(axis=1) / 3
                gdf['t_01'] = gdf.iloc[:, [5,29,53]].sum(axis=1) / 3
                gdf['t_02'] = gdf.iloc[:, [6,30,54]].sum(axis=1) / 3
                gdf['t_03'] = gdf.iloc[:, [7,31,55]].sum(axis=1) / 3
                gdf['t_04'] = gdf.iloc[:, [8,32,56]].sum(axis=1) / 3
                gdf['t_05'] = gdf.iloc[:, [9,33,57]].sum(axis=1) / 3
                gdf['t_06'] = gdf.iloc[:, [10,34,58]].sum(axis=1) / 3
                gdf['t_07'] = gdf.iloc[:, [11,35,59]].sum(axis=1) / 3
                gdf['t_08'] = gdf.iloc[:, [12,36,60]].sum(axis=1) / 3
                gdf['t_09'] = gdf.iloc[:, [13,37,61]].sum(axis=1) / 3
                gdf['t_10'] = gdf.iloc[:, [14,38,62]].sum(axis=1) / 3
                gdf['t_11'] = gdf.iloc[:, [15,39,63]].sum(axis=1) / 3
                gdf['t_12'] = gdf.iloc[:, [16,40,64]].sum(axis=1) / 3
                gdf['t_13'] = gdf.iloc[:, [17,41,65]].sum(axis=1) / 3
                gdf['t_14'] = gdf.iloc[:, [18,42,66]].sum(axis=1) / 3
                gdf['t_15'] = gdf.iloc[:, [19,43,67]].sum(axis=1) / 3
                gdf['t_16'] = gdf.iloc[:, [20,44,68]].sum(axis=1) / 3
                gdf['t_17'] = gdf.iloc[:, [21,45,69]].sum(axis=1) / 3
                gdf['t_18'] = gdf.iloc[:, [22,46,70]].sum(axis=1) / 3
                gdf['t_19'] = gdf.iloc[:, [23,47,71]].sum(axis=1) / 3
                gdf['t_20'] = gdf.iloc[:, [24,48,72]].sum(axis=1) / 3
                gdf['t_21'] = gdf.iloc[:, [25,49,73]].sum(axis=1) / 3
                gdf['t_22'] = gdf.iloc[:, [26,50,74]].sum(axis=1) / 3
                gdf['t_23'] = gdf.iloc[:, [27,51,75]].sum(axis=1) / 3

                agg_tme = gdf.groupby(['std_year','std_month','id','hname','areanm']).agg({'t_00': np.sum, 't_01': np.sum, 't_02': np.sum, 't_03': np.sum, 
                                                                                           't_04': np.sum, 't_05': np.sum, 't_06': np.sum, 't_07': np.sum,
                                                                                           't_08': np.sum, 't_09': np.sum, 't_10': np.sum, 't_11': np.sum,
                                                                                           't_12': np.sum, 't_13': np.sum, 't_14': np.sum, 't_15': np.sum,
                                                                                           't_16': np.sum, 't_17': np.sum, 't_18': np.sum, 't_19': np.sum,
                                                                                           't_20': np.sum, 't_21': np.sum, 't_22': np.sum, 't_23': np.sum
                                                                                          }).round(0).reset_index().sort_values(by='std_month')

                agg_tme_t = agg_tme.melt(id_vars=['std_year','std_month','id','hname','areanm'],
                                         value_vars=['t_00','t_01','t_02','t_03','t_04','t_05','t_06','t_07','t_08','t_09','t_10','t_11',
                                                     't_12','t_13','t_14','t_15','t_16','t_17','t_18','t_19','t_20','t_21','t_22','t_23'])
                agg_tme_t.columns = ['std_year','std_month','id','hname','areanm','times','pop']

                agg_tme_t.to_sql("m_mean_tim_pop", con=result, schema="geumjeonggu_26410", if_exists="append", index=False) 

                print(f" ========== Finish aggregate {data[39:].split('.')[0]} {self._year}. {self._month}. ========")
                
            else:
                pass
   
        return print()

    def carduse(self):
        print(f" ========== Start aggregate busan_blk_sec {self._year}. {self._month}. ==========")
        df = pd.read_sql_query(f"SELECT * FROM carduse.busan_blk_sec WHERE SUBSTRING(std_ymd,1,6)='{self._ym}'", con=data)
        df['std_ym'] = [df.loc[i, 'std_ymd'][:6] for i in df.index]
        df = df.loc[df['hcode'].str.startswith('26410')].copy()
        df = pd.merge(df, sh_hcode, "inner", "hcode")
        df = pd.merge(df, sh_rycode, "inner", "ry_m_cd")
        df = pd.merge(df, study_grid, "inner", left_on="blk_id", right_on="id")

        agg_df1 = df.groupby(['std_ym','blk_id','hname']).agg({'amt': np.mean}).round(0).reset_index().sort_values(by='std_ym')
        agg_df1.columns = ['std_ym','id','hname','amt']
        agg_df2 = df.groupby(['std_ym','blk_id','hname','ry_m_nm']).agg({'amt': np.mean}).round(0).reset_index().sort_values(by='std_ym')
        agg_df2.columns = ['std_ym','id','hname','ry_m_nm','amt']
                
        agg_df1.to_sql("m_mean_amt", con=result, schema="geumjeonggu_26410", if_exists="append", index=False)
        agg_df2.to_sql("m_mean_ry_amt", con=result, schema="geumjeonggu_26410", if_exists="append", index=False)
        
        print(f" ========== Finish aggregate busan_blk_sec {self._year}. {self._month}. ==========")
        
        return print()
        
if __name__ == "__main__":
    for year in range(2019, 2024):
        for month in range(1, 13):
            if len(str(month)) == 1:
                ym = str(year) + "0" + str(month)
            else:
                ym = str(year) + str(month)
            
            Aggregated(year, month, ym).genpop()
            Aggregated(year, month, ym).timepop()
            Aggregated(year, month, ym).carduse()
