import geopandas as gpd
import pandas as pd
import numpy as np
import calendar
import glob

hcode = pd.read_excel("D:/10_분석업무/00_공통코드/행정코드/2023/KIKcd_H.20240208(말소코드포함).xlsx", dtype={'행정동코드': 'str'})
hcode = hcode.loc[(hcode['시군구명']=="서구") & (hcode['말소일자'].isnull())][1:]
hcode = hcode[['행정동코드','읍면동명']]
hcode.columns = ['hcode', 'hname']
grid = gpd.read_file("D:/Project/geodata/griddata/busan_50cell_v21.shp", crs="EPSG:5179")
area = gpd.read_file("D:/Project/geodata/boundary/ngii/202307/shp/sig.shp", encoding="cp949", crs="EPSG:5179")
area = area.loc[area['SIG_CD'].astype(str).str.contains('26140')]
area_grid = gpd.overlay(grid, area, "intersection")
pop_lists = glob.glob("D:/Project/datacheck/01_lifepop/01_upload/*_p_*.csv", recursive=True)
output_path = "D:/10_분석업무/구군청/26140_서구/2024년/교육진흥과/20240507/집계결과/"

class Aggregated:

    def __init__(self, year, month, ym):
        self._year = year
        self._month = month
        self._ym = ym
        self.gender_data = []
        self.times_data = []
        
    def read_data(self, path, sep="|", date_col="std_ymd", dtype=None):
        return pd.read_csv(path, sep=sep, parse_dates=[date_col], dtype=dtype, encoding="utf-8", low_memory=False)
    
    def preprocess_data(self, df):
        df = df.loc[df['hcode'].str.startswith('26140')].copy()
        df['id'] = df['id'].astype(str)
        df['std_ym'] = df['std_ymd'].astype(str).str[:7]
        return df
        
    def save_gender_data(self, df, group_cols, value_cols):
        results = np.round(df.groupby(group_cols)[value_cols].sum().reset_index())
        results = pd.melt(results, id_vars=group_cols, value_vars=value_cols, var_name='class', value_name='pop')
        self.gender_data.append(results)
        return results

    def save_times_data(self, df, group_cols, value_cols):
        results = np.round(df.groupby(group_cols)[value_cols].sum().reset_index())
        results = pd.melt(results, id_vars=group_cols, value_vars=value_cols, var_name='class', value_name='pop')
        self.times_data.append(results)
        return results
        
    def aggregate_gender(self, df):
        df['65over'] = df.loc[:, ['h_m_6569','h_w_6569','w_m_6569','w_w_6569','v_m_6569','v_w_6569']].sum(axis=1) / calendar.monthrange(int(self._year), int(self._month))[1]
        df['70over'] = df.loc[:, ['h_m_7000','h_w_7000','w_m_7000','w_w_7000','v_m_7000','v_w_7000']].sum(axis=1) / calendar.monthrange(int(self._year), int(self._month))[1]
        self.save_gender_data(df, ['std_ym','hname','id'], ['65over','70over'])
        
    def aggregate_times(self, df):
        # 2022년 의뢰시간과 동일하게 적용: 08시~18시
        times_slots = {
            't_08': ['h_t_08','w_t_08','v_t_08'], 't_09': ['h_t_09','w_t_09','v_t_09'], 't_10': ['h_t_10','w_t_10','v_t_10'],
            't_11': ['h_t_11','w_t_11','v_t_11'], 't_12': ['h_t_12','w_t_12','v_t_12'], 't_13': ['h_t_13','w_t_13','v_t_13'],
            't_14': ['h_t_14','w_t_14','v_t_14'], 't_15': ['h_t_15','w_t_15','v_t_15'], 't_16': ['h_t_16','w_t_16','v_t_16'],
            't_17': ['h_t_17','w_t_17','v_t_17'], 't_18': ['h_t_18','w_t_18','v_t_18']}
        
        for time, slot in times_slots.items():
            df[time] = df.loc[:, slot].sum(axis=1) / len(slot) / calendar.monthrange(int(self._year), int(self._month))[1]
        self.save_times_data(df, ['std_ym','hname','id'], ['t_08','t_09','t_10','t_11','t_12','t_13','t_14','t_15','t_16','t_17','t_18'])
        
    def lifepop(self):
        for data in pop_lists:
            if self._ym == data.split('_')[-1].split('.')[0]:
                print(f"========== {self._ym} 생활인구 집계시작 ==========")
                df = self.read_data(data, dtype={'hcode': 'str', 'id': 'str'})
                df = self.preprocess_data(df)
                df = pd.merge(df, hcode, "inner", "hcode")
                if 'h_m_0009' in df.columns:
                    df = pd.merge(df, area_grid, "inner", "id")
                    self.aggregate_gender(df)
                elif 'h_t_00' in df.columns:
                    df = pd.merge(df, area_grid, "inner", "id")
                    self.aggregate_times(df)
                else:
                    pass
            else:
                pass
            
        print(f"========== {self._ym} 생활인구 집계완료 ==========\n")

if __name__ == "__main__":
    all_gender_data = []
    all_times_data = []
    
    for year in range(2023, 2024):
        for month in range(6, 9):
            ym = str(year) + f"{month:02d}"
            aggregated = Aggregated(year, month, ym)
            aggregated.lifepop()
            all_gender_data.extend(aggregated.gender_data)
            all_times_data.extend(aggregated.times_data)

    final_gender_df = pd.concat(all_gender_data, ignore_index=True)
    final_gender_df.to_csv(output_path + "ID별_65세이상_존재인구_현황.csv", sep="|", encoding="utf-8", index=False)
    
    final_times_df = pd.concat(all_times_data, ignore_index=True)
    final_times_df.to_csv(output_path + "ID별_시간대_존재인구_현황.csv", sep="|", encoding="utf-8", index=False)
