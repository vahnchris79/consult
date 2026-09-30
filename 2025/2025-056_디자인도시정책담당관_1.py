
import pandas as pd

data_path = "D:\\02_사업관리\\2025년\\데이터 분석 컨설팅\\20251229_디자인도시정책담당관\\집계결과\\"

df1 = pd.read_csv(data_path + "월별 관광지 유입지별 방문인구.csv", dtype={'std_ym': 'str', 'inflow_cd': 'str'}, encoding="utf-8")
df2 = pd.read_csv("D:\\02_사업관리\\2025년\\데이터 구매 및 활용\\12_적재확인\\01_관광인구\\kt_m_tour_inflow_202510.csv",
                              sep="|", dtype={'std_ym': 'str', 'inflow_cd': 'str'}, encoding="utf-8")
df2 = df2.loc[df2['site_cd'] == 'A15'].copy()
df2 = df2[['std_ym','site_nm','inflow_cd','f_pop']]
df = pd.concat([df1, df2], ignore_index=True)
# print(df['std_ym'].unique())

df['yyyymm'] = df['std_ym'].str[:4] + '-' + df['std_ym'].str[-2:]

df.loc[~df['inflow_cd'].str.startswith('26'), 'class'] = '외지인'
df.loc[df['inflow_cd'].str.startswith('26'), 'class'] = '내지인'

group = round(df.groupby(['yyyymm','site_nm','class'])['f_pop'].sum()).unstack().reset_index().sort_values(by=['yyyymm'])
group.to_csv(data_path + "월별_관광지(송도해수욕장)_관광인구(추출).csv", encoding="utf-8", index=False)
