
import pandas as pd
import numpy as np

path = "D:/02_사업관리/2025년/데이터 분석 컨설팅/20251121_부산진구청/03_집계결과/"
df1 = pd.read_excel(path + "비씨카드_부산광역시 서면권 세대별 테마거리 데이터_251124.xlsx",
                    sheet_name="데이터", engine="openpyxl")
df2 = pd.read_csv(path + "월별_요일별_격자별_업종_매출현황.csv", encoding="utf-8")

df1['기준연월2'] = df1['기준연월'].astype(str).str[:7]
group1 = df1.groupby(['기준연월2','요일']).agg({'매출금액': np.sum, '매출건수': np.sum}).reset_index()
group1.columns = ['기준연월','요일','매출금액','매출건수']
group2 = df2.groupby(['기준연월','요일']).agg({'매출금액': np.sum, '매출건수': np.sum}).reset_index()

group = pd.concat([group1, group2], ignore_index=True)
group.to_excel(path + "월별 요일별_매출현황.xlsx", engine="openpyxl")