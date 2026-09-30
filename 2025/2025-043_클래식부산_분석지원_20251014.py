
# 클래식부산 데이터 분석 컨설팅
# 부산콘서트홀 기준 반경 750m 이내 소비현황 비교분석
# 기준: 2024년 1월 ~ 8월, 대상: 2025년 1월 ~ 8월
# 성별, 연령(10세), 시간대(4시간 단위) 별 카드이용 금액 및 건수
# 연령그룹 = {01: 20세미만, 02~03: 20대, 04~05: 30대, 06~07: 40대,
#             08~09: 50대, 10~11: 60대, 12~13: 70대, 14~15: 80대이상}
# 시간그룹 = {00, 01, 02, 03: 심야2, 04, 05, 06, 07: 오전1, 08, 09, 10, 11: 오전2,
#             12, 13, 14, 15: 오후1, 16, 17, 18, 19: 오후2, 20, 21, 22, 23: 심야1}

import pandas as pd
import glob

data_lists = glob.glob("D:/02_사업관리/2025년/데이터 분석 컨설팅/20251014_클래식부산/data/*_p_*.csv", recursive=True)
grd_lists = pd.read_csv("grd_20251014.csv", dtype={'id': str}, encoding="utf-8")
output_path = "D:/02_사업관리/2025년/데이터 분석 컨설팅/20251014_클래식부산/02_집계결과/"
genders = []
ages = []
times = []

class Carduse:

    def __init__(self, data):
        self._data = data
    
    @staticmethod
    def label_ages(df):
        age_map = {
            '01': '20세미만', '02': '20대', '03': '20대', '04': '30대', '05': '30대', 
            '06': '40대', '07': '40대', '08': '50대', '09': '50대', '10': '60대', '11': '60대', 
            '12': '70대', '13': '70대', '14': '80대이상', '15': '80대이상'}
        df['연령'] = df['ages'].map(age_map)
        return df
    
    @staticmethod
    def label_times(df):
        times_map = {
            '심야2': ['00', '01', '02', '03'], '오전1': ['04', '05', '06', '07'], '오전2': ['08', '09', '10', '11'], 
            '오후1': ['12', '13', '14', '15'], '오후2': ['16', '17', '18', '19'], '심야1': ['20', '21', '22', '23']}
        def map_time_peroid(hour_code):
            for peroid, codes in times_map.items():
                if hour_code in codes:
                    return peroid
            return None
        df['시간'] = df['tme'].apply(map_time_peroid)

        return df

    def genages(self):
        if '_emd_' in self._data:
            df = pd.read_csv(self._data, sep="|", dtype={'std_ymd': str, 'hcode': str, 'id': str, 'ages': str}, encoding="utf-8")
            df['std_ymd'] = pd.to_datetime(df['std_ymd'])
            df['std_ym'] = df['std_ymd'].astype(str).str[:7]
            df = pd.merge(grd_lists, df, how="left", on="id").dropna()
            df = Carduse.label_ages(df)
            genders.append(df.groupby(['std_ym', 'id', 'gender']).agg({'amt': 'sum', 'cnt': 'sum'}).reset_index())
            ages.append(df.groupby(['std_ym', 'id', '연령']).agg({'amt': 'sum', 'cnt': 'sum'}).reset_index())
        pass
    
    def times(self):
        if '_tme_' in self._data:
            df = pd.read_csv(self._data, sep="|", dtype={'std_ymd': str, 'hcode': str,  'id': str, 'tme': str}, encoding="utf-8")
            df['std_ymd'] = pd.to_datetime(df['std_ymd'])
            df['std_ym'] = df['std_ymd'].astype(str).str[:7]
            df = pd.merge(grd_lists, df, how="left", on="id").dropna()
            df = Carduse.label_times(df)
            times.append(df.groupby(['std_ym', 'id', '시간']).agg({'amt': 'sum', 'cnt': 'sum'}).reset_index())
        pass


if __name__ == "__main__":
    for data in data_lists:
        Carduse(data).genages()
        Carduse(data).times()
    if genders:
        genders2 = pd.concat(genders, ignore_index=True)
        ages2 = pd.concat(ages, ignore_index=True)

        genders2.loc[genders2['gender']=='M', '성별'] = '남성'
        genders2.loc[genders2['gender']=='F', '성별'] = '여성'
        
        genders2.rename(columns={'std_ym': '기준연월', 'amt': '이용금액', 'cnt': '이용건수'}, inplace=True)
        ages2.rename(columns={'std_ym': '기준연월', 'amt': '이용금액', 'cnt': '이용건수'}, inplace=True)
        
        genders2 = genders2[['기준연월', 'id', '성별', '이용금액', '이용건수']]
        ages2 = ages2[['기준연월', 'id', '연령', '이용금액', '이용건수']]
        
        genders2.to_csv(output_path + "2025-000_gender_202401-2024-08.csv", sep="|", encoding="utf-8", index=False)
        ages2.to_csv(output_path + "2025-000_age_202401-2024-08.csv", sep="|", encoding="utf-8", index=False)

    if times:
        times2 = pd.concat(times, ignore_index=True)
        times2.rename(columns={'std_ym': '기준연월', 'amt': '이용금액', 'cnt': '이용건수'}, inplace=True)
        times2 = times2[['기준연월', 'id', '시간', '이용금액', '이용건수']]
        times2.to_csv(output_path + "2025-000_time_202401-2024-08.csv", sep="|", encoding="utf-8", index=False)