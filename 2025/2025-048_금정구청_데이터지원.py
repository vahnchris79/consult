
import pandas as pd

path = "D:/02_사업관리/2025년/데이터 분석 컨설팅/20251117_금정구청/02_집계결과/"
df = pd.read_excel(path + "비씨카드_부산광역시 남산동 데이터_251121.xlsx", engine="openpyxl")
df2 = pd.read_csv(path + "월별 업종별 카드이용.csv", sep=",", encoding="utf=8")
df['기준연월'] = df['기준연월'].astype(str)
df['기준연월'] = df['기준연월'].str[:7]
df = df.drop(columns=['업종중분류코드'])
df = df[['기준연월','요일','행정동명','업종중분류명','매출금액','매출건수']]

df2['매출금액'] = df2['매출금액'].astype(int)
df2['매출건수'] = df2['매출건수'].astype(int)
df2.columns = ['기준연월','요일','행정동명','업종중분류명','매출금액','매출건수']

result = pd.concat([df, df2], ignore_index=True)
result.to_csv(path + "월별 업종별 카드이용 현황.csv", sep=",", encoding="utf-8", index=False)