
import pandas as pd
import glob
import calendar

path = "D:\\02_사업관리\\2025년\\데이터 구매 및 활용\\12_적재확인\\01_생활인구\\행정동 시간대\\"
data_lists = glob.glob(path + "*.csv", recursive=True)
gcode = pd.read_csv("D:\\02_사업관리\\코드자료\\부산구군코드.csv", dtype={'gcode': str}, encoding="utf-8")
output = "D:\\02_사업관리\\2025년\\데이터 분석 컨설팅\\20251212_인구정책담당관\\"

daylists = []
for year in range(2023, 2026):
    for month in range(1, 13):
        std_ym = str(year) + '-' + str(f"{month:02d}")
        daycnt = calendar.monthrange(year, month)[1]
        daylists.append({'std_ym': std_ym, 'daycnt': daycnt})
daycnt = pd.DataFrame(daylists).sort_values(['std_ym','daycnt'], ascending=True).reset_index(drop=True)

results = []
for data in data_lists:
    df = pd.read_csv(data, sep="|", dtype={'std_ymd': str, 'hcode': str, 'tme': str}, encoding="utf-8")
    df['std_ymd'] = df['std_ymd'].astype('datetime64[ns]').astype(str)
    df['std_ym'] = df['std_ymd'].str[:7]
    df['gcode'] = df['hcode'].str[:5]
    results.append(round(df.groupby(['std_ym','gcode'], as_index=False)[['h_pop','w_pop','v_pop']].sum()))

group = pd.concat(results, ignore_index=True)
group = group.merge(gcode, "left", "gcode")
group = group.merge(daycnt, "left", "std_ym")
group['h_mean'] = round(group['h_pop'] / 24 / group['daycnt'])
group['w_mean'] = round(group['w_pop'] / 24 /  group['daycnt'])
group['v_mean'] = round(group['v_pop'] / 24 / group['daycnt'])
group = group[['std_ym','gname','h_mean','w_mean','v_mean']]
group = group.melt(id_vars=['std_ym','gname'], value_vars=['h_mean','w_mean','v_mean'], var_name='class', value_name='pop')
group.loc[group['class'].str.startswith('h'), '목적'] = '거주'
group.loc[group['class'].str.startswith('w'), '목적'] = '직장'
group.loc[group['class'].str.startswith('v'), '목적'] = '방문'
group = group[['std_ym','gname','목적','pop']]
group.columns = ['기준연월','구군','목적','인구수']
group.to_excel(output + "생활인구집계.xlsx", engine="openpyxl", index=False)