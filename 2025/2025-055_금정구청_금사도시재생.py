

import pandas as pd

workspace = "D:\\02_사업관리\\2025년\\데이터 분석 컨설팅\\20251125_금정구청\\도시재생\\02_대상지역\\"
data_path1 = "D:\\02_사업관리\\2025년\\데이터 구매 및 활용\\12_적재확인\\02_카드이용\\"
data_path2 = "D:\\02_사업관리\\코드자료\\"
output = "D:\\02_사업관리\\2025년\\데이터 분석 컨설팅\\20251125_금정구청\\도시재생\\"
sec = pd.read_csv(data_path1 + "bccd_d_sec_p_202510.csv", sep="|", dtype={'std_ymd': str, 'hcode': str, 'id': str},
                  encoding="utf-8")
idlist = pd.read_csv(workspace + "grdlist_20251125.csv", dtype={'id': str}, encoding="utf-8")
rycode = pd.read_csv(data_path2 + "bccd_sec_code.csv", sep="|", encoding="utf-8")

def secuse(df):
    df['std_ymd'] = df['std_ymd'].astype('datetime64[ns]')
    df['weekday'] = df['std_ymd'].dt.day_name('ko_KR')
    df['std_ym'] = df['std_ymd'].astype(str).str[:7]
    df = pd.merge(idlist, df, "left", "id")
    df = pd.merge(df, rycode, how="left", on="ry_m_cd")
    group = round(df.groupby(['std_ym','weekday','id','ry_m_nm'], as_index=False)[['amt', 'cnt']].sum(numeric_only=True).sort_values(by='std_ym'))
    group.columns = ['기준연월','요일','격자번호','업종중분류','매출금액','매출건수']
    return group

kind = secuse(sec)
kind.to_excel(output + "업종_카드이용_2025년10월.xlsx", engine="openpyxl")
