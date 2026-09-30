import pandas as pd
import calendar

path = "D:\\02_사업관리\\2025년\\데이터 구매 및 활용\\12_적재확인\\01_생활인구\\"
output = "D:\\02_사업관리\\2025년\\데이터 분석 컨설팅\\20251211_청년정책과\\"
gcode = pd.read_csv("D:\\02_사업관리\\코드자료\\부산구군코드.csv", sep=",", dtype={'gcode': str}, encoding="utf-8")

# 월별 일수 데이터프레임 생성
results2 = []
for year in range(2023, 2026):
    for month in range(1, 13):
        std_ym = str(year) + '-' + str(f"{month:02d}")
        daycnt = calendar.monthrange(year, month)[1]
        results2.append({'std_ym': std_ym, 'daycnt': daycnt})
daycnt = pd.DataFrame(results2).sort_values(['std_ym','daycnt']).reset_index(drop=True)

# 2025년 10월 별도집계
df = pd.read_csv(path + "kt_d_living_youth_emd_202510.csv", sep="|", dtype={'std_ymd': str, 'hcode': str, 'ages': str}, encoding="utf-8")
df['std_ymd'] = df['std_ymd'].astype('datetime64[ns]')
df['std_ym'] = df['std_ymd'].astype(str).str[:7]
df['gcode'] = df['hcode'].str[:5]
df['sum_pop'] = round(df.loc[:, ['h_pop','w_pop','v_pop']].sum(axis=1))

# 성별집계
group1 = round(df.groupby(['std_ym','gcode','gender'], as_index=False)['sum_pop'].sum())
group1 = pd.merge(group1, gcode, "left", "gcode")
group1 = pd.merge(group1, daycnt, "left", "std_ym")
group1['mean_pop'] = round(group1['sum_pop'] / 24 / group1['daycnt'])

group1.loc[group1['gender']=='M', "성별"] = "남성"
group1.loc[group1['gender']=='F', "성별"] = "여성"
group1 = group1[['std_ym','gname','성별','mean_pop']]
group1.columns = ['기준연월','구군','성별','인구수']
group1.to_excel(output + "구군별 성별 청년인구_202510.xlsx", engine="openpyxl", index=False)

# 연령집계
group2 = round(df.groupby(['std_ym','gcode','ages'], as_index=False)['sum_pop'].sum())
group2 = pd.merge(group2, gcode, "left", "gcode")
group2 = pd.merge(group2, daycnt, "left", "std_ym")
group2['mean_pop'] = round(group2['sum_pop'] / 24 / group2['daycnt'])
group2['연령'] = group2['ages'].str[:2] + "-" + group2['ages'].str[-2:] + "세"
group2 = group2[['std_ym','gname','연령','mean_pop']]
group2.columns = ['기준연월','구군','연령','인구수']
group2.to_excel(output + "구군별 연령 청년인구_202510.xlsx", engine="openpyxl", index=False)




