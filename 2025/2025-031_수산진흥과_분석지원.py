
# 수산진흥과 데이터 분석 컨설팅
# 2025년 1월 ~ 3월 업종별 카드소비 현황 집계
# 대상업종: 한식(M014), 양식/중식/일식(M015~M017), 일반요식(M018), 음식료품(M021)
# 특이사항: 카드사 변경(신한카드 → BC카드)
# 2024년 교체용 집계자료 생성(추가)

import pandas as pd
import numpy as np
import glob
import warnings
warnings.filterwarnings('ignore')
from tqdm import tqdm
pd.set_option("display.float_format", "{:,.0f}".format)

grd_list = pd.read_csv("D:/02_사업관리/2024년/데이터 분석 컨설팅/20240830_수산진흥과/☆수산물 유통·판매 업종 매출 추이/분석대상구역_16개구역_240829.csv", 
                       dtype={'id': str}, encoding="utf-8")
sec_code = pd.read_csv("D:/02_사업관리/2025년/데이터 구매 및 활용/12_적재확인/코드자료/bccd_sec_code.csv", sep="|", encoding="utf-8")
data_path = "D:/02_사업관리/2025년/데이터 구매 및 활용/12_적재확인/카드이용/"
output_path = "D:/02_사업관리/2025년/데이터 분석 컨설팅/20250822_수산진흥과/02_집계결과/"

result = []
for month in range(1, 13):
    data_lists = glob.glob(data_path + f"2024{month:02d}/bccd_d_sec_p_2024{month:02d}.csv", recursive=True)
    for data in tqdm(data_lists):
        df = pd.read_csv(data, sep="|", dtype={'std_ymd': str, 'hcode': str, 'id': str}, encoding="utf-8")
        df['std_ymd'] = pd.to_datetime(df['std_ymd'])
        df['std_ym'] = df['std_ymd'].astype(str).str[:7] + "-01"
        df = grd_list.merge(df, how="left", on="id").dropna()
        df_s = df.loc[df['ry_m_cd'].str.contains('M014|M015|M016|M017|M018|M021')].copy()
        #group = df.groupby(['std_ym', 'area_cd', 'area_nm', 'ry_m_cd']).agg({'amt': np.sum, 'cnt': np.sum}).reset_index().fillna(0)
        pivot_t = df.pivot_table(values=['amt','cnt'], index=['std_ym','area_cd','area_nm'], aggfunc=np.sum).reset_index().fillna(0)
        pivot_t.columns = [col if col[0] == "" else f"{col[0]}_{col[1]}" if isinstance(col, tuple) else col for col in pivot_t.columns]
        pivot_t['구역총계(금액)'] = pivot_t['amt']
        pivot_t['구역총계(건수)'] = pivot_t['cnt']
        pivot_t = pivot_t[['std_ym','area_cd','area_nm','구역총계(금액)','구역총계(건수)']]
        pivot_s = df_s.pivot_table(values=['amt','cnt'], columns='ry_m_cd', index=['std_ym','area_cd','area_nm'], aggfunc=np.sum).reset_index().fillna(0)
        pivot_s.columns = [col if col[0] == "" else f"{col[0]}_{col[1]}" if isinstance(col, tuple) else col for col in pivot_s.columns]
        pivot_s['한식(금액)'] = pivot_s['amt_M014']
        pivot_s['한식(건수)'] = pivot_s['cnt_M014']
        pivot_s['일중양식(금액)'] = pivot_s['amt_M015'] + pivot_s['amt_M016'] + pivot_s['amt_M017']
        pivot_s['일중양식(건수)'] = pivot_s['cnt_M015'] + pivot_s['cnt_M016'] + pivot_s['cnt_M017']
        pivot_s['기타요식(금액)'] = pivot_s['amt_M018']
        pivot_s['기타요식(건수)'] = pivot_s['cnt_M018']
        pivot_s['음식료품(금액)'] = pivot_s['amt_M021']
        pivot_s['음식료품품(건수)'] = pivot_s['cnt_M021']
        pivot_s['수산소계(금액)'] = pivot_s['amt_M014'] + pivot_s['amt_M015'] + pivot_s['amt_M016'] + pivot_s['amt_M017'] + pivot_s['amt_M018'] + pivot_s['amt_M021']
        pivot_s['수산소계(건수)'] = pivot_s['cnt_M014'] + pivot_s['cnt_M015'] + pivot_s['cnt_M016'] + pivot_s['cnt_M017'] + pivot_s['cnt_M018'] + pivot_s['cnt_M021']
        pivot_s = pivot_s[['std_ym_','area_cd_','area_nm_','수산소계(금액)','한식(금액)','일중양식(금액)','기타요식(금액)',
                           '음식료품(금액)','수산소계(건수)','한식(건수)','일중양식(건수)','기타요식(건수)','음식료품품(건수)']]
        pivot_s.rename(columns={'std_ym_': 'std_ym', 'area_cd_': 'area_cd', 'area_nm_': 'area_nm'}, inplace=True)

        merge = pivot_t.merge(pivot_s, how="left", on=['std_ym','area_cd','area_nm'])
        merge = merge[['std_ym','area_cd','area_nm','구역총계(금액)','수산소계(금액)','한식(금액)','일중양식(금액)','기타요식(금액)',
                       '음식료품(금액)','구역총계(건수)','수산소계(건수)','한식(건수)','일중양식(건수)','기타요식(건수)','음식료품품(건수)']]
        
    result.append(merge)
    total = pd.concat(result, ignore_index=True)
    total.to_csv(output_path + "2024년_월별_재집계.csv", encoding="utf-8", index=False)