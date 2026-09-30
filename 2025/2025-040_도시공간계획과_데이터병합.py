
import geopandas as gpd

path = "D:/02_사업관리/2025년/데이터 분석 컨설팅/20250915_도시공간계획과/03_집계결과/카드이용/"
path2 = "D:/02_사업관리/2025년/데이터 분석 컨설팅/20250915_도시공간계획과/"
card = gpd.read_file(path + "2020-2024_carduse_center.csv", encoding="utf-8", dtype={'id': str})
card.to_file(path2 + "(2025-040) 데이터 분석 컨설팅 데이터.gpkg", layer="2020-2024_carduse_center", encoding="utf-8")
