import pandas as pd
import numpy as np
import re


path = "D:/02_사업관리/2025년/데이터 분석 컨설팅/20250808_금정구청/"

# emd = inputs[0].drop(columns=['dat_flow_id', 'part_batchdate'])
tme = pd.read_csv(path + "00_data/skt_d_service_time_p_202403.csv", sep="|", dtype={'std_ymd': str, 'hcode': str, 'id': str},
                  encoding="utf-8")
grdlst = pd.read_csv(path + "02_대상구역/grdlst_26410_20250808_v1.csv", dtype={'id': str}, encoding="utf-8")
hcode = pd.read_csv("D:/02_사업관리/코드자료/부산행정동코드.csv", sep=",", dtype={'hcode': str}, encoding="utf-8")

# 대상영역기준 서비스인구 추출
# merged1 = grdlst.merge(, how="left", on="id")
merged2 = grdlst.merge(tme, how="left", on="id")

def extract_columns(df):
    emd_cols = [c for c in df.columns if re.fullmatch(r'[hwv]_[mw]_\d{4}', c)]
    time_cols = [c for c in df.columns if re.fullmatch(r'[hwv]_t_\d{2}', c)]
    return emd_cols + time_cols

def dataprocessing(df):
    cols = extract_columns(df)
    df[cols] = df[cols].astype(float)
    df = df.drop(columns=['dat_flow_id','part_batchdate'], errors='ignore')
    # 날짜 처리
    df['std_ymd'] = pd.to_datetime(df['std_ymd'], format="%Y%m%d")
    df['std_ym'] = df['std_ymd'].astype(str).str[:7]
    df['dayname'] = df['std_ymd'].dt.day_name('ko_KR')
    df = pd.merge(df, hcode, "left", "hcode")
    return df

# -------------------------
# 공통 라벨링 함수
# -------------------------
def label_registed(df):
    df.loc[df['class'].str.startswith('h'), 'registed'] = '주거'
    df.loc[df['class'].str.startswith('w'), 'registed'] = '직장'
    df.loc[df['class'].str.startswith('v'), 'registed'] = '방문'
    return df

def label_gender(df):
    df.loc[df['class'].str.contains('_m'), 'gender'] = '남성'
    df.loc[df['class'].str.contains('_w'), 'gender'] = '여성'
    return df

def label_ages(df):
    age_map = {
        '20le': '20대미만', '20eq': '20대', '30eq': '30대',
        '40eq': '40대', '50eq': '50대', '60gt': '60대이상'
    }
    for k, v in age_map.items():
        df.loc[df['class'].str.endswith(k), 'ages'] = v
    return df

def label_times(df):
    hr = df['class'].str.extract(r'_t_(\d{2})', expand=False)
    df['time'] = hr.apply(lambda x: f"{int(x):02d}시" if pd.notnull(x) else None)
    df.loc[df['time'].str.contains('07시|08시|09시|10시'), 'times'] = '오전'
    df.loc[df['time'].str.contains('11시|12시|13시|14시'), 'times'] = '점심'
    df.loc[df['time'].str.contains('15시|16시|17시|18시'), 'times'] = '오후'
    df.loc[df['time'].str.contains('19시|20시|21시|22시'), 'times'] = '저녁'
    df.loc[df['time'].str.contains('23시|00시|01시|02시'), 'times'] = '야간'
    df.loc[df['time'].str.contains('03시|04시|05시|06시'), 'times'] = '심야'
    return df

# -------------------------
# 성별 집계
# -------------------------
def aggregate_gender(df):
    df = dataprocessing(df)
    gender_dict = {
        'h_m': [f'h_m_{age}' for age in ['0009','1014','1519','2024','2529','3034','3539',
                                         '4044','4549','5054','5559','6064','6569','7000']],
        'h_w': [f'h_w_{age}' for age in ['0009','1014','1519','2024','2529','3034','3539',
                                         '4044','4549','5054','5559','6064','6569','7000']],
        'w_m': [f'w_m_{age}' for age in ['0009','1014','1519','2024','2529','3034','3539',
                                         '4044','4549','5054','5559','6064','6569','7000']],
        'w_w': [f'w_w_{age}' for age in ['0009','1014','1519','2024','2529','3034','3539',
                                         '4044','4549','5054','5559','6064','6569','7000']],
        'v_m': [f'v_m_{age}' for age in ['0009','1014','1519','2024','2529','3034','3539',
                                         '4044','4549','5054','5559','6064','6569','7000']],
        'v_w': [f'v_w_{age}' for age in ['0009','1014','1519','2024','2529','3034','3539',
                                         '4044','4549','5054','5559','6064','6569','7000']]
    }
    for key, cols in gender_dict.items():
        df[key] = df[cols].sum(axis=1)
    keys = list(gender_dict.keys())
    group = df.groupby(['std_ym','dayname','hname','id'])[keys].sum().reset_index()
    melted = group.melt(id_vars=['std_ym','dayname','hname','id'], value_vars=keys,
                        var_name='class', value_name='pop')
    melted = label_registed(melted)
    melted = label_gender(melted)
    return melted[['std_ym','dayname','hname','id','registed','gender','pop']]

# -------------------------
# 연령 집계
# -------------------------
def aggregate_ages(df):
    df = dataprocessing(df)
    ages_dict = {
        'h_20le': ['h_m_0009','h_m_1014','h_m_1519','h_w_0009','h_w_1014','h_w_1519'],
        'h_20eq': ['h_m_2024','h_m_2529','h_w_2024','h_w_2529'],
        'h_30eq': ['h_m_3034','h_m_3539','h_w_3034','h_w_3539'],
        'h_40eq': ['h_m_4044','h_m_4549','h_w_4044','h_w_4549'],
        'h_50eq': ['h_m_5054','h_m_5559','h_w_5054','h_w_5559'],
        'h_60gt': ['h_m_6064','h_m_6569','h_m_7000','h_w_6064','h_w_6569','h_w_7000'],
        'w_20le': ['w_m_0009','w_m_1014','w_m_1519','w_w_0009','w_w_1014','w_w_1519'],
        'w_20eq': ['w_m_2024','w_m_2529','w_w_2024','w_w_2529'],
        'w_30eq': ['w_m_3034','w_m_3539','w_w_3034','w_w_3539'],
        'w_40eq': ['w_m_4044','w_m_4549','w_w_4044','w_w_4549'],
        'w_50eq': ['w_m_5054','w_m_5559','w_w_5054','w_w_5559'],
        'w_60gt': ['w_m_6064','w_m_6569','w_m_7000','w_w_6064','w_w_6569','w_w_7000'],
        'v_20le': ['v_m_0009','v_m_1014','v_m_1519','v_w_0009','v_w_1014','v_w_1519'],
        'v_20eq': ['v_m_2024','v_m_2529','v_w_2024','v_w_2529'],
        'v_30eq': ['v_m_3034','v_m_3539','v_w_3034','v_w_3539'],
        'v_40eq': ['v_m_4044','v_m_4549','v_w_4044','v_w_4549'],
        'v_50eq': ['v_m_5054','v_m_5559','v_w_5054','v_w_5559'],
        'v_60gt': ['v_m_6064','v_m_6569','v_m_7000','v_w_6064','v_w_6569','v_w_7000']
    }
    for key, cols in ages_dict.items():
        df[key] = df[cols].sum(axis=1)

    keys = list(ages_dict.keys())
    group = df.groupby(['std_ym','dayname','hname','id'])[keys].sum().reset_index()
    melted = group.melt(id_vars=['std_ym','dayname','hname','id'], value_vars=keys,
                        var_name='class', value_name='pop')

    melted = label_registed(melted)
    melted = label_ages(melted)
    return melted[['std_ym','dayname','hname','id','registed','ages','pop']]

# -------------------------
# 시간대 집계
# -------------------------
def aggregate_times(df):
    df = dataprocessing(df)
    # 시간대 컬럼만 추출
    t_cols = [c for c in df.columns if re.fullmatch(r'[hwv]_t_\d{2}', c)]
    group = (df.groupby(['std_ym','dayname','hname','id'])[t_cols].sum()/4).reset_index()
    group = group.dropna()
    melted = group.melt(id_vars=['std_ym','dayname','hname','id'], value_vars=t_cols,
                        var_name='class', value_name='pop')
    melted = label_registed(melted)
    melted = label_times(melted)
    return melted[['std_ym','dayname','hname','id','registed','times','pop']]

# gender = aggregate_gender(merged1)
# age = aggregate_ages(merged1)
time = aggregate_times(merged2).to_csv(path + "03_집계결과/result_202403_time.csv", sep=",", encoding="utf-8", index=False)