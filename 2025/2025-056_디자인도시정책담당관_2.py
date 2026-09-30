
import pandas as pd
import glob

data_path = glob.glob("D:\\02_사업관리\\2025년\\데이터 분석 컨설팅\\20251229_디자인도시정책담당관\\집계결과\\BUSAN_POI_INFLOW_FINAL\\*.csv", recursive=True)
output_path = "D:\\02_사업관리\\2025년\\데이터 분석 컨설팅\\20251229_디자인도시정책담당관\\집계결과\\"

res = []
for data in data_path:
    res.append(pd.read_csv(data, dtype={'ETL_YM': 'str', 'TIME': 'str', 'HCODE': 'str', 'INFLOW_CD': 'str'},
                           encoding="utf-8").rename(columns=str.lower))

df = pd.concat(res, ignore_index=True)
df['std_ym'] = df['etl_ym'].str[:4] + '-' + df['etl_ym'].str[-2:]

df.loc[~df['inflow_cd'].str.startswith('26'), 'class'] = '외지인'
df.loc[df['inflow_cd'].str.startswith('26'), 'class'] = '내지인'

group = round(df.groupby(['std_ym','id','time','class'])['pop'].sum()).unstack().reset_index().sort_values(by=['std_ym', 'time'])
group.to_csv(output_path + "월별_사업지_유입인구.csv", encoding="utf-8", index=False)
