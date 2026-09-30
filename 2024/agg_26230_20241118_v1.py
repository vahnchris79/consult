
# 데이터 분석 컨설팅 2024.12.01
# 부산진구청 2024. 11.18 신청

# 부산광역시 청년인구 소득, 소비 집계
# 청년인구: 15세~44세 5세 단위
# 기간: 2019년~2023년
# 시군구별, 연도별

from pandasql import sqldf
import pandas as pd
import numpy as np
import glob

data_path = "D:/Project/datacheck/03_credit/01_upload/KCB/"
output_path = "D:/10_분석업무/05_구군요청/26230_부산진구/2024년/20241118/일자리정책과/집계결과/"
results = list()
values = list()

class Credit:

    def __init__(self, year, name):
        self._year = year
        self._name = name

    def merge_data(self):
        data_lists = glob.glob(data_path + f'busan_creditstatics_{self._year}/*_{self._name}_*.txt', recursive=True)
        for data in data_lists:
            return results.append(pd.read_csv(data, sep="|", dtype={'BS_YR_MON': str, 'AGE_CD': str}, encoding="utf-8"))
    
    def filter_data(df):
        df['BS_YR'] = df['BS_YR_MON'].str[:4]
        df = df.loc[df['AGE_CD'].str.contains('18|20|25|30|35|40')].copy()
        return df

    # 연도별 시구군별 집계
    def aggregate_data(self):
        Credit(year, name).merge_data()
        df = pd.concat(results, ignore_index=True)
        df = Credit.filter_data(df)
        if 'INC_10PERC' in df.columns:
            df['INC_SUM_MON'] = df['INC_SUM'] / 12
            group = round(df.groupby(['BS_YR', 'CT_CNTY_GU_NM', 'AGE_CD']).agg({'INC_SUM_MON': np.sum})).reset_index()
            group.columns = ['기준연월', '구군명', '연령대', '소득합계']
            group.to_csv(output_path + "연도별 구군별 청년인구별 소득집계.csv", sep="|", encoding="utf-8", index=False)
        if 'CD_10PERC' in df.columns:
            df['SUM_CD_USE_TOT_MON'] = df['SUM_CD_USE_TOT'] / 12
            group = round(df.groupby(['BS_YR', 'CT_CNTY_GU_NM', 'AGE_CD']).agg({'SUM_CD_USE_TOT_MON': np.sum})).reset_index()
            group.columns = ['기준연월', '구군명', '연령대', '소비합계']
            group.to_csv(output_path + "연도별 구군별 청년인구별 소비집계.csv", sep="|", encoding="utf-8", index=False)
    
if __name__ == "__main__":
    for year in ['2019', '2020', '2021', '2022', '2023']:
        for name in ['INC', 'CD']:
            print(f"{year}년 {name} 집계시작")
            Credit(year, name).aggregate_data()
            print(f"{year}년 {name} 집계완료")