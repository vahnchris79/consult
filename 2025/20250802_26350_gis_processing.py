# 침수예상지역 추출 스크림트

from qgis.analysis import QgsRasterCalculatorEntry, QgsRasterCalculator
from qgis.core import QgsProject, QgsVectorLayer
import processing
import os

def extract_flood_area_simple(dem_name, threshold, river_flood_gpkg_path, river_layer_name, output_dir):
    
    # 1. DEM 레이어
    dem_layer = QgsProject.instance().mapLayersByName(dem_name)[0]
    
    # 2. Raster 계산 설정
    entry = QgsRasterCalculatorEntry()
    entry.ref = 'dem@1'
    entry.raster = dem_layer
    entry.bandNumber = 1
    
    extent = dem_layer.extent()
    width = dem_layer.width()
    height = dem_layer.height()
    
    # 3. DEM 기반 침수 마스크 계산
    dem_mask_path = os.path.join(output_dir, 'flood_dem_mask.tif')
    QgsRasterCalculator(
        f'("{entry.ref}" < {threshold}) * 1',
        dem_mask_path, 'GTiff', extent, width, height, [entry]
    ).processCalculation()
    
    # 4. 마스크 -> 벡터 변환
    dem_vec_path = os.path.join(output_dir, 'flood_dem_mask_vector.shp')
    processing.run("gdal:polygonize", {
        'INPUT': dem_mask_path,
        'BAND': 1,
        'FIELD': 'value',
        'EIGHT_CONNECTEDNESS': False,
        'EXTRA': '',
        'OURPUT': dem_vec_path
    })
    dem_vector = QgsVectorLayer(dem_vec_path, 'flood_dem_vector', 'ogr')
    dem_vector.setSubsetString('"value" = 1')
    QgsProject.instance().addMapLayer(dem_vector)
    
    # 5. 하천범람지도 불러오기
    river_layer = QgsVectorLayer(f"{river_flood_gpkg_path}|layername={river_layer_name}", 'river_flood', 'ogr')
    QgsProject.instance().addMapLayer(river_layer)
    
    # 6. 병합
    merged_output = os.path.join(output_dir, 'flood_area_combined.shp')
    processing.run("native:mergevectorlayers", {
        'LAYERS': [dem_vector, river_layer],
        'CRS': river_layer.crs(),
        'OUTPUT': merged_output
    })
    
    merged_layer = QgsVectorLayer(merged_output, 'flood_area_combined', 'ogr')
    QgsProject.instance().addMapLayer(merged_layer)
    
    print("DEM + 하천범람 통합 침수예상지역 생성 완료: ", merge_output)

extract_flood_area_simple(
    dem_name='dem_haewondae',
    threshold=10,
    river_flood_gpkg_path = 'D:/QGIS_Works/Data/26350_20250710_analysis.gpkg',
    river_layer_name = 'flood_zone',
    output_dir = 'D:/QGIS_Works/Output'
)