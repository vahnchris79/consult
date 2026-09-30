

# 도시공간계획과 데이터 분석 컨설팅
# 7개 중심(서면, 중앙, 해운대, 사상, 하단, 덕천, 동래)에 대한 특성분석
# 최근 5년간 주중, 주말, 시간대별 유동인구 특성, 카드사용 변화분석
# 7개 중심지 통행특성 분석(버스, 지하철, 자가용, 도보)

# 최근 5년간 주중, 주말 시간대별 유동인구 특성, 카드사용 변화분석

import pandas as pd
import glob
import sqlite3

pop_map_lists = []
pop_chart_lists = []
crd_map_lists = []
crd_chart_lists = []

path = "D:/02_사업관리/2025년/데이터 분석 컨설팅/20250915_도시공간계획과/03_집계결과/"
csv_map_path = glob.glob(path + "지도시각화/*.csv")
csv_chart_path = glob.glob(path + "차트시각화/*.csv")
con = sqlite3.connect(path + "2025_040_도시공간계획과_20250915.db")
cursor = con.cursor()
cursor.execute("""
    CREATE TABLE IF NOT EXISTS livingpop_map_table ( 
               std_ym VARCHAR, weeknm VARCHAR, times VARCHAR, 
               id VARCHAR, x FLOAT(3, 5), y FLOAT(3, 5), name VARCHAR,
               pop DOUBLE)""")
cursor.execute("""
    CREATE TABLE IF NOT EXISTS livingpop_chart_table ( 
               std_ym VARCHAR, weeknm VARCHAR, times VARCHAR, name VARCHAR,
               pop DOUBLE)""")
cursor.execute("""
    CREATE TABLE IF NOT EXISTS carduse_map_table ( 
               std_ym VARCHAR, weeknm VARCHAR, times VARCHAR, 
               id VARCHAR, x FLOAT(3, 5), y FLOAT(3, 5), name VARCHAR,
               amt DOUBLE, cnt DOUBLE)""")
cursor.execute("""
    CREATE TABLE IF NOT EXISTS carduse_chart_table ( 
               std_ym VARCHAR, weeknm VARCHAR, times VARCHAR, name VARCHAR,
               amt DOUBLE, cnt DOUBLE)""")

con.commit()

print("시각화용 데이터 병합 시작")

for data in csv_path:
    if 'livingpop_map' in data:
        pop_map_lists.append(pd.read_csv(data, encoding="utf-8"))
        res2 = pd.concat(pop_map_lists, ignore_index=True)
        res2.to_sql("livingpop_map_table", con=con, if_exists='replace', index=False)
    elif 'livingpop_chart' in data:
        pop_chart_lists.append(pd.read_csv(data, encoding="utf-8"))
        res2 = pd.concat(pop_chart_lists, ignore_index=True)
        res2.to_sql("livingpop_chart_table", con=con, if_exists='replace', index=False)
    elif 'carduse_map' in data:
        crd_map_lists.append(pd.read_csv(data, encoding="utf-8"))
        res2 = pd.concat(crd_map_lists, ignore_index=True)
        res2.to_sql("carduse_map_table", con=con, if_exists='replace', index=False)
    elif 'carduse_chart' in data:
        crd_chart_lists.append(pd.read_csv(data, encoding="utf-8"))
        res2 = pd.concat(crd_chart_lists, ignore_index=True)
        res2.to_sql("carduse_chart_table", con=con, if_exists='replace', index=False)

con.close()
print("시각화용 데이터 병합 완료")