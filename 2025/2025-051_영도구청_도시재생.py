
import pandas as pd


path = "D:/02_사업관리/2025년/데이터 분석 컨설팅/20251128_영도구청/02_집계결과/"
df = pd.read_csv(path + "행정동별 가맹점 창폐업 카드소비 데이터(영도구 봉래1동)_251201.csv",
                   dtype={'std_ym': str, 'hcode': str, 'ry_s_cd': str}, encoding="utf-8")
code = pd.read_csv("D:/02_사업관리/코드자료/bccd_sec_code.csv", sep="|", dtype={'ry_s_cd': str}, encoding="utf-8")

df['std_ym2'] = df['std_ym'].str[:4] + "-" + df['std_ym'].str[-2:]
df = df.merge(code, "left", "ry_m_cd")

group = df.groupby(['std_ym2','ry_m_nm','card_pos'])[['lat_mct_cnt','opa_mct_cnt','me_mct_cnt']].sum().reset_index().sort_values('std_ym2', ascending=True)
group = group.melt(id_vars=['std_ym2','ry_m_nm'], value_vars=['lat_mct_cnt','opa_mct_cnt','me_mct_cnt'], var_name='class', value_name='cnt')
group.loc[group['class'].str.startswith('lat'), '운영분류'] = '신규'
group.loc[group['class'].str.startswith('opa'), '운영분류'] = '영업'
group.loc[group['class'].str.startswith('me'), '운영분류'] = '폐업'
group = group[['std_ym2','ry_m_nm','운영분류','cnt']]
group.columns = ['기준연월', '업종중분류', '운영분류', '창폐업건수']
group.to_csv(path + "월별_행정동_창폐업현황_202301-202305.csv", sep=",", encoding="utf-8", index=False)