
from tqdm import tqdm
import pandas as pd
import calendar
import glob

path = "D:\\02_사업관리\\2025년\\데이터 구매 및 활용\\12_적재확인\\01_생활인구\\청년인구(연령시간)\\"
output = "D:\\02_사업관리\\2025년\\데이터 분석 컨설팅\\20251211_청년정책과\\"
gcode = pd.read_csv("D:\\02_사업관리\\코드자료\\부산구군코드.csv", sep=",", dtype={'gcode': str}, encoding="utf-8")

data_lists = glob.glob(path + "*.csv", recursive=True)
results1 = []

# 월별 합산 후 병합
for data in tqdm(data_lists):
    df = pd.read_csv(data, sep="|", dtype={'std_ymd': str, 'hcode': str, 'ages': str, 'tme': str}, encoding="utf-8")
    df['std_ymd'] = df['std_ymd'].astype('datetime64[ns]')
    df['weekday'] = df['std_ymd'].dt.day_name('ko_KR')
    df['std_ym'] = df['std_ymd'].astype(str).str[:7]
    df['gcode'] = df['hcode'].str[:5]
    df['sum_pop'] = round(df.loc[:, ['h_pop','w_pop','v_pop']].sum(axis=1))
    results1.append(df.groupby(['std_ym','gcode','ages','tme'], as_index=False)['sum_pop'].sum())
group = pd.concat(results1, ignore_index=True).sort_values(['std_ym','gcode','ages','tme'])
group = pd.merge(group, gcode, "left", "gcode")

# 월별 일수 데이터프레임 생성
results2 = []
for year in range(2023, 2026):
    for month in range(1, 13):
        std_ym = str(year) + '-' + str(f"{month:02d}")
        daycnt = calendar.monthrange(year, month)[1]
        results2.append({'std_ym': std_ym, 'daycnt': daycnt})
daycnt = pd.DataFrame(results2).sort_values(['std_ym','daycnt']).reset_index(drop=True)

# 월별 일평균
group = group.merge(daycnt, "left", "std_ym")
group['avg_pop'] = group['sum_pop'] / group['daycnt']
group['연령'] = group['ages'].str[:2] + "-" + group['ages'].str[-2:] + "세"
group['시간'] = group['tme'] + "시"
group = group[['std_ym','gname','연령','시간','avg_pop']]
group.columns = ['기준연월', '구군', '연령', '시간', '인구수']
group.to_excel(output + "구군별 연령시간별 청년인구 현황.xlsx", engine="openpyxl", index=False)
