# 파일 경로와 레이어 이름
gpkg_path = "D:/02_사업관리/2025년/데이터 분석 컨설팅/20250808_기장군청/(2025-034) 데이터 분석 컨설팅 데이터.gpkg"
layer_name = "2024y_id_times_pop"  # gpkg 안에 저장된 레이어 이름

# 레이어 불러오기
layer = QgsVectorLayer(f"{gpkg_path}|layername={layer_name}", layer_name, "ogr")

# 프로젝트에 추가
if layer.isValid():
    QgsProject.instance().addMapLayer(layer)
    print("레이어가 성공적으로 불러와졌습니다.")
else:
    print("레이어를 불러올 수 없습니다.")

layer = iface.activeLayer()
field_name = "pop2"          # 집계할 필드명
condition = "\"times2\" = '심야2'"    # 필터 조건(QGIS 표현식)

# 집계 파라미터(조건식 전달)
params = QgsAggregateCalculator.AggregateParameters()
params.filter = condition

# 최대값
max_val, ok_max = layer.aggregate(QgsAggregateCalculator.Max, field_name, params)
# 최소값
min_val, ok_min = layer.aggregate(QgsAggregateCalculator.Min, field_name, params)

if ok_max and ok_min:
    print(f"조건({condition})을 만족하는 '{field_name}'의 최대값: {max_val}, 최소값: {min_val}")
else:
    print("집계에 실패했습니다. 필드명/조건식을 확인하세요.")
