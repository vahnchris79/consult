# 데이터 분석 컨설팅(도시공간계획과): 지도시각화

import pandas as pd
import geopandas as gpd

path = "D:/02_사업관리/2025년/데이터 분석 컨설팅/20250915_도시공간계획과/"

centergrid = gpd.read_file(path + "(2025-040) 데이터 분석 컨설팅 데이터.gpkg", layer="center50m_4326")
carduse = gpd.read_file(path + "(2025-040) 데이터 분석 컨설팅 데이터.gpkg", layer="2020-2024_carduse_center")

print(centergrid)
print(carduse)

