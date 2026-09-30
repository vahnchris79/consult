
from datetime import datetime
import calendar
import pandas as pd
import glob

data_lists = glob.glob("D:/05_외부지원/20251110_청년정책과/data/*.csv", recursive=True)
gcode = pd.read_csv("D:/02_사업관리/코드자료/부산구군코드.csv", sep=",", dtype={'gcode': str}, encoding="utf-8")
output_path = "D:/05_외부지원/20251110_청년정책과/result/"

all_genders = []
all_ages = []
youth_genders = []
youth_ages = []

# 월별 일수 데이터프레임 생성
cnt = []
for month in range(1, 13):
    _, daycnt = calendar.monthrange(2025, month)
    cnt.append([f"2025-{month:02d}", daycnt])
daycnt = pd.DataFrame(cnt, columns=['std_ym','daycnt'])

def common(df):
    df['std_ymd'] = df['std_ymd'].astype('datetime64[ns]').astype(str)
    df['std_ym'] = df['std_ymd'].str[:7]
    df['gcode'] = df['hcode'].str[:5]
    df = pd.merge(df, gcode, "left", "gcode")
    return df

def all_preprocess(df):
    df = common(df)
    df.loc[df['gender'].str.contains('M'), '성별'] = '남성'
    df.loc[df['gender'].str.contains('F'), '성별'] = '여성'
    df.loc[df['ages'].str.contains('00|10|15'), '연령'] = '20대미만'
    df.loc[df['ages'].str.contains('20|25'), '연령'] = '20대'
    df.loc[df['ages'].str.contains('30|35'), '연령'] = '30대'
    df.loc[df['ages'].str.contains('40|45'), '연령'] = '40대'
    df.loc[df['ages'].str.contains('50|55'), '연령'] = '50대'
    df.loc[df['ages'].str.contains('60|65'), '연령'] = '60대'
    df.loc[df['ages'].str.contains('70|75'), '연령'] = '70대이상'
    df['total_pop'] = round(df.loc[:, ['h_pop','w_pop','v_pop']].sum(axis=1) / 24, 2)
    return df

def youth_preprocess(df):
    df = common(df)
    df.loc[df['gender'].str.contains('m'), '성별'] = '남성'
    df.loc[df['gender'].str.contains('f'), '성별'] = '여성'
    df.loc[df['ages'].str.contains('1821'), '연령'] = '18~21세'
    df.loc[df['ages'].str.contains('22|26'), '연령'] = '22~29세'
    df.loc[df['ages'].str.contains('30|34'), '연령'] = '30~37세'
    df.loc[df['ages'].str.contains('38|41'), '연령'] = '38~39세'
    df['total_pop'] = round(df.loc[:, ['h_pop','w_pop','v_pop']].sum(axis=1) / 24, 2)
    return df

def aggregate_gender(df):
    all_genders.append(df.groupby(['std_ym','gcode','gname','성별'],
                                  as_index=False)['total_pop'].sum().sort_values(['std_ym','gcode'], ascending=True))
    group = pd.concat(all_genders, ignore_index=True)
    group = pd.merge(group, daycnt, "left", "std_ym")
    group['mean_pop'] = round(group['total_pop'] / group['daycnt'])
    group = group[['std_ym', 'gname', '성별', 'mean_pop']]
    group.columns = ['기준연월', '구군', '성별', '전체인구']
    group.to_csv(output_path + "2025년 부산시 생활인구(전체) 성별현황.csv", sep=",", index=False)
    return group

def aggregate_ages(df):
    all_ages.append(df.groupby(['std_ym','gcode', 'gname','연령'],
                               as_index=False)['total_pop'].sum().sort_values(['std_ym','gcode'], ascending=True))
    group = pd.concat(all_ages, ignore_index=True)
    group = pd.merge(group, daycnt, "left", "std_ym")
    group['mean_pop'] = round(group['total_pop'] / group['daycnt'])
    group = group[['std_ym', 'gname', '연령', 'mean_pop']]
    group.columns = ['기준연월', '구군', '연령', '전체인구']    
    group.to_csv(output_path + "2025년 부산시 생활인구(전체) 연령현황.csv", sep=",", index=False)
    return group

def aggregate_youth_gender(df):
    youth_genders.append(df.groupby(['std_ym','gcode','gname','성별'],
                                    as_index=False)['total_pop'].sum().sort_values(['std_ym','gcode'], ascending=True))
    group = pd.concat(youth_genders, ignore_index=True)
    group = pd.merge(group, daycnt, "left", "std_ym")
    group['mean_pop'] = round(group['total_pop'] / group['daycnt'])
    group = group[['std_ym', 'gname', '성별', 'mean_pop']]
    group.columns = ['기준연월', '구군', '성별', '전체인구']
    group.to_csv(output_path + "2025년 부산시 생활인구(청년) 성별현황.csv", sep=",", index=False)
    return group

def aggregate_youth_ages(df):
    youth_ages.append(df.groupby(['std_ym','gcode', 'gname','연령'],
                                 as_index=False)['total_pop'].sum().sort_values(['std_ym','gcode'], ascending=True))
    group = pd.concat(youth_ages, ignore_index=True)
    group = pd.merge(group, daycnt, "left", "std_ym")
    group['mean_pop'] = round(group['total_pop'] / group['daycnt'])
    group = group[['std_ym', 'gname', '연령', 'mean_pop']]
    group.columns = ['기준연월', '구군', '연령', '전체인구']    
    group.to_csv(output_path + "2025년 부산시 생활인구(청년) 연령현황.csv", sep=",", index=False)
    return group

for data in data_lists:
    if '_living_emd_' in data:
        df = pd.read_csv(data, sep="|", dtype={'std_ymd': str, 'hcode': str, 'ages': str},  encoding="utf-8")
        df = all_preprocess(df)
        aggregate_gender(df)
        aggregate_ages(df)
    elif '_living_youth_emd_' in data:
        df = pd.read_csv(data, sep="|", dtype={'std_ymd': str, 'hcode': str, 'ages': str},  encoding="utf-8")
        df = youth_preprocess(df)
        aggregate_youth_gender(df) 
        aggregate_youth_ages(df)
