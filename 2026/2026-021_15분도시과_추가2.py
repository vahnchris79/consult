import pandas as pd
import glob
import warnings
warnings.filterwarnings('ignore')

hcode = pd.read_csv(r"D:\\02_사업관리\\코드자료\\부산행정동코드.csv", dtype={'hcode': str}, encoding="utf-8")
idlist_2022 = pd.read_csv(r"D:\\02_사업관리\\2026년\\데이터 분석 컨설팅\\20260723_15분도시과\\대상영역\\사업지변경_22년.csv",
                                                 sep="|", dtype={'id': str}, encoding="utf-8")
idlist_2325 = pd.read_csv(r"D:\\02_사업관리\\2026년\\데이터 분석 컨설팅\\20260723_15분도시과\\대상영역\\사업지변경_23-25년.csv",
                                                  sep="|", dtype={'id': str}, encoding="utf-8")
data_lists = glob.glob(r"D:\\02_사업관리\\자체분석\\01_생활인구\\50m\\*.csv", recursive=True)
output_path = r"D:\\02_사업관리\\2026년\\데이터 분석 컨설팅\\20260723_15분도시과\\집계결과\\"

def extract(data_lists, idlist):
    values = []
    for data in data_lists:
        df = pd.read_csv(data, sep="|", dtype={'std_ymd': str, 'hcode': str, 'id': str}, encoding="utf-8")
        df['std_ymd'] = df['std_ymd'].astype('datetime64[ns]')
        df['std_ym'] = df['std_ymd'].astype(str).str[:7]
        df = pd.merge(idlist, df, on="id", how="inner")
        df = pd.merge(df, hcode, on="hcode", how="inner")
        # 분기별 마지막 7일 추출
        df['quarter'] = df['std_ymd'].dt.to_period('Q')
        q_end = (df.groupby('quarter')['std_ymd'].max().reset_index(name='week_end'))
        q_end['week_start'] = q_end['week_end'] - pd.Timedelta(days=6)
        merged = df.merge(q_end, "left", "quarter")
        values.append(merged.loc[(merged['std_ymd'] >= merged['week_start']) & (merged['std_ymd'] <= merged['week_end'])].sort_values('std_ymd'))
    # merged = merged.loc[(merged['std_ymd'] >= merged['week_start']) & (merged['std_ymd'] <= merged['week_end'])].sort_values('std_ymd')
    concated = pd.concat(values, ignore_index=True)
    return concated

def weekday(data_lists, idlist):
    print("주간시간대 생활인구 집계시작")
    df = extract(data_lists, idlist)
    weekday_dict = {
        '10H': ['h_t_10','w_t_10','v_t_10'], '11H': ['h_t_11','w_t_11','v_t_11'], '12H': ['h_t_12','w_t_12','v_t_12'],
        '13H': ['h_t_13','w_t_13','v_t_13'], '14H': ['h_t_14','w_t_14','v_t_14'], '15H': ['h_t_15','w_t_15','v_t_15'],
        '16H': ['h_t_16','w_t_16','v_t_16'],}
    for key, value in weekday_dict.items():
        df[key] = df.loc[:, value].sum(axis=1)
    keys = [key for key in weekday_dict.keys()]
    group = df.groupby(['std_ym','hname','id','사업명'], as_index=False)[keys].sum().round()
    group.columns = ['기준연월','행정동명','ID','사업명','10시','11시','12시','13시','14시','15시','16시']
    print("주간시간대 생활인구 집계완료")
    return group

def over60min(data_lists, idlist):
    print("\n60분이상 체류인구 집계시작")
    df = extract(data_lists, idlist)
    visitor_dicts = {
        '00-01H': ['v_t_00', 'v_t_01'], '02-03H': ['v_t_02', 'v_t_03'], '04-05H': ['v_t_04', 'v_t_05'],
        '06-07H': ['v_t_06', 'v_t_07'], '08-09H': ['v_t_08', 'v_t_09'], '10-11H': ['v_t_10', 'v_t_11'],
        '12-13H': ['v_t_12', 'v_t_13'], '14-15H': ['v_t_14', 'v_t_15'], '16-17H': ['v_t_16', 'v_t_17'],
        '18-19H': ['v_t_18', 'v_t_19'], '20-21H': ['v_t_20', 'v_t_21'], '22-23H': ['v_t_22', 'v_t_23'],}
    for key, value in visitor_dicts.items():
        df[key] = df.loc[:, value].sum(axis=1)
    keys = [key for key in visitor_dicts.keys()]
    group = df.groupby(['std_ym','hname','id','사업명'], as_index=False)[keys].sum().round()
    group.columns = ['기준연월','행정동','ID','사업명','00-01시','02-03시','04-05시','06-07시',
                     '08-09시','10-11시','12-13시','14-15시','16-17시','18-19시','20-21시','22-23시']
    print("60분이상 체류인구 집계시작")
    return group

weekday(data_lists, idlist_2325).to_excel(output_path + "주간시간대_생활인구_현황_2526년.xlsx", engine='openpyxl', index=False)
over60min(data_lists, idlist_2325).to_excel(output_path + "60분이상_체류인구_현황_2526년.xlsx", engine='openpyxl', index=False)