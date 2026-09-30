import pandas as pd
import numpy as np
import calendar

path = "D:\\02_사업관리\\2025년\\데이터 구매 및 활용\\12_적재확인\\"
output = "D:\\02_사업관리\\2025년\\데이터 분석 컨설팅\\20251117_금정구청\\02_집계결과\\"
emd = pd.read_csv(path + "01_생활인구\\kt_d_living_emd_202511.csv", sep="|", 
                  dtype={'std_ymd': str, 'hcode': str, 'ages': str}, encoding="utf-8")
tme = pd.read_csv(path + "01_생활인구\\kt_d_living_tme_202511.csv", sep="|", 
                  dtype={'std_ymd': str, 'hcode': str, 'tme': str}, encoding="utf-8")
sec = pd.read_csv(path + "02_카드이용\\bccd_d_sec_202511.csv", sep="|", 
                  dtype={'std_ymd': str, 'hcode': str}, encoding="utf-8")
code = pd.read_csv("D:\\02_사업관리\\코드자료\\bccd_sec_code.csv", sep="|", encoding="utf-8")
code2 = code.drop_duplicates(subset=['ry_m_cd','ry_m_nm'], keep='first')
print(code['ry_m_nm'].unique())
results = []
for year in range(2023, 2026):
    for month in range(1, 13):
        std_ym = str(year) + "-" + str(f"{month:02d}")
        daycnt = calendar.monthrange(year, month)[1]
        results.append({"std_ym": std_ym, "daycnt": daycnt})
daycnt = pd.DataFrame(results).sort_values(['std_ym','daycnt'], ascending=False).reset_index(drop=True)

def filtered(df):
    df = df[df['hcode'] == '2641067000'].copy()
    df['std_ymd'] = df['std_ymd'].astype('datetime64[ns]')
    df['weekday'] = df['std_ymd'].dt.day_name('ko_KR')
    df['std_ym'] = df['std_ymd'].astype(str).str[:7]
    df['hname'] = "남산동"
    if 'ry_m_cd' in df.columns:
        df = df.merge(code2, "left", "ry_m_cd")
    return df

def gender(df):
    df = filtered(df)
    group = df.groupby(['std_ym','weekday','hname','gender'], as_index=False)[['h_pop','w_pop','v_pop']].sum()
    group = group.merge(daycnt, "left", "std_ym")
    group['h_mean'] = round(group['h_pop'] / 24 / group['daycnt']).astype(int)
    group['w_mean'] = round(group['w_pop'] / 24 / group['daycnt']).astype(int)
    group['v_mean'] = round(group['v_pop'] / 24 / group['daycnt']).astype(int)
    group = group.melt(id_vars=['std_ym','weekday','hname','gender'], value_vars=['h_mean','w_mean','v_mean'], var_name='class', value_name='pop')
    group.loc[group['gender']=='M', '성별'] = '남성'
    group.loc[group['gender']=='F', '성별'] = '여성'
    group.loc[group['class'].str.startswith('h'), '구분'] = '주거'
    group.loc[group['class'].str.startswith('w'), '구분'] = '직장'
    group.loc[group['class'].str.startswith('v'), '구분'] = '방문'
    group = group[['std_ym','weekday','hname','성별','구분','pop']]
    group.columns = ['기준연월','요일','행정동','성별','구분','인구수']
    return group

def ages(df):
    df = filtered(df)
    group = df.groupby(['std_ym','weekday','hname','ages'], as_index=False)[['h_pop','w_pop','v_pop']].sum()
    group = group.merge(daycnt, "left", "std_ym")
    group['h_mean'] = round(group['h_pop'] / 24 / group['daycnt']).astype(int)
    group['w_mean'] = round(group['w_pop'] / 24 / group['daycnt']).astype(int)
    group['v_mean'] = round(group['v_pop'] / 24 / group['daycnt']).astype(int)
    group = group.melt(id_vars=['std_ym','weekday','hname','ages'], value_vars=['h_mean','w_mean','v_mean'], 
                             var_name='class', value_name='pop')
    group.loc[group['ages'].str.contains('0009|1014|1519'), "연령"] = '20대미만'
    group.loc[group['ages'].str.contains('2024|2529'), "연령"] = '20대'
    group.loc[group['ages'].str.contains('3034|3539'), "연령"] = '30대'
    group.loc[group['ages'].str.contains('4044|4549'), "연령"] = '40대'
    group.loc[group['ages'].str.contains('5054|5559'), "연령"] = '50대'
    group.loc[group['ages'].str.contains('6064|6569|7074|7500'), "연령"] = '60대이상'
    group.loc[group['class'].str.startswith('h'), '구분'] = '주거'
    group.loc[group['class'].str.startswith('w'), '구분'] = '직장'
    group.loc[group['class'].str.startswith('v'), '구분'] = '방문'
    group = group[['std_ym','weekday','hname','연령','구분','pop']]
    group.columns = ['기준연월','요일','행정동','연령','구분','인구수']
    return group

def times(df):
    df = filtered(df)
    group = df.groupby(['std_ym','weekday','hname','tme'], as_index=False)[['h_pop','w_pop','v_pop']].sum()
    group = group.merge(daycnt, "left", "std_ym")
    group['h_mean'] = round(group['h_pop'] / group['daycnt']).astype(int)
    group['w_mean'] = round(group['w_pop'] / group['daycnt']).astype(int)
    group['v_mean'] = round(group['v_pop'] / group['daycnt']).astype(int)
    group = group.melt(id_vars=['std_ym','weekday','hname','tme'], value_vars=['h_mean','w_mean','v_mean'], 
                             var_name='class', value_name='pop')
    group['시간'] = group['tme'] + "시"
    group.loc[group['class'].str.startswith('h'), '구분'] = '주거'
    group.loc[group['class'].str.startswith('w'), '구분'] = '직장'
    group.loc[group['class'].str.startswith('v'), '구분'] = '방문'
    group = group[['std_ym','weekday','hname','시간','구분','pop']]
    group.columns = ['기준연월','요일','행정동','시간','구분','인구수']
    return group

def industry(df):
    df = filtered(df)
    group = df.groupby(['std_ym','weekday','hname','ry_m_nm'], as_index=False)[['amt','cnt']].sum()
    weekday_cnt = group.groupby(['std_ym','weekday'])['weekday'].count().reset_index(name='weekcnt')
    group = group.merge(weekday_cnt, "left", on=["std_ym","weekday"])
    group['amt_mean'] = round(group['amt'] / group['weekcnt']).astype(int)
    group['cnt_mean'] = round(group['cnt'] / group['weekcnt']).astype(int)
    group = group[['std_ym','weekday','hname','ry_m_nm','amt_mean','cnt_mean']]
    group.columns = ['기준연월','요일','행정동','업종중분류명','매출금액','매출건수']
    return group

# gender(emd).to_csv(output + "월별_성별_생활인구_2511.csv", sep=",", index=False)
# ages(emd).to_csv(output + "월별_연령_생활인구_2511.csv", sep=",", index=False)
# times(tme).to_csv(output + "월별_시간_생활인구_2511.csv", sep=",", index=False)
industry(sec).to_csv(output + "월별 일평균 업종 카드이용_2511(6).csv", sep=",", index=False)
# print(round(industry(sec).pivot_table(columns='기준연월', values='매출금액', aggfunc=np.sum)/100000000, 3))

print("Done!")