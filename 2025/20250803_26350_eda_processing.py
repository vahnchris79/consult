
# 행정동별 재난대피소당 재난취약계층 수용인원 산출
import pandas as pd
import numpy as np
import geopandas as gpd

shelter = gpd.read_file("05_Result/(2025-028) 데이터 분석 컨설팅 분석자료.gpkg", layer="재난대피소_읍면동추가")
#print(shelter.head())
disaster = gpd.read_file("05_Result/(2025-028) 데이터 분석 컨설팅 분석자료.gpkg", layer="재난취약계층현황_읍면동추가")
#print(disaster.head())

# 행정동별 재난대피소 집계, 행정동별 재난취약계층 집계
shelter_cnt = shelter.groupby(['EMD_KOR_NM'])['시설유형'].count().reset_index(name='대피소수')
disaster_cnt = disaster.groupby(['EMD_KOR_NM'])['구분'].count().reset_index(name='취약계층현황')
#print(shelter_cnt)
#print(disaster_cnt)

# 재난대피소 당 수용인원
per_person = shelter_cnt.merge(disaster_cnt, 'left', on='EMD_KOR_NM')
per_person['대피소당수용인원'] = round(per_person['취약계층현황'] / per_person['대피소수'])
print(per_person)