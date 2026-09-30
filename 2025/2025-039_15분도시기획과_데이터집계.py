
import pandas as pd

output_path = "D:/02_사업관리/2025년/데이터 분석 컨설팅/20250915_15분도시기획과/02_집계결과/"

df = pd.read_csv("D:/02_사업관리/2025년/데이터 구매 및 활용/12_적재확인/생활인구/kt_d_living_tme_p_202509.csv",
                 sep="|", dtype={'std_ymd': str, 'hcode': str, 'id': str}, encoding="utf-8")
hcode = pd.read_csv("D:/02_사업관리/코드자료/부산행정동코드.csv", sep=",", 
                    dtype={'hcode': str}, encoding="utf-8")
grdlst = pd.read_csv("D:/02_사업관리/2025년/데이터 분석 컨설팅/20250915_15분도시기획과/02_대상영역/grdlst_20251029.csv",
                    sep=",", dtype={'id': str}, encoding="utf-8")

df['std_ymd'] = pd.to_datetime(df['std_ymd'])
cols = [col for col in df.columns if '_t_' in col]
df[cols] = df[cols].astype(float)


# 주간시간(10시~16시) 생활인구
df['t10'] = df.iloc[:, [13, 37, 61]].sum(axis=1)
df['t11'] = df.iloc[:, [14, 38, 62]].sum(axis=1)
df['t12'] = df.iloc[:, [15, 39, 63]].sum(axis=1)
df['t13'] = df.iloc[:, [16, 40, 64]].sum(axis=1)
df['t14'] = df.iloc[:, [17, 41, 65]].sum(axis=1)
df['t15'] = df.iloc[:, [18, 42, 66]].sum(axis=1)
df['t16'] = df.iloc[:, [19, 43, 67]].sum(axis=1)

# 60분이상 체류인구
for i in range(52, 76):
    df['v0001'] = df.iloc[:, [52, 53]].sum(axis=1)
    df['v0203'] = df.iloc[:, [54, 55]].sum(axis=1)
    df['v0405'] = df.iloc[:, [56, 57]].sum(axis=1)
    df['v0607'] = df.iloc[:, [58, 59]].sum(axis=1)
    df['v0809'] = df.iloc[:, [60, 61]].sum(axis=1)
    df['v1011'] = df.iloc[:, [62, 63]].sum(axis=1)
    df['v1213'] = df.iloc[:, [64, 65]].sum(axis=1)
    df['v1415'] = df.iloc[:, [66, 67]].sum(axis=1)
    df['v1617'] = df.iloc[:, [68, 69]].sum(axis=1)
    df['v1819'] = df.iloc[:, [70, 71]].sum(axis=1)
    df['v2021'] = df.iloc[:, [72, 73]].sum(axis=1)
    df['v2223'] = df.iloc[:, [74, 75]].sum(axis=1)

df = pd.merge(df, hcode, "left", "hcode")
df2 = grdlst.merge(df, "left", "id")

# 분기별 마지막 7일 추출
df2['quarter'] = df2['std_ymd'].dt.to_period('Q')
q_end = (df2.groupby('quarter')['std_ymd'].max().reset_index(name='week_end'))
q_end['week_start'] = q_end['week_end'] - pd.Timedelta(days=6)
df3 = df2.merge(q_end, "left", "quarter")
df3 = df3.loc[(df3['std_ymd'] >= df3['week_start']) & (df3['std_ymd'] <= df3['week_end'])].sort_values('std_ymd')

# 월별 집계
df3['std_ym'] = df3['std_ymd'].astype(str).str[:7]
cols1 = [col for col in df3.columns if 't1' in col]
cols2 = [col for col in df3.columns if 'v0' in col or 'v1' in col or 'v2' in col]
result1 = round(df3.groupby(['std_ym','hname','id','사업명'])[cols1].sum()).reset_index().sort_values('std_ym', ascending=True)
result1.columns = ['기준연월','행정동','ID','사업지명','10시','11시','12시','13시','14시','15시','16시']
result2 = round(df3.groupby(['std_ym','hname','id','사업명'])[cols2].sum()).reset_index().sort_values('std_ym', ascending=True)
result2.columns = ['기준연월','행정동','ID','사업지명','00~01시','02~03시','04~05시','06~07시','08~09시',
                   '10~11시','12~13시','14~15시','16~17시','18~19시','20~21시','22~23시']

result1.to_csv(output_path + "result1.csv", sep=",", encoding="utf-8", index=False)
result2.to_csv(output_path + "result2.csv", sep=",", encoding="utf-8", index=False)