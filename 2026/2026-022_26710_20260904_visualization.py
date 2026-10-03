# -*- coding: utf-8 -*-
"""
기장군 생활인구(100m 격자)×CCTV 수급 분석 + 브이월드 시각화
==================================================================
[판정 기준 — 절대값]
  격자 지표 = 명당인구 = 생활인구 / (반경 내 CCTV 수)   # 클수록 CCTV 부족
  임계값(THRESHOLD) = 각 연도별 100m 격자 '연평균 명당인구'의 평균 (자동 산출)
  판정:  명당인구 ≥ 임계값 × 부족_배수  → 부족
         명당인구 ≤ 임계값 × 많음_배수  → 많음
         그 사이                        → 적당
         반경 내 CCTV 0개 + 인구 존재    → 부족 (명당인구 = 무한대)
         연평균 생활인구 < MIN_POP       → 해당없음(분석 제외)

  ※ 아래 '판정 기준 변수'는 요청부서 검토 후 값만 바꾸면 재분석됩니다.

필요 패키지: pip install geopandas folium pandas numpy branca
브이월드 인증키: https://www.vworld.kr 에서 발급 후 VWORLD_KEY 입력
"""
import os
from dotenv import load_dotenv
import numpy as np
import pandas as pd
import geopandas as gpd
import folium
from folium.plugins import HeatMap
from branca.element import MacroElement
from jinja2 import Template

# ============================================================
# ★ 판정 기준 변수 (요청부서 검토 후 여기만 조정) ★
# ============================================================
RADIUS_M         = 200        # CCTV 커버리지 반경(m). 명목 감시거리 15m → 방범 존재감 기준 확대
THRESHOLD_MODE   = "auto"     # "auto": 연도별 격자 연평균 명당인구 자동 / "manual": 아래 값 사용
MANUAL_THRESHOLD = {}         # 예: {2022: 1500, 2023: 1600}  (mode="manual"일 때, 명/대)
부족_배수         = 1.0        # 명당인구 ≥ 임계값 × 부족_배수 → 부족  (1.0=연평균 그대로, ↑일수록 엄격)
많음_배수         = 0.5        # 명당인구 ≤ 임계값 × 많음_배수 → 많음
MIN_POP          = 1          # 연평균 생활인구 이 값 미만 격자는 '해당없음'으로 제외

# ============================================================
# 입력 (파일 구조에 맞춘 기본값)
# ============================================================
GPKG        = "2026-022_26710_CCTV.gpkg"
POP_LAYERS  = {2022: "100m_hjdong_pop_2022", 2023: "100m_hjdong_pop_2023",
               2024: "100m_hjdong_pop_2024", 2025: "100m_hjdong_pop_2025",
               2026: "100m_hjdong_pop_2026"}   # ※ 현재 5개 레이어 값이 동일(2022) → 원본 확인 권장
CCTV_LAYER  = "CCTVINFO_26170"
EMD_LAYER   = "EMD26710"
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "env"))
VWORLD_KEY  = os.environ["VWORLD_API_KEY"]

COL_GID, COL_TCLS, COL_POP, COL_DONG = "100MGID", "시간분류", "생활인구", "행정동명"
TIME_ORDER  = ["심야2", "오전1", "오전2", "오후1", "오후2", "심야1"]
MAP_YEAR    = 2022            # 지도로 그릴 연도
OUTPUT_PATH     = r"03_집계결과\\PNG\\"
os.makedirs(OUTPUT_PATH, exist_ok=True)

# ============================================================
# 1. 로드 (연도는 레이어명 기준. 데이터의 기준연도 컬럼은 오기라 미사용)
# ============================================================
frames = []
for yr, ly in POP_LAYERS.items():
    g = gpd.read_file(GPKG, layer=ly); g["연도"] = yr; frames.append(g)
pop  = gpd.GeoDataFrame(pd.concat(frames, ignore_index=True),
                        geometry="geometry", crs=frames[0].crs)
cctv = gpd.read_file(GPKG, layer=CCTV_LAYER)
emd  = gpd.read_file(GPKG, layer=EMD_LAYER)

geo = pop.drop_duplicates(COL_GID)[[COL_GID, COL_DONG, "geometry"]].reset_index(drop=True)
geo = gpd.GeoDataFrame(geo, geometry="geometry", crs=pop.crs)

# ============================================================
# 2. CCTV 커버리지 (격자 중심 반경 RADIUS_M 내 CCTV 수) — 이미 EPSG:5179(m)
# ============================================================
buf = geo.copy(); buf["geometry"] = geo.geometry.centroid.buffer(RADIUS_M)
j = gpd.sjoin(cctv[["geometry"]], buf[[COL_GID, "geometry"]], predicate="within")
covmap = j.groupby(COL_GID).size().reindex(geo[COL_GID]).fillna(0)
geo["cctv_cov"] = geo[COL_GID].map(covmap)

def 명당인구(popval, cov):
    cov = np.asarray(cov, float)
    return np.where(cov > 0, np.asarray(popval, float) / np.where(cov == 0, np.nan, cov), np.inf)

def 판정(r, thr):
    if np.isinf(r):            return "부족"        # 인구 있는데 CCTV 0
    if np.isnan(r):            return "해당없음"
    if r >= thr * 부족_배수:    return "부족"
    if r <= thr * 많음_배수:    return "많음"
    return "적당"

# ============================================================
# 3. 연도별 임계값 = 격자 연평균 명당인구의 평균
# ============================================================
연평균 = pop.groupby(["연도", COL_GID])[COL_POP].mean().reset_index(name="연평균생활인구")
연평균["cctv_cov"] = 연평균[COL_GID].map(covmap).fillna(0)
연평균["명당인구"] = 명당인구(연평균["연평균생활인구"], 연평균["cctv_cov"])
연평균.loc[연평균["연평균생활인구"] < MIN_POP, "명당인구"] = np.nan

thr_by_year = {}
for yr, d in 연평균.groupby("연도"):
    if THRESHOLD_MODE == "manual" and yr in MANUAL_THRESHOLD:
        thr_by_year[yr] = float(MANUAL_THRESHOLD[yr])
    else:
        thr_by_year[yr] = float(d.loc[np.isfinite(d["명당인구"]), "명당인구"].mean())
pd.DataFrame({"연도": list(thr_by_year), "임계값_명당인구": list(thr_by_year.values())}
    ).to_csv(f"{OUTPUT_PATH}/임계값_연도별.csv", index=False, encoding="utf-8-sig")
print("연도별 임계값(명/대):", {k: round(v, 1) for k, v in thr_by_year.items()})

# ============================================================
# 4. 시간분류 × 격자 × 연도 판정
# ============================================================
agg = pop.groupby(["연도", COL_GID, COL_TCLS])[COL_POP].mean().reset_index()
agg["cctv_cov"] = agg[COL_GID].map(covmap).fillna(0)
agg["명당인구"] = 명당인구(agg[COL_POP], agg["cctv_cov"])
연pop = 연평균.set_index(["연도", COL_GID])["연평균생활인구"]
agg["연평균생활인구"] = agg.set_index(["연도", COL_GID]).index.map(연pop)
agg.loc[agg["연평균생활인구"] < MIN_POP, "명당인구"] = np.nan
agg["임계값"] = agg["연도"].map(thr_by_year)
agg["판정"] = [판정(r, t) for r, t in zip(agg["명당인구"], agg["임계값"])]
agg[COL_DONG] = agg[COL_GID].map(geo.set_index(COL_GID)[COL_DONG])
agg.to_csv(f"{OUTPUT_PATH}/격자별_수급분석_전체.csv", index=False, encoding="utf-8-sig")

# 요약 (MAP_YEAR)
a = agg[agg["연도"] == MAP_YEAR]
summ = a.groupby([COL_TCLS, "판정"]).size().unstack(fill_value=0).reindex(TIME_ORDER)
for c in ["부족", "적당", "많음", "해당없음"]:
    summ[c] = summ.get(c, 0)
summ = summ[["부족", "적당", "많음", "해당없음"]]
summ["부족비율%"] = (summ["부족"] / summ[["부족", "적당", "많음"]].sum(axis=1) * 100).round(1)
summ.to_csv(f"{OUTPUT_PATH}/수급요약_시간분류별.csv", encoding="utf-8-sig")
print(summ.to_string())

# ============================================================
# 5. 브이월드 지도 (시간분류별 HTML)
# ============================================================
geo_wgs, cctv_wgs, emd_wgs = geo.to_crs(4326), cctv.to_crs(4326), emd.to_crs(4326)
cent = geo.copy(); cent["geometry"] = geo.geometry.centroid; cent = cent.to_crs(4326)
cent["lat"], cent["lon"] = cent.geometry.y, cent.geometry.x
center = [cent["lat"].mean(), cent["lon"].mean()]
COLOR = {"부족": "#d73027", "적당": "#fee08b", "많음": "#1a9850", "해당없음": "#dddddd"}
VW = [("Base", "브이월드 기본", "png"), ("gray", "회색", "png"),
      ("midnight", "야간", "png"), ("Satellite", "위성", "jpeg")]

for t in TIME_ORDER:
    sub = a[a[COL_TCLS] == t].set_index(COL_GID)
    m = folium.Map(location=center, zoom_start=12, tiles="OpenStreetMap", control_scale=True)
    for layer, name, ext in VW:
        folium.TileLayer(
            f"https://api.vworld.kr/req/wmts/1.0.0/{VWORLD_KEY}/{layer}/{{z}}/{{y}}/{{x}}.{ext}",
            attr="© VWorld", name=name, overlay=False).add_to(m)
    heat = list(zip(cent["lat"], cent["lon"], cent[COL_GID].map(sub[COL_POP]).fillna(0)))
    HeatMap(heat, name="생활인구 히트맵", radius=16, blur=13, min_opacity=0.3).add_to(m)
    g = geo_wgs.copy()
    g["판정"] = g[COL_GID].map(sub["판정"])
    g["생활인구"] = g[COL_GID].map(sub[COL_POP]).round(0)
    g["CCTV수"] = g[COL_GID].map(sub["cctv_cov"])
    g["명당인구"] = g[COL_GID].map(sub["명당인구"]).replace([np.inf], -1).round(0)
    g = g.dropna(subset=["판정"])
    folium.GeoJson(g, name="수급 판정 격자",
        style_function=lambda x: {"fillColor": COLOR.get(x["properties"]["판정"], "#ccc"),
                                  "color": "none", "fillOpacity": 0.55},
        tooltip=folium.GeoJsonTooltip(
            fields=[COL_DONG, "생활인구", "CCTV수", "명당인구", "판정"],
            aliases=["행정동", "생활인구", f"CCTV(반경{RADIUS_M}m)", "명당인구(-1=CCTV0)", "판정"])
    ).add_to(m)
    folium.GeoJson(emd_wgs, name="읍면동 경계",
        style_function=lambda x: {"fillOpacity": 0, "color": "#333", "weight": 1.5}).add_to(m)
    fg = folium.FeatureGroup(name="CCTV 위치")
    for pt in cctv_wgs.geometry:
        folium.CircleMarker([pt.y, pt.x], radius=2, color="#08519c",
                            fill=True, fill_opacity=0.85, weight=0).add_to(fg)
    fg.add_to(m)
    thr = thr_by_year[MAP_YEAR]
    leg = MacroElement(); leg._template = Template(f"""{{% macro html(this,kwargs) %}}
<div style="position:fixed;bottom:25px;left:25px;z-index:9999;background:#fff;padding:10px 14px;
 border-radius:6px;font-size:13px;box-shadow:0 1px 4px rgba(0,0,0,.3)">
<b>수급 판정 ({t}) · 임계값 {thr:,.0f}명/대</b><br>
<span style="color:#d73027">■</span> 부족&nbsp;<span style="color:#fee08b">■</span> 적당&nbsp;
<span style="color:#1a9850">■</span> 많음<br><span style="color:#08519c">●</span> CCTV</div>{{% endmacro %}}""")
    m.get_root().add_child(leg)
    folium.LayerControl(collapsed=False).add_to(m)
    m.save(f"{OUTPUT_PATH}/CCTV분석_{t}.html")
    print("saved", t)
print("완료")
