import pandas as pd
import calendar

path = "D:/02_사업관리/2025년/데이터 구매 및 활용/12_적재확인/카드이용/"
output = "D:/02_사업관리/2025년/데이터 분석 컨설팅/20251117_금정구청/02_집계결과/"
sec = pd.read_csv(path + "bccd_d_sec_202308.csv", sep="|", dtype={'std_ymd': str, 'hcode': str, 'id': str},
                  encoding="utf-8")
code = pd.read_csv("D:/02_사업관리/코드자료/bccd_sec_code.csv", sep="|", encoding="utf-8")

results = []
for year in range(2023, 2026):
    for month in range(1, 13):
        std_ym = str(year) + "-" + str(f"{month:02d}")
        daycnt = calendar.monthrange(year, month)[1]
        results.append({"std_ym": std_ym, "daycnt": daycnt})
daycnt = pd.DataFrame(results).sort_values(['std_ym','daycnt'], ascending=False).reset_index(drop=True)

sec = sec[sec['hcode'].str.startswith('2641067')].copy()
print(sec.head(3))
sec['std_ymd'] = sec['std_ymd'].astype('datetime64[ns]')
sec['std_ym'] = sec['std_ymd'].astype(str).str[:7]
sec['weekday'] = sec['std_ymd'].dt.day_name('ko_KR')
sec['hname'] = "남산동"
sec = sec.merge(code, "left", "ry_m_cd")
sec['amt'] = sec['amt'].astype(float)
sec['cnt'] = sec['cnt'].astype(float)
group = sec.groupby(['std_ym','weekday','hname','ry_m_nm'], as_index=False)[['amt','cnt']].sum()
# group = group.merge(daycnt, "left", "std_ym")
# group['amt_mean'] = round(group['amt'] / group['daycnt'])
# group['cnt_mean'] = round(group['cnt'] / group['daycnt'])
sec = group[['std_ym','weekday','hname','ry_m_nm','amt','cnt']]
sec.columns = ['기준연월','요일','행정동명','업종중분류','매출금액','매출건수']
sec.to_csv(output + "월별 업종별 카드이용 현황_202308_v2.csv", encoding="utf-8", index=False)