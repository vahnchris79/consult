# -*- coding: utf-8 -*-
"""
기장군 생활인구(100m 격자)×방범용 CCTV 수급 분석 + 브이월드 배경 A1 PNG 시각화
==========================================================================
[산출물]  (OUTPUT_PATH/PNG_A1/)
  ① 01_CCTV설치현황_{연도}.png        : 연도 × 100m 격자 생활인구 히트맵 × 행정동 경계 × CCTV 위치 (5장)
  ② 02_생활인구_색온도_{연도}.png      : 행정동별 생활인구 색온도(choropleth) 지도 (5장)
  ③ 03_행정동별_인구분포_{연도}.png : 행정동별 인구밀도 지도 + 행정동 표 + 5개년 추이 (A1, 연도별 5장)
  ④ 04_행정동별_생활인구_{연도}.png : 3_행정구역별 인구분포_Wide.csv 기준 연도별 행정동 생활인구 지도 (A1, 5장)
  - 모든 PNG는 A1(594×841mm) 용지에 1:1로 들어가는 크기(기본 300dpi → 7016×9933px)로 저장
  - 2026년은 1~7월 자료만 사용 → 제목·범례에 '2026년(1~7월)'로 표기 (연평균 = 기간 평균)

[판정 기준 — 절대값]  (기존 로직 유지)
  격자 지표 = 명당인구 = (격자 중심 반경 R 내 격자들의 생활인구 합) / (같은 반경 R 내 CCTV 수)
             → 분자·분모의 공간범위를 동일한 원(반경 R)으로 맞춤. 클수록 CCTV 부족
             (POP_SCOPE="cell"로 바꾸면 기존 방식: 해당 격자 생활인구 / 반경 내 CCTV 수)
  임계값 = 각 연도별 100m 격자 '연평균 명당인구'의 평균 (자동 산출)
  판정: 명당인구 ≥ 임계값×부족_배수 → 부족 / ≤ 임계값×많음_배수 → 많음 / 그 사이 → 적당
        반경 내 CCTV 0개 + 인구 존재 → 부족 / 연평균 생활인구 < MIN_POP → 해당없음

필요 패키지: pip install geopandas pandas numpy matplotlib requests pillow scipy
브이월드 인증키: https://www.vworld.kr 에서 발급 (타일 요청 시 등록 도메인을 Referer로 전송)
"""
import os
import re
import math
import warnings
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd
import geopandas as gpd
import requests
from PIL import Image
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from matplotlib import font_manager
from matplotlib.colors import BoundaryNorm, Normalize, ListedColormap
from matplotlib.cm import ScalarMappable
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Rectangle

warnings.filterwarnings("ignore", category=UserWarning)
Image.MAX_IMAGE_PIXELS = None

# ============================================================
# ★ 판정 기준 변수 (요청부서 검토 후 여기만 조정) ★
# ============================================================
RADIUS_M         = 200        # CCTV 커버리지·생활인구 집계 공통 반경(m)
POP_SCOPE        = "radius"   # "radius": 분자=반경 내 격자 생활인구 합(권장) / "cell": 분자=해당 격자 생활인구
THRESHOLD_MODE   = "auto"     # "auto" / "manual"
MANUAL_THRESHOLD = {}         # 예: {2022: 1500, 2023: 1600}
부족_배수         = 1.0
많음_배수         = 0.5
MIN_POP          = 1

# ============================================================
# 입력
# ============================================================
GPKG        = "2026-022_26710_CCTV.gpkg"
YEARS       = [2022, 2023, 2024, 2025, 2026]
POP_LAYERS  = {y: f"100m_hjdong_pop_{y}" for y in YEARS}
CCTV_XLSX   = "CCTV 위치정보기장군_중복제거_혜안변환.xlsx"   # CCTV 설치현황(위도·경도·설치년월). 파일이 있으면 이것을 사용
CCTV_LAYER  = "CCTVINFO_26170"    # CCTV_XLSX 가 없을 때 GPKG 레이어 사용 (※ 기장군 코드는 26710 — 오기 여부 확인)
EMD_LAYER   = "EMD26710"
VWORLD_KEY  = "A991416E-F2EE-3959-99F3-C71FFC190B72"
VWORLD_REFERER = ""               # 인증키 발급 시 등록한 서비스 URL (예: "http://localhost"). 비워두면 미전송

COL_GID, COL_TCLS, COL_POP, COL_DONG = "100MGID", "시간분류", "생활인구", "행정동명"
COL_HOUR    = "특정시간"          # 00H~23H (시간분류 1개 = 4개 시각)
GRID_AGG_MODE = "legacy"         # "legacy": 이전 결과(보고서·PDF)와 같은 방식 — 격자의 모든 행 평균, 행정동은 격자의 첫 행정동
                                 # "split" : 행정동 경계 격자를 행정동별로 나눠 합산(경계 격자 인구 과소 보정)
# ※ 원자료 구조: 격자 × 시각(24) 1행. 행정동 경계에 걸친 격자는 행정동별로 2행 → 격자 값은 행정동 합산 후 평균
TIME_ORDER  = ["심야2", "오전1", "오전2", "오후1", "오후2", "심야1"]
YEAR_LABEL  = {y: f"{y}년" for y in YEARS} | {2026: "2026년(1~7월)"}

# --- CCTV 속성 (공공데이터 CCTV 표준데이터 컬럼 기준, 없으면 자동으로 무시) ---
COL_CCTV_PURPOSE = "설치목적구분"   # 방범용만 추출
PURPOSE_KEYWORD  = "방범"          # None 이면 전체 CCTV 사용
COL_CCTV_INSTALL = "설치년월"       # 설치년월(2008.11~2025.9) 기준 연도 말 누적 CCTV 사용 ("설치연월"도 자동 인식)
                                   #   None 으로 두면 설치현황 전체를 5개년에 동일 적용
CCTV_REF_DATE    = "2025.9"        # 설치이력 마지막 시점 → 2026년은 이 시점 기준 CCTV로 표기
CLIP_CCTV_TO_EMD = True            # 기장군 경계 밖 CCTV 제외
CCTV_YEARS       = [2022, 2023, 2024, 2025, 2026]   # 설치현황·1대당 생활인구 집계 연도
CCTV_YEAR_MAP    = {2026: 2025}      # 설치이력이 2025.9까지 → 2026년 생활인구는 2025년(9월) CCTV와 비교
CCTV_BASIS       = {2022: "2022년 12월말", 2023: "2023년 12월말", 2024: "2024년 12월말", 2025: "2025년 9월", 2026: "2025년 9월"}  # 표기용
POP_PERIOD       = {2022: "2022년 1~12월", 2023: "2023년 1~12월", 2024: "2024년 1~12월", 2025: "2025년 1~12월", 2026: "2026년 1~7월"}
COL_CCTV_CAM     = "카메라대수"      # 한 지점 카메라 수(없으면 지점당 1대로 계산)

# --- 생활인구(② 색온도 지도) : 일별 행정동 유입지별 시간대 생활인구 ---
#   {연도: CSV 경로 또는 GPKG 레이어명}. 비워두면 100m 격자 생활인구를 행정동 단위로 합산해 사용
INFLOW_SOURCES = {}   # 예: {2022: "유입지별_2022.csv", ..., 2026: "inflow_hjdong_2026"}
# 유입지별 생활인구를 행정동·연도별 연평균으로 미리 집계한 표(가로형: 기준연도 | 기장읍 | 일광읍 ...). 있으면 이것을 우선 사용
INFLOW_WIDE_CSV = "3_행정구역별 인구분포_Wide.csv"
POP_MONTHS      = {2026: 7}        # 연도별 자료 개월 수(없으면 12). 2026년은 1~7월
ANNUALIZE_PARTIAL = False          # True: 부분연도 값을 × 12/개월 로 연환산 / False: 제공 자료 값을 그대로 사용
INFLOW_COL_DONG, INFLOW_COL_POP = "행정동명", "생활인구"
INFLOW_COL_DATE, INFLOW_COL_TIME = "기준일ID", "시간대구분"
INFLOW_COL_ORIGIN    = "유입지"     # 유입지(출발지) 컬럼
INFLOW_EXTERNAL_ONLY = False        # True: 같은 행정동 내부 유입 제외(순수 외부 유입만)

# ============================================================
# ★ 출력(A1 이미지) 설정 ★
# ============================================================
OUTPUT_PATH  = "03_집계결과"
PNG_DIR      = os.path.join(OUTPUT_PATH, "PNG_A1")
TILE_CACHE   = os.path.join(OUTPUT_PATH, "_vworld_tile_cache")
PAPER_MM     = (594, 841)       # A1 (가로, 세로) mm
DPI          = 300              # 300: 7016×9933px (인쇄용) / 200: 4677×6622px (가벼움)
ORIENT       = "auto"           # "portrait" / "landscape" / "auto"(기장군 경계 형태에 맞춤)
VW_LAYER_CCTV  = ("Base", "png")   # ① 배경: Base / gray / midnight / Satellite(jpeg) / white
VW_LAYER_CHORO = ("gray", "png")   # ②③ 배경
VW_FALLBACK    = [("Base", "png"), ("white", "png")]   # 배경 레이어 실패 시 차례로 대체
BASEMAP_ALPHA  = 1.0
MAX_TILES      = 3000             # 한 장당 타일 상한 (초과 시 줌 자동 하향)
TILE_WORKERS   = 8
HEAT_STYLE     = "grid"           # "grid": 100m 격자 채색 / "kde": 부드러운 히트맵
HEAT_ALPHA     = 0.70
HEAT_CMAP      = "YlOrRd"
TEMP_CMAP      = "RdYlBu_r"       # 색온도(차가움=파랑 → 뜨거움=빨강)
DENS_CMAP      = "YlGnBu"
CCTV_COLOR, CCTV_NEW_COLOR = "#0b3d91", "#00c2ff"

os.makedirs(PNG_DIR, exist_ok=True)
os.makedirs(TILE_CACHE, exist_ok=True)

# ============================================================
# 0. 공통 유틸
# ============================================================
def set_korean_font():
    cands = ["Malgun Gothic", "맑은 고딕", "NanumGothic", "NanumBarunGothic", "AppleGothic",
             "Noto Sans CJK KR", "Noto Sans KR", "Noto Sans CJK JP"]
    have = {f.name for f in font_manager.fontManager.ttflist}
    for c in cands:
        if c in have:
            plt.rcParams["font.family"] = c
            break
    else:
        print("[경고] 한글 폰트를 찾지 못했습니다. 글자가 깨지면 맑은고딕/나눔고딕을 설치하세요.")
    plt.rcParams["axes.unicode_minus"] = False

set_korean_font()
HALO = [pe.withStroke(linewidth=6, foreground="white")]

def paper_inches(orient):
    w, h = PAPER_MM
    if orient == "landscape":
        w, h = h, w
    return w / 25.4, h / 25.4

def norm_name(s):
    return str(s).strip().split()[-1] if pd.notna(s) and str(s).strip() else s

def fmt(v):
    return "-" if v is None or not np.isfinite(v) else f"{v:,.0f}"

# ---------------- 브이월드 WMTS 타일 ----------------
ORIGIN = 20037508.342789244
_sess = requests.Session()
_sess.headers.update({"User-Agent": "Mozilla/5.0 (GijangCCTV-analysis)"})
if VWORLD_REFERER:
    _sess.headers.update({"Referer": VWORLD_REFERER})

_TILE_ERR = {}      # 레이어별 첫 실패 원인(진단용)

def _tile(layer, ext, z, x, y):
    p = os.path.join(TILE_CACHE, layer, str(z), str(y), f"{x}.{ext}")
    if os.path.exists(p) and os.path.getsize(p) > 0:
        try:
            return Image.open(p).convert("RGB")
        except Exception:
            os.remove(p)                                   # 깨진 캐시는 지우고 다시 받음
    url = f"https://api.vworld.kr/req/wmts/1.0.0/{VWORLD_KEY}/{layer}/{z}/{y}/{x}.{ext}"
    for _ in range(3):
        try:
            r = _sess.get(url, timeout=20)
            if r.status_code == 200:
                try:                                       # Content-Type 대신 실제 이미지인지로 판정
                    im = Image.open(BytesIO(r.content)).convert("RGB")
                except Exception:
                    _TILE_ERR.setdefault(layer, f"HTTP 200, 이미지 아님 (Content-Type={r.headers.get('Content-Type')}) "
                                                f"응답: {r.text[:150]!r}")
                    return None
                os.makedirs(os.path.dirname(p), exist_ok=True)
                with open(p, "wb") as f:
                    f.write(r.content)
                return im
            _TILE_ERR.setdefault(layer, f"HTTP {r.status_code} (Content-Type={r.headers.get('Content-Type')}) "
                                        f"응답: {r.text[:150]!r}")
            if r.status_code in (400, 401, 403, 404):
                return None                                # 재시도해도 같은 결과
        except requests.RequestException as e:
            _TILE_ERR.setdefault(layer, f"요청 오류: {e}")
    return None

def pick_zoom(extent, px_width):
    x0, x1, y0, y1 = extent
    res = (x1 - x0) / px_width
    z = int(np.clip(math.ceil(math.log2(2 * ORIGIN / 256 / res)), 6, 18))
    while z > 6:
        ts = 2 * ORIGIN / 2 ** z
        n = (int((x1 - x0) / ts) + 2) * (int((y1 - y0) / ts) + 2)
        if n <= MAX_TILES:
            break
        z -= 1
    return z

def add_vworld(ax, extent, px_width, layer_ext, alpha=BASEMAP_ALPHA, _fallback=None):
    """extent=(xmin,xmax,ymin,ymax) EPSG:3857. 실패 시 False 반환(흰 배경)"""
    layer, ext = layer_ext
    z = pick_zoom(extent, px_width)
    ts = 2 * ORIGIN / 2 ** z
    x0, x1, y0, y1 = extent
    tx0, tx1 = int((x0 + ORIGIN) // ts), int((x1 + ORIGIN) // ts)
    ty0, ty1 = int((ORIGIN - y1) // ts), int((ORIGIN - y0) // ts)
    jobs = [(tx, ty) for ty in range(ty0, ty1 + 1) for tx in range(tx0, tx1 + 1)]
    print(f"  · 브이월드 {layer} z={z} 타일 {len(jobs)}개")
    with ThreadPoolExecutor(TILE_WORKERS) as ex:
        tiles = list(ex.map(lambda t: _tile(layer, ext, z, t[0], t[1]), jobs))
    ok = sum(t is not None for t in tiles)
    if ok == 0:
        print(f"  [경고] 브이월드 '{layer}' 타일을 받지 못했습니다. 원인: {_TILE_ERR.get(layer, '알 수 없음')}")
        fb = [le for le in (VW_FALLBACK if _fallback is None else _fallback) if le[0] != layer]
        if fb:
            print(f"  → 대체 배경 '{fb[0][0]}' 레이어로 다시 시도합니다.")
            return add_vworld(ax, extent, px_width, fb[0], alpha, _fallback=fb[1:])
        print("  → 흰 배경으로 출력합니다.")
        return False
    mosaic = Image.new("RGB", ((tx1 - tx0 + 1) * 256, (ty1 - ty0 + 1) * 256), "white")
    for (tx, ty), im in zip(jobs, tiles):
        if im is not None:
            mosaic.paste(im.resize((256, 256)), ((tx - tx0) * 256, (ty - ty0) * 256))
    ext_m = (-ORIGIN + tx0 * ts, -ORIGIN + (tx1 + 1) * ts, ORIGIN - (ty1 + 1) * ts, ORIGIN - ty0 * ts)
    ax.imshow(np.asarray(mosaic), extent=ext_m, origin="upper", interpolation="lanczos",
              alpha=alpha, zorder=0)
    if ok < len(jobs):
        print(f"  [주의] 타일 {len(jobs) - ok}개 누락")
    return True

# ---------------- 지도 장식 ----------------
def fit_extent(bounds, ax_w_in, ax_h_in, margin=0.04):
    x0, y0, x1, y1 = bounds
    w, h = x1 - x0, y1 - y0
    x0, x1, y0, y1 = x0 - w * margin, x1 + w * margin, y0 - h * margin, y1 + h * margin
    w, h = x1 - x0, y1 - y0
    target = ax_h_in / ax_w_in
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    if h / w < target:
        h = w * target
    else:
        w = h / target
    return (cx - w / 2, cx + w / 2, cy - h / 2, cy + h / 2)

def add_scalebar(ax, extent, lat_c, fs):
    x0, x1, y0, y1 = extent
    k = math.cos(math.radians(lat_c))                   # 3857 → 실거리 보정
    true_w = (x1 - x0) * k
    nice = [500, 1000, 2000, 2500, 5000, 10000, 20000]
    L = max([n for n in nice if n <= true_w / 5] or [nice[0]])
    Lm = L / k
    bx, by = x0 + (x1 - x0) * 0.04, y0 + (y1 - y0) * 0.035
    hh = (y1 - y0) * 0.006
    for i in range(4):
        ax.add_patch(Rectangle((bx + i * Lm / 4, by), Lm / 4, hh, fc="black" if i % 2 == 0 else "white",
                               ec="black", lw=1.5, zorder=20))
    for i, lab in [(0, "0"), (2, f"{L / 2000:g}"), (4, f"{L / 1000:g} km")]:
        ax.text(bx + i * Lm / 4, by + hh * 1.8, lab, ha="center", va="bottom", fontsize=fs,
                zorder=20, path_effects=HALO)

def add_north(ax, extent, fs):
    x0, x1, y0, y1 = extent
    x, y = x0 + (x1 - x0) * 0.06, y1 - (y1 - y0) * 0.09
    ax.annotate("N", xy=(x, y + (y1 - y0) * 0.04), xytext=(x, y), ha="center", va="top",
                fontsize=fs * 1.6, fontweight="bold", zorder=20,
                arrowprops=dict(facecolor="black", width=fs * 0.35, headwidth=fs * 1.1, headlength=fs * 1.2),
                path_effects=HALO)

def base_axes(fig, rect, extent):
    ax = fig.add_axes(rect)
    ax.set_xlim(extent[0], extent[1]); ax.set_ylim(extent[2], extent[3])
    ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values():
        s.set_linewidth(2)
    return ax

def draw_boundary(ax, emd3857, lw=3.0):
    emd3857.boundary.plot(ax=ax, color="white", linewidth=lw * 2.2, zorder=8)
    emd3857.boundary.plot(ax=ax, color="#222222", linewidth=lw, linestyle="-", zorder=9)

def label_dongs(ax, polys, text_fn, fs, color="black"):
    for _, r in polys.iterrows():
        p = r.geometry.representative_point()
        ax.text(p.x, p.y, text_fn(r), ha="center", va="center", fontsize=fs, fontweight="bold",
                color=color, zorder=15, linespacing=1.3, path_effects=HALO)

def quantile_bounds(values, qs=(0.0, 0.3, 0.5, 0.7, 0.85, 0.93, 0.97, 0.99)):
    v = np.asarray(values, float)
    v = v[np.isfinite(v) & (v >= MIN_POP)]
    if len(v) == 0:
        return np.array([MIN_POP, MIN_POP * 10])
    def r2(x):
        if x <= 0:
            return 0
        m = 10 ** (math.floor(math.log10(x)) - 1)
        return round(x / m) * m
    b = np.unique([max(MIN_POP, r2(q)) for q in np.quantile(v, qs)])
    if len(b) < 3:
        b = np.unique(np.round(np.linspace(v.min(), v.max(), 6)))
    b[0] = min(b[0], MIN_POP)
    return b

def footer(fig, text, fs):
    fig.text(0.985, 0.012, text, ha="right", va="bottom", fontsize=fs, color="#444")

# ============================================================
# 1. 로드
# ============================================================
print("▶ 데이터 로드")
frames = []
for yr, ly in POP_LAYERS.items():
    g = gpd.read_file(GPKG, layer=ly); g["연도"] = yr; frames.append(g)
pop = gpd.GeoDataFrame(pd.concat(frames, ignore_index=True), geometry="geometry", crs=frames[0].crs)
pop[COL_DONG] = pop[COL_DONG].map(norm_name)
if CCTV_XLSX and os.path.exists(CCTV_XLSX):
    _c = pd.read_excel(CCTV_XLSX)
    _c.columns = [str(c).replace("*", "").strip() for c in _c.columns]   # "위도*" → "위도"
    _c = _c.dropna(subset=["위도", "경도"])
    cctv = gpd.GeoDataFrame(_c, geometry=gpd.points_from_xy(_c["경도"], _c["위도"]), crs=4326).to_crs(pop.crs)
    print(f"  CCTV 설치현황(엑셀) {len(cctv)}개 로드")
else:
    cctv = gpd.read_file(GPKG, layer=CCTV_LAYER).to_crs(pop.crs)
    cctv.columns = [str(c).replace("*", "").strip() for c in cctv.columns]
emd  = gpd.read_file(GPKG, layer=EMD_LAYER).to_crs(pop.crs)

geo = pop.drop_duplicates(COL_GID)[[COL_GID, COL_DONG, "geometry"]].reset_index(drop=True)
geo = gpd.GeoDataFrame(geo, geometry="geometry", crs=pop.crs)

# --- 행정동 폴리곤: EMD 레이어 이름이 생활인구 행정동명과 맞으면 사용, 아니면 격자 dissolve
emd_name_col = next((c for c in [COL_DONG, "ADM_NM", "adm_nm", "EMD_KOR_NM", "EMD_NM", "HJD_NM"]
                     if c in emd.columns), None)
dong_poly = None
if emd_name_col:
    e = emd.copy(); e["dong"] = e[emd_name_col].map(norm_name)
    if set(geo[COL_DONG].dropna()) <= set(e["dong"]):
        dong_poly = e.dissolve("dong").reset_index()[["dong", "geometry"]]
if dong_poly is None:
    print("  [안내] EMD 레이어 이름이 행정동명과 불일치 → 100m 격자를 행정동별로 병합해 행정동 폴리곤 생성")
    dong_poly = geo.dissolve(COL_DONG).reset_index().rename(columns={COL_DONG: "dong"})[["dong", "geometry"]]
dong_poly["면적_km2"] = dong_poly.geometry.area / 1e6
DONGS = sorted(dong_poly["dong"])

# --- 방범용 CCTV 필터 + 설치연도
if PURPOSE_KEYWORD and COL_CCTV_PURPOSE in cctv.columns:
    n0 = len(cctv)
    cctv = cctv[cctv[COL_CCTV_PURPOSE].astype(str).str.contains(PURPOSE_KEYWORD, na=False)].copy()
    print(f"  방범용 CCTV 필터: {n0} → {len(cctv)}개")
if CLIP_CCTV_TO_EMD:
    n0 = len(cctv)
    cctv = cctv[cctv.within(emd.union_all().buffer(1))].copy()
    if len(cctv) < n0:
        print(f"  기장군 경계 밖 CCTV 제외: {n0} → {len(cctv)}개")
COL_CCTV_INSTALL = next((c for c in [COL_CCTV_INSTALL, "설치년월", "설치연월"] if c and c in cctv.columns), None)
if COL_CCTV_INSTALL:
    cctv["설치연도"] = cctv[COL_CCTV_INSTALL].astype(str).str.extract(r"((?:19|20)\d{2})")[0].astype(float)
    n_na = cctv["설치연도"].isna().sum()
    if n_na:
        print(f"  [주의] 설치연월 미상 {n_na}개 → 전 연도에 포함")
else:
    cctv["설치연도"] = np.nan
    print("  [안내] CCTV 설치현황(단일 시점)을 2022~2026년 모든 연도에 동일 적용")
USE_INSTALL = cctv["설치연도"].notna().any()
if USE_INSTALL:
    print("  연도 말 누적 방범용 CCTV:", {y: int((cctv["설치연도"].isna() | (cctv["설치연도"] <= y)).sum()) for y in YEARS})
cctv = cctv.reset_index(drop=True)
cctv["행정동"] = gpd.sjoin(cctv[["geometry"]], dong_poly[["dong", "geometry"]],
                          predicate="within", how="left").groupby(level=0)["dong"].first()
# --- 행정동 배정 보완 (경계 공간조인 실패분 → 설치요청주소의 읍·면)
addr_col = next((c for c in ["설치요청주소", "소재지지번주소", "소재지도로명주소"] if c in cctv.columns), None)
if addr_col:
    stem = {d[:-1]: d for d in DONGS}                      # "정관 달산리"처럼 읍·면이 빠진 주소도 인식
    addr_dong = (cctv[addr_col].astype(str).str.extract("(" + "|".join(stem) + ")(?:읍|면)?")[0].map(stem))
    n_fill = (cctv["행정동"].isna() & addr_dong.notna()).sum()
    n_diff = (cctv["행정동"].notna() & addr_dong.notna() & (cctv["행정동"] != addr_dong)).sum()
    cctv["행정동"] = cctv["행정동"].fillna(addr_dong)
    print(f"  행정동 주소 보완 {n_fill}개, 공간조인-주소 불일치 {n_diff}개(공간조인 우선)")
cctv["행정동"] = cctv["행정동"].fillna("미상")

def cctv_of_year(yr):
    yr = CCTV_YEAR_MAP.get(yr, yr)          # 2026 → 2025년(9월) 누적 CCTV
    return cctv[cctv["설치연도"].isna() | (cctv["설치연도"] <= yr)]

# ============================================================
# 2. 연도별 CCTV 커버리지 (격자 중심 반경 RADIUS_M 내 CCTV 수)
# ============================================================
buf = geo.copy(); buf["geometry"] = geo.geometry.centroid.buffer(RADIUS_M)
cov_list = []
for yr in YEARS:
    j = gpd.sjoin(cctv_of_year(yr)[["geometry"]], buf[[COL_GID, "geometry"]], predicate="within")
    s = j.groupby(COL_GID).size().reindex(geo[COL_GID]).fillna(0)
    cov_list.append(pd.DataFrame({"연도": yr, COL_GID: geo[COL_GID].values, "cctv_cov": s.values}))
cov_long = pd.concat(cov_list, ignore_index=True)

# --- 분자용 이웃 격자 목록: 격자 중심이 기준 격자 중심에서 반경 RADIUS_M 이내인 격자(자기 자신 포함)
#     100m 격자·반경 200m → 기준 격자 포함 13칸(≈0.13km², 원 면적 0.126km²와 거의 같음)
cent_pts = geo[[COL_GID, "geometry"]].copy(); cent_pts["geometry"] = geo.geometry.centroid
buf_eq = geo[[COL_GID, "geometry"]].copy(); buf_eq["geometry"] = cent_pts.geometry.buffer(RADIUS_M + 0.5)
nbr = (gpd.sjoin(cent_pts.rename(columns={COL_GID: "이웃GID"}), buf_eq, predicate="within")
       [[COL_GID, "이웃GID"]].reset_index(drop=True))
print(f"  반경 {RADIUS_M}m 이웃 격자 수(평균): {nbr.groupby(COL_GID).size().mean():.1f}칸")

def 반경인구(df, popcol, keys):
    """df(격자별 인구) → 격자 중심 반경 내 이웃 격자 인구 합. keys: 연도(+시간분류)"""
    if POP_SCOPE != "radius":
        return df[popcol].values
    m = nbr.merge(df[keys + [COL_GID, popcol]].rename(columns={COL_GID: "이웃GID"}), on="이웃GID")
    tot = m.groupby(keys + [COL_GID])[popcol].sum().rename("_r")
    return df.merge(tot.reset_index(), on=keys + [COL_GID], how="left")["_r"].fillna(0).values

def 명당인구(popval, cov):
    cov = np.asarray(cov, float)
    return np.where(cov > 0, np.asarray(popval, float) / np.where(cov == 0, np.nan, cov), np.inf)

def 판정(r, thr):
    if np.isinf(r):            return "부족"
    if np.isnan(r):            return "해당없음"
    if r >= thr * 부족_배수:    return "부족"
    if r <= thr * 많음_배수:    return "많음"
    return "적당"

# ============================================================
# 3. 연도별 임계값
# ============================================================
_hk = [COL_HOUR] if COL_HOUR in pop.columns else []
# 격자 × 시각 값 (경계 격자는 행정동별 행을 합산)
if GRID_AGG_MODE == "split":
    hourly = pop.groupby(["연도", COL_GID, COL_TCLS] + _hk)[COL_POP].sum().reset_index()
else:   # legacy: 원자료 행을 그대로 평균 (경계 격자는 두 행정동 행의 평균)
    hourly = pop[["연도", COL_GID, COL_TCLS, COL_POP] + _hk]
# 행정동 × 격자 × 시각 값 (행정동 집계용: 경계 격자는 행정동별로 나눠 반영)
hourly_d = pop.groupby(["연도", COL_DONG, COL_GID, COL_TCLS] + _hk)[COL_POP].sum().reset_index()
연평균 = hourly.groupby(["연도", COL_GID])[COL_POP].mean().reset_index(name="연평균생활인구")
연평균 = 연평균.merge(cov_long, on=["연도", COL_GID], how="left").fillna({"cctv_cov": 0})
연평균["반경내생활인구"] = 반경인구(연평균, "연평균생활인구", ["연도"])
연평균["명당인구"] = 명당인구(연평균["반경내생활인구"], 연평균["cctv_cov"])
연평균.loc[연평균["연평균생활인구"] < MIN_POP, "명당인구"] = np.nan
연평균[COL_DONG] = 연평균[COL_GID].map(geo.set_index(COL_GID)[COL_DONG])

thr_by_year = {}
for yr, d in 연평균.groupby("연도"):
    if THRESHOLD_MODE == "manual" and yr in MANUAL_THRESHOLD:
        thr_by_year[yr] = float(MANUAL_THRESHOLD[yr])
    else:
        thr_by_year[yr] = float(d.loc[np.isfinite(d["명당인구"]), "명당인구"].mean())
연평균["판정"] = [판정(r, thr_by_year[y]) for r, y in zip(연평균["명당인구"], 연평균["연도"])]
pd.DataFrame({"연도": list(thr_by_year), "임계값_명당인구": list(thr_by_year.values())}
    ).to_csv(os.path.join(OUTPUT_PATH, "임계값_연도별.csv"), index=False, encoding="utf-8-sig")
print("연도별 임계값(명/대):", {k: round(v, 1) for k, v in thr_by_year.items()})

# ============================================================
# 4. 시간분류 × 격자 × 연도 판정
# ============================================================
agg = hourly.groupby(["연도", COL_GID, COL_TCLS])[COL_POP].mean().reset_index()
agg = agg.merge(cov_long, on=["연도", COL_GID], how="left").fillna({"cctv_cov": 0})
agg["반경내생활인구"] = 반경인구(agg, COL_POP, ["연도", COL_TCLS])
agg["명당인구"] = 명당인구(agg["반경내생활인구"], agg["cctv_cov"])
agg = agg.merge(연평균[["연도", COL_GID, "연평균생활인구"]], on=["연도", COL_GID], how="left")
agg.loc[agg["연평균생활인구"] < MIN_POP, "명당인구"] = np.nan
agg["임계값"] = agg["연도"].map(thr_by_year)
agg["판정"] = [판정(r, t) for r, t in zip(agg["명당인구"], agg["임계값"])]
agg[COL_DONG] = agg[COL_GID].map(geo.set_index(COL_GID)[COL_DONG])
agg.to_csv(os.path.join(OUTPUT_PATH, "격자별_수급분석_전체.csv"), index=False, encoding="utf-8-sig")

rows = []
for yr in YEARS:
    a = agg[agg["연도"] == yr]
    s = a.groupby([COL_TCLS, "판정"]).size().unstack(fill_value=0).reindex(TIME_ORDER).fillna(0)
    for c in ["부족", "적당", "많음", "해당없음"]:
        s[c] = s[c] if c in s else 0
    s = s[["부족", "적당", "많음", "해당없음"]]
    s["부족비율%"] = (s["부족"] / s[["부족", "적당", "많음"]].sum(axis=1).replace(0, np.nan) * 100).round(1)
    rows.append(s.assign(연도=yr).reset_index())
pd.concat(rows).to_csv(os.path.join(OUTPUT_PATH, "수급요약_시간분류별_연도별.csv"),
                       index=False, encoding="utf-8-sig")

# ============================================================
# 5. 연도 × 행정동 요약 (CCTV 수, 생활인구, 생활인구)
# ============================================================
# 5-1. 격자 기반 행정동 평균 생활인구 (= 격자 연평균의 합)
if GRID_AGG_MODE == "split":
    grid_dong = (hourly_d.groupby(["연도", COL_DONG, COL_GID])[COL_POP].mean()      # 격자별 시각 평균
                 .groupby(["연도", COL_DONG]).sum().rename("생활인구").reset_index())
else:
    grid_dong = 연평균.groupby(["연도", COL_DONG])["연평균생활인구"].sum().rename("생활인구").reset_index()
print(f"  격자 생활인구 집계 방식: {GRID_AGG_MODE} →",
      grid_dong.groupby("연도")["생활인구"].sum().round(0).to_dict())

# 5-2. 생활인구 (유입지별 자료 / 없으면 격자 합산값)
def read_any(src):
    if str(src).lower().endswith(".csv"):
        for enc in ("utf-8-sig", "cp949"):
            try:
                return pd.read_csv(src, encoding=enc)
            except UnicodeDecodeError:
                continue
    return pd.DataFrame(gpd.read_file(GPKG, layer=src).drop(columns="geometry", errors="ignore"))

def load_inflow_wide(path):
    """가로형 행정동 생활인구 표 → (연도, 행정동명, 생활인구) 세로형. 구분자 자동 인식(| , 탭)"""
    for enc in ("utf-8-sig", "cp949"):
        try:
            w = pd.read_csv(path, sep=None, engine="python", encoding=enc)
            break
        except UnicodeDecodeError:
            continue
    ycol = w.columns[0]
    w["연도"] = w[ycol].astype(str).str.extract(r"((?:19|20)\d{2})")[0].astype(int)
    long = w.drop(columns=ycol).melt(id_vars="연도", var_name=COL_DONG, value_name="생활인구_유입지")
    long[COL_DONG] = long[COL_DONG].map(norm_name)
    long["생활인구_유입지"] = pd.to_numeric(long["생활인구_유입지"], errors="coerce")
    if ANNUALIZE_PARTIAL:
        long["생활인구_유입지"] = long["생활인구_유입지"] * 12 / long["연도"].map(lambda y: POP_MONTHS.get(y, 12))
    return long[long[COL_DONG].isin(DONGS)]

if INFLOW_WIDE_CSV and os.path.exists(INFLOW_WIDE_CSV):
    flow = load_inflow_wide(INFLOW_WIDE_CSV)
    FLOW_DESC = "유입지별 생활인구 행정동 연평균" + (" · 2026년은 1~7월 × 12/7 연환산" if ANNUALIZE_PARTIAL else "")
    print(f"  생활인구: {INFLOW_WIDE_CSV} 사용 →", flow.groupby("연도")["생활인구_유입지"].sum().round(0).to_dict())
elif INFLOW_SOURCES:
    flow_rows = []
    for yr, src in INFLOW_SOURCES.items():
        df = read_any(src)
        df[INFLOW_COL_DONG] = df[INFLOW_COL_DONG].map(norm_name)
        if INFLOW_EXTERNAL_ONLY and INFLOW_COL_ORIGIN in df:
            df = df[df[INFLOW_COL_ORIGIN].map(norm_name) != df[INFLOW_COL_DONG]]
        keys = [c for c in (INFLOW_COL_DATE, INFLOW_COL_TIME) if c in df]
        if keys:
            v = df.groupby([INFLOW_COL_DONG] + keys)[INFLOW_COL_POP].sum().groupby(level=0).mean()
        else:
            v = df.groupby(INFLOW_COL_DONG)[INFLOW_COL_POP].mean()
        flow_rows.append(pd.DataFrame({"연도": yr, COL_DONG: v.index, "생활인구_유입지": v.values}))
    flow = pd.concat(flow_rows, ignore_index=True)
    FLOW_DESC = "일별 행정동 유입지별 시간대 생활인구" + (" (외부 유입)" if INFLOW_EXTERNAL_ONLY else "")
else:
    flow = grid_dong.rename(columns={"생활인구": "생활인구_유입지"})
    FLOW_DESC = "일별 행정동 100m 격자 시간대 생활인구 (행정동 합산)"

cctv_cnt = pd.DataFrame([{"연도": yr, COL_DONG: d, "CCTV수": n}
                         for yr in YEARS
                         for d, n in cctv_of_year(yr).groupby("행정동").size().items()])
dong_sum = (pd.MultiIndex.from_product([YEARS, DONGS], names=["연도", COL_DONG]).to_frame(index=False)
            .merge(grid_dong, how="left").merge(flow, how="left").merge(cctv_cnt, how="left")
            .fillna({"CCTV수": 0}))
dong_sum["면적_km2"] = dong_sum[COL_DONG].map(dong_poly.set_index("dong")["면적_km2"])
dong_sum["인구밀도_명km2"] = dong_sum["생활인구"] / dong_sum["면적_km2"]
dong_sum["CCTV1대당_생활인구"] = dong_sum["생활인구"] / dong_sum["CCTV수"].replace(0, np.nan)
부족격자 = (연평균[연평균["판정"] == "부족"].groupby(["연도", COL_DONG]).size().rename("부족격자수"))
dong_sum = dong_sum.merge(부족격자.reset_index(), how="left").fillna({"부족격자수": 0})
dong_sum["생활인구_전년대비%"] = dong_sum.sort_values("연도").groupby(COL_DONG)["생활인구_유입지"].pct_change() * 100
dong_sum.to_csv(os.path.join(OUTPUT_PATH, "연도별_행정동별_요약.csv"), index=False, encoding="utf-8-sig")

# ============================================================
# 5-3. [2022~2026] 연도별 CCTV 설치현황 집계 (행정동 × 100m 격자)
# ============================================================
#  · 기준: 각 연도 말(12월) 누적 = 설치년월의 연도 ≤ 해당 연도인 방범용 CCTV  (2025년은 9월까지 설치분, 2026년 생활인구는 2025.9 CCTV와 비교)
#  · 대수: 카메라대수 합계 (컬럼이 없으면 설치 지점 1곳 = 1대)
#  · 격자 배정: CCTV 좌표가 들어가는 생활인구 100m 격자(공간조인). 생활인구 격자가 없는 곳은 '격자없음'
#  · 행정동 배정: 행정동 경계 공간조인 → 실패 시 설치요청주소의 읍·면 이름으로 보완
print("▶ 연도별 CCTV 설치현황 집계 (행정동 × 100m 격자)")
cam = (pd.to_numeric(cctv[COL_CCTV_CAM], errors="coerce").fillna(1)
       if COL_CCTV_CAM in cctv.columns else pd.Series(1, index=cctv.index))
cctv["카메라대수_n"] = cam.clip(lower=1).astype(int)

# (1) 격자 배정
_gj = gpd.sjoin(cctv[["geometry"]], geo[[COL_GID, "geometry"]], predicate="within", how="left")
cctv[COL_GID] = _gj.groupby(level=0)[COL_GID].first().reindex(cctv.index).fillna("격자없음")
cctv["격자X"] = (cctv.geometry.x // 100 * 100).astype(int)      # 100m 격자 좌하단 좌표(EPSG:5179), 검증용
cctv["격자Y"] = (cctv.geometry.y // 100 * 100).astype(int)
# (2) 행정동 배정은 1. 로드 단계에서 완료 (모든 집계표가 같은 행정동 배정을 쓰도록)
print(f"  생활인구 격자 밖 CCTV: {(cctv[COL_GID] == '격자없음').sum()}개")

# (3) 격자별 연도별 누적·신규
grid_rows = []
for yr in CCTV_YEARS:
    cy = cctv_of_year(yr)
    g = (cy.groupby(["행정동", COL_GID, "격자X", "격자Y"])
           .agg(누적_CCTV=("카메라대수_n", "sum"), 설치지점수=("카메라대수_n", "size"))
           .reset_index())
    new_ = (cy[cy["설치연도"] == yr].groupby(COL_GID)["카메라대수_n"].sum())
    g["당해신규_CCTV"] = g[COL_GID].map(new_).fillna(0).astype(int)
    grid_rows.append(g.assign(연도=yr))
cctv_grid = pd.concat(grid_rows, ignore_index=True)
cctv_grid = cctv_grid.merge(연평균[["연도", COL_GID, "연평균생활인구", "반경내생활인구", "cctv_cov", "명당인구", "판정"]]
                            .rename(columns={"cctv_cov": "반경내_CCTV"}), on=["연도", COL_GID], how="left")
cctv_grid["격자_1대당_생활인구"] = cctv_grid["연평균생활인구"] / cctv_grid["누적_CCTV"]
cctv_grid["CCTV_기준시점"] = cctv_grid["연도"].map(CCTV_BASIS)
cctv_grid = cctv_grid[["연도", "CCTV_기준시점", "행정동", COL_GID, "격자X", "격자Y", "누적_CCTV", "당해신규_CCTV", "설치지점수",
                       "연평균생활인구", "격자_1대당_생활인구", "반경내생활인구", "반경내_CCTV", "명당인구", "판정"]]
cctv_grid.sort_values(["연도", "행정동", "누적_CCTV"], ascending=[True, True, False]).to_csv(
    os.path.join(OUTPUT_PATH, "CCTV_격자별_연도별_설치현황_2022-2026.csv"), index=False, encoding="utf-8-sig")

# (4) 행정동별 연도별 설치현황
pop_grid_n = 연평균[연평균["연평균생활인구"] >= MIN_POP].groupby(["연도", COL_DONG]).size()
dong_rows = []
for yr in CCTV_YEARS:
    cy = cctv_of_year(yr)
    for d in DONGS + ["미상"]:
        c = cy[cy["행정동"] == d]
        if d == "미상" and c.empty:
            continue
        cg = c[c[COL_GID] != "격자없음"][COL_GID].nunique()
        pg = pop_grid_n.get((yr, d), np.nan)
        dong_rows.append({"연도": yr, "행정동": d,
                          "누적_CCTV": int(c["카메라대수_n"].sum()),
                          "당해신규_CCTV": int(c.loc[c["설치연도"] == yr, "카메라대수_n"].sum()),
                          "설치지점수": len(c), "CCTV설치_격자수": cg, "생활인구_격자수": pg,
                          "설치격자비율_%": cg / pg * 100 if pg else np.nan,
                          "설치격자당_CCTV": c["카메라대수_n"].sum() / cg if cg else np.nan})
cctv_dong = pd.DataFrame(dong_rows)
tot = (cctv_dong.groupby("연도")[["누적_CCTV", "당해신규_CCTV", "설치지점수", "CCTV설치_격자수", "생활인구_격자수"]]
       .sum().reset_index().assign(행정동="기장군 계"))
tot["설치격자비율_%"] = tot["CCTV설치_격자수"] / tot["생활인구_격자수"] * 100
tot["설치격자당_CCTV"] = tot["누적_CCTV"] / tot["CCTV설치_격자수"]
cctv_dong = pd.concat([cctv_dong, tot], ignore_index=True)
cctv_dong["전년대비_증가율_%"] = cctv_dong.sort_values("연도").groupby("행정동")["누적_CCTV"].pct_change() * 100
cctv_dong.insert(1, "CCTV_기준시점", cctv_dong["연도"].map(CCTV_BASIS))
cctv_dong.to_csv(os.path.join(OUTPUT_PATH, "CCTV_행정동별_연도별_설치현황_2022-2026.csv"),
                 index=False, encoding="utf-8-sig")

# ============================================================
# 5-4. [2022~2026] 연도별 행정동별 CCTV 1대당 생활인구
# ============================================================
#  · 행정동 생활인구 = Σ(행정동 내 100m 격자의 연평균 생활인구)  → '평소 동시에 머무는 평균 인원'
#    (격자 연평균 = 해당 연도 모든 일자·시간분류의 평균)
#  · 시간분류별 생활인구 = Σ(격자의 해당 시간분류 평균 생활인구)
#  · CCTV 1대당 생활인구 = 행정동 생활인구 ÷ 해당 연도 말 누적 방범용 CCTV 대수
print("▶ 연도별 행정동별 CCTV 1대당 생활인구")
if GRID_AGG_MODE == "split":
    _hd = hourly_d[hourly_d["연도"].isin(CCTV_YEARS)]
    pop_y = (_hd.groupby(["연도", COL_DONG, COL_GID])[COL_POP].mean()
             .groupby(["연도", COL_DONG]).sum().rename("연평균_생활인구"))
    pop_t = (_hd.groupby(["연도", COL_DONG, COL_GID, COL_TCLS])[COL_POP].mean()
             .groupby(["연도", COL_DONG, COL_TCLS]).sum()
             .unstack(COL_TCLS).reindex(columns=TIME_ORDER))
else:
    pop_y = (연평균[연평균["연도"].isin(CCTV_YEARS)].groupby(["연도", COL_DONG])["연평균생활인구"].sum()
             .rename("연평균_생활인구"))
    pop_t = (agg[agg["연도"].isin(CCTV_YEARS)].groupby(["연도", COL_DONG, COL_TCLS])[COL_POP].sum()
             .unstack(COL_TCLS).reindex(columns=TIME_ORDER))
pop_t.columns = [f"생활인구_{t}" for t in pop_t.columns]
per = (pd.concat([pop_y, pop_t], axis=1).reset_index().rename(columns={COL_DONG: "행정동"})
       .merge(cctv_dong[["연도", "행정동", "누적_CCTV"]], on=["연도", "행정동"], how="left"))
pop_cols = ["연평균_생활인구"] + list(pop_t.columns)
per_tot = per.groupby("연도")[pop_cols + ["누적_CCTV"]].sum(min_count=1).reset_index().assign(행정동="기장군 계")
if "미상" in set(cctv_dong["행정동"]):   # 행정동 미상 CCTV는 군 합계에만 반영
    per_tot["누적_CCTV"] = per_tot["연도"].map(cctv_dong[cctv_dong["행정동"] == "기장군 계"]
                                             .set_index("연도")["누적_CCTV"])
per = pd.concat([per, per_tot], ignore_index=True)
den = per["누적_CCTV"].replace(0, np.nan)
per["CCTV1대당_생활인구"] = per["연평균_생활인구"] / den
for t in TIME_ORDER:
    per[f"1대당_{t}"] = per[f"생활인구_{t}"] / den
per["1대당_전년대비_%"] = per.sort_values("연도").groupby("행정동")["CCTV1대당_생활인구"].pct_change() * 100
per.insert(1, "생활인구_기간", per["연도"].map(POP_PERIOD))
per.insert(2, "CCTV_기준시점", per["연도"].map(CCTV_BASIS))
# 검산: '기장군 계'의 1대당 생활인구 = 군 전체 생활인구 ÷ 군 전체 CCTV (비율이므로 행정동 값의 단순 합·단순 평균이 아님)
#       = Σ(행정동 1대당 × 행정동 CCTV 비중) (CCTV 대수 가중평균)
chk = []
for yr, d in per.groupby("연도"):
    dd, tt = d[d["행정동"] != "기장군 계"], d[d["행정동"] == "기장군 계"].iloc[0]
    n_unk = int(cctv_dong.query("연도 == @yr and 행정동 == '미상'")["누적_CCTV"].sum())
    w = dd["누적_CCTV"] / dd["누적_CCTV"].sum()
    chk.append({"연도": yr,
                "행정동_CCTV_합": dd["누적_CCTV"].sum(), "행정동미상_CCTV": n_unk, "군_CCTV_계": tt["누적_CCTV"],
                "행정동_생활인구_합": dd["연평균_생활인구"].sum(), "군_생활인구_계": tt["연평균_생활인구"],
                "군_1대당(합÷합)": tt["CCTV1대당_생활인구"],
                "행정동_1대당_CCTV가중평균": (dd["CCTV1대당_생활인구"] * w).sum(),
                "행정동_1대당_단순합(참고·의미없음)": dd["CCTV1대당_생활인구"].sum(),
                "행정동_1대당_단순평균(참고)": dd["CCTV1대당_생활인구"].mean()})
    if n_unk:
        print(f"  [주의] {yr}년 행정동 미상 CCTV {n_unk}대 → 군 계에만 포함되어 행정동 합과 {n_unk}대 차이")
check = pd.DataFrame(chk)
print("  [검산]\n" + check.round(1).to_string(index=False))
check.to_csv(os.path.join(OUTPUT_PATH, "검산_CCTV1대당_생활인구_2022-2026.csv"), index=False, encoding="utf-8-sig")
per.to_csv(os.path.join(OUTPUT_PATH, "연도별_행정동별_CCTV1대당_생활인구_2022-2026.csv"),
           index=False, encoding="utf-8-sig")

# 요약 피벗 (콘솔 + 엑셀)
pv_cnt = cctv_dong.pivot(index="행정동", columns="연도", values="누적_CCTV")
pv_new = cctv_dong.pivot(index="행정동", columns="연도", values="당해신규_CCTV")
pv_per = per.pivot(index="행정동", columns="연도", values="CCTV1대당_생활인구").round(0)
print("  [누적 방범용 CCTV(대)]\n" + pv_cnt.to_string())
print("  [CCTV 1대당 생활인구(명/대)]\n" + pv_per.to_string())
try:
    with pd.ExcelWriter(os.path.join(OUTPUT_PATH, "CCTV_설치현황_1대당생활인구_2022-2026.xlsx")) as xw:
        pv_cnt.to_excel(xw, sheet_name="행정동_누적CCTV")
        pv_new.to_excel(xw, sheet_name="행정동_당해신규")
        pv_per.to_excel(xw, sheet_name="행정동_1대당생활인구")
        cctv_dong.to_excel(xw, sheet_name="행정동별_설치현황", index=False)
        per.to_excel(xw, sheet_name="1대당생활인구_상세", index=False)
        cctv_grid.to_excel(xw, sheet_name="격자별_설치현황", index=False)
        check.to_excel(xw, sheet_name="검산", index=False)
except ImportError:
    print("  [안내] openpyxl 미설치 → 엑셀 요약 생략 (CSV는 저장됨)")

# ============================================================
# 6. 지도용 좌표 변환 (EPSG:3857 = 브이월드 WMTS)
# ============================================================
geo3857  = geo.to_crs(3857)
emd3857  = emd.to_crs(3857)
dong3857 = dong_poly.to_crs(3857)
cctv3857 = cctv.to_crs(3857)
bounds   = emd3857.total_bounds
lat_c    = gpd.GeoSeries([emd.union_all().centroid], crs=emd.crs).to_crs(4326).iloc[0].y
if ORIENT == "auto":
    ORIENT = "portrait" if (bounds[3] - bounds[1]) >= (bounds[2] - bounds[0]) * 0.9 else "landscape"
FIG_W, FIG_H = paper_inches(ORIENT)
MAP_RECT = [0.035, 0.075, 0.93, 0.82]          # 지도 영역(그림 비율)
AX_W_IN, AX_H_IN = FIG_W * MAP_RECT[2], FIG_H * MAP_RECT[3]
EXTENT = fit_extent(bounds, AX_W_IN, AX_H_IN)
AX_PX  = AX_W_IN * DPI
FS = dict(title=54, sub=30, label=26, legend=24, small=20)   # A1 인쇄용 pt

def new_sheet(title, subtitle):
    fig = plt.figure(figsize=(FIG_W, FIG_H), dpi=DPI, facecolor="white")
    fig.text(0.035, 0.965, title, fontsize=FS["title"], fontweight="bold", va="top")
    fig.text(0.035, 0.935, subtitle, fontsize=FS["sub"], color="#333", va="top")
    return fig

def save(fig, name):
    p = os.path.join(PNG_DIR, name)
    fig.savefig(p, dpi=DPI, facecolor="white")
    plt.close(fig)
    with Image.open(p) as im:
        w, h = im.size
    print(f"  saved {p}  ({w}×{h}px = {w / DPI * 25.4:.0f}×{h / DPI * 25.4:.0f}mm @ {DPI}dpi)")

SRC_NOTE = ("배경지도: 국토교통부 브이월드(VWorld) · 자료: 일별 행정동 100m 격자 시간대 생활인구, "
            "일별 행정동 유입지별 시간대 생활인구, CCTV 설치현황 · 2026년은 1~7월 자료")

# ============================================================
# 7. ① 연도별 CCTV 설치위치 × 100m 격자 생활인구 히트맵 × 행정동
# ============================================================
print("▶ ① CCTV 설치현황 지도")
heat_bounds = quantile_bounds(연평균["연평균생활인구"])     # 5개년 공통 구간 → 연도 간 비교 가능
heat_cmap = ListedColormap(plt.get_cmap(HEAT_CMAP)(np.linspace(0.08, 1, len(heat_bounds))))
heat_cmap.set_under((0, 0, 0, 0))
heat_norm = BoundaryNorm(heat_bounds, heat_cmap.N, extend="max")

def draw_heat(ax, g):
    g = g[g["연평균생활인구"] >= MIN_POP]
    if HEAT_STYLE == "kde":
        from scipy.ndimage import gaussian_filter
        px = 25.0
        c = g.geometry.centroid
        xe = np.arange(EXTENT[0], EXTENT[1] + px, px); ye = np.arange(EXTENT[2], EXTENT[3] + px, px)
        H, _, _ = np.histogram2d(c.y, c.x, bins=[ye, xe], weights=g["연평균생활인구"])
        H = gaussian_filter(H, sigma=120 / px) * (100 * 100) / (px * px)   # 100m 격자 단위 환산
        H = np.ma.masked_less(H, heat_bounds[0])
        ax.imshow(H, extent=(xe[0], xe[-1], ye[0], ye[-1]), origin="lower", cmap=heat_cmap,
                  norm=heat_norm, alpha=HEAT_ALPHA, zorder=3, interpolation="bilinear")
    else:
        g.plot(ax=ax, column="연평균생활인구", cmap=heat_cmap, norm=heat_norm,
               alpha=HEAT_ALPHA, linewidth=0, zorder=3)

for yr in YEARS:
    ylab = YEAR_LABEL[yr]
    cy = cctv3857[cctv3857["설치연도"].isna() | (cctv3857["설치연도"] <= yr)]
    new = cy[cy["설치연도"] == yr]
    old = cy.drop(new.index)
    ds = dong_sum[dong_sum["연도"] == yr].set_index(COL_DONG)
    ref = f" {CCTV_REF_DATE}" if CCTV_REF_DATE else ""
    fig = new_sheet(f"기장군 {ylab} 생활인구 분포와 방범용 CCTV 설치현황",
                    f"100m 격자 연평균 생활인구({ylab}) × 행정동 경계 × 방범용 CCTV {len(cy):,}대"
                    + ((f" ({yr}년 말 기준 누적 · 당해 신규 {len(new):,}대)" if yr < 2026 or len(new)
                        else f" ({CCTV_REF_DATE or '최종'} 설치이력 기준 누적)") if USE_INSTALL
                       else f" (설치현황{ref} 기준, 5개년 공통)")
                    + f"\n명당인구(반경 {RADIUS_M}m 내 생활인구 ÷ 반경 내 CCTV) 임계값 {thr_by_year[yr]:,.0f}명/대")
    ax = base_axes(fig, MAP_RECT, EXTENT)
    add_vworld(ax, EXTENT, AX_PX, VW_LAYER_CCTV)
    g = geo3857.merge(연평균[연평균["연도"] == yr][[COL_GID, "연평균생활인구"]], on=COL_GID)
    draw_heat(ax, g)
    draw_boundary(ax, emd3857)
    ax.scatter(old.geometry.x, old.geometry.y, s=70, c=CCTV_COLOR, edgecolors="white",
               linewidths=1.2, zorder=12)
    if len(new):
        ax.scatter(new.geometry.x, new.geometry.y, s=110, c=CCTV_NEW_COLOR, marker="D",
                   edgecolors="black", linewidths=1.2, zorder=13)
    label_dongs(ax, dong3857, lambda r: (f"{r['dong']}\nCCTV {ds.loc[r['dong'], 'CCTV수']:,.0f}대"
                                         f" · 생활인구 {fmt(ds.loc[r['dong'], '생활인구'])}명")
                if r["dong"] in ds.index else r["dong"], FS["label"])
    add_scalebar(ax, EXTENT, lat_c, FS["small"]); add_north(ax, EXTENT, FS["label"])

    handles = [Line2D([], [], marker="o", ls="", ms=16, mfc=CCTV_COLOR, mec="white",
                      label=f"방범용 CCTV ({len(old):,}대)")]
    if len(new):
        handles.append(Line2D([], [], marker="D", ls="", ms=16, mfc=CCTV_NEW_COLOR, mec="black",
                              label=f"{yr}년 신규 설치 ({len(new):,}대)"))
    handles.append(Line2D([], [], color="#222", lw=4, label="행정동 경계"))
    ax.legend(handles=handles, loc="upper right", fontsize=FS["legend"], frameon=True,
              framealpha=0.92, borderpad=1.0, title="범례", title_fontsize=FS["legend"]).set_zorder(30)
    # 행정동 요약표
    tb = ds.reindex(DONGS)
    cell = [[d, f"{tb.loc[d, 'CCTV수']:,.0f}", fmt(tb.loc[d, "생활인구"]),
             fmt(tb.loc[d, "CCTV1대당_생활인구"]), f"{tb.loc[d, '부족격자수']:,.0f}"] for d in DONGS]
    cell.append(["합계", f"{tb['CCTV수'].sum():,.0f}", fmt(tb["생활인구"].sum()),
                 fmt(tb["생활인구"].sum() / max(tb["CCTV수"].sum(), 1)), f"{tb['부족격자수'].sum():,.0f}"])
    tax = fig.add_axes([0.58, 0.09, 0.37, 0.022 * (len(cell) + 1)]); tax.axis("off")
    t = tax.table(cellText=cell, colLabels=["행정동", "CCTV(대)", "생활인구(명)", "1대당(명)", "부족격자"],
                  loc="center", cellLoc="center", bbox=[0, 0, 1, 1])
    t.auto_set_font_size(False); t.set_fontsize(FS["small"])
    for (r, c), cl in t.get_celld().items():
        cl.set_edgecolor("#888"); cl.set_facecolor("#e8eef7" if r == 0 else (1, 1, 1, 0.92))
        if r == 0 or r == len(cell):
            cl.get_text().set_fontweight("bold")
    # 컬러바
    cax = fig.add_axes([0.2, 0.045, 0.6, 0.013])
    cb = fig.colorbar(ScalarMappable(heat_norm, heat_cmap), cax=cax, orientation="horizontal",
                      spacing="uniform", ticks=heat_bounds, extend="max")
    cb.ax.set_xticklabels([f"{b:,.0f}" for b in heat_bounds], fontsize=FS["small"])
    cb.set_label("100m 격자 연평균 생활인구 (명, 5개년 공통 구간)", fontsize=FS["legend"])
    footer(fig, SRC_NOTE, FS["small"] * 0.8)
    save(fig, f"01_CCTV설치현황_{yr}.png")

# ============================================================
# 8. ② 행정동별 생활인구 색온도 지도 (5장)
# ============================================================
print("▶ ② 생활인구 색온도 지도")
fv = dong_sum["생활인구_유입지"].dropna()
temp_norm = Normalize(vmin=fv.min() * 0.95, vmax=fv.max() * 1.02)   # 5개년 공통 스케일
temp_cmap = plt.get_cmap(TEMP_CMAP)
for yr in YEARS:
    ylab = YEAR_LABEL[yr]
    ds = dong_sum[dong_sum["연도"] == yr].set_index(COL_DONG)
    fig = new_sheet(f"기장군 행정동별 생활인구 색온도 지도 ({ylab})",
                    f"행정동 평균 시간대 생활인구 (자료: {FLOW_DESC})  |  "
                    f"기장군 합계 {fmt(ds['생활인구_유입지'].sum())}명")
    ax = base_axes(fig, MAP_RECT, EXTENT)
    add_vworld(ax, EXTENT, AX_PX, VW_LAYER_CHORO)
    d = dong3857.merge(ds[["생활인구_유입지", "생활인구_전년대비%"]], left_on="dong", right_index=True, how="left")
    d.plot(ax=ax, column="생활인구_유입지", cmap=temp_cmap, norm=temp_norm, alpha=0.68, linewidth=0, zorder=3,
           missing_kwds={"color": "#dddddd", "alpha": 0.5})
    draw_boundary(ax, emd3857)
    def lab(r):
        s = f"{r['dong']}\n{fmt(r['생활인구_유입지'])}명"
        if pd.notna(r["생활인구_전년대비%"]):
            s += f"\n(전년比 {r['생활인구_전년대비%']:+.1f}%)"
        return s
    label_dongs(ax, d, lab, FS["label"] * 1.15)
    add_scalebar(ax, EXTENT, lat_c, FS["small"]); add_north(ax, EXTENT, FS["label"])
    cax = fig.add_axes([0.2, 0.045, 0.6, 0.013])
    cb = fig.colorbar(ScalarMappable(temp_norm, temp_cmap), cax=cax, orientation="horizontal")
    cb.ax.tick_params(labelsize=FS["small"])
    cb.ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:,.0f}"))
    cb.set_label("생활인구 (명)  ◀ 낮음(차가움) ─ 높음(뜨거움) ▶  · 5개년 공통 스케일", fontsize=FS["legend"])
    footer(fig, SRC_NOTE, FS["small"] * 0.8)
    save(fig, f"02_생활인구_색온도_{yr}.png")

# ============================================================
# 9. ③ 행정동별 인구분포 — 연도별 A1 PNG (03_행정동별_인구분포_{연도}.png)
#    행정동 인구밀도(명/km²) = 100m 격자 연평균 생활인구 합 ÷ 행정동 면적, 5개년 공통 색상 구간
# ============================================================
print("▶ ③ 행정동별 인구분포 (연도별)")
LW, LH = paper_inches("landscape")
dens = dong_sum["인구밀도_명km2"].dropna()
dens_bounds = np.unique(np.round(np.quantile(dens, np.linspace(0, 1, 7)), -1))
if len(dens_bounds) < 3:
    dens_bounds = np.linspace(dens.min(), dens.max() + 1, 6)
dens_bounds[-1] = max(dens_bounds[-1], dens.max() + 1)
dens_cmap = ListedColormap(plt.get_cmap(DENS_CMAP)(np.linspace(0.12, 1, len(dens_bounds) - 1)))
dens_norm = BoundaryNorm(dens_bounds, dens_cmap.N)
SRC_NOTE3 = ("배경지도: 국토교통부 브이월드(VWorld) · 자료: 일별 행정동 100m 격자 시간대 생활인구(행정동 합산) · "
             "경계: 읍면동(EMD) · 2026년은 1~7월 자료")
piv_all = dong_sum.pivot(index=COL_DONG, columns="연도", values="생활인구").reindex(DONGS)
for yr in YEARS:
    ylab = YEAR_LABEL[yr]
    ds = dong_sum[dong_sum["연도"] == yr].set_index(COL_DONG)
    fig = new_sheet(f"기장군 {ylab} 행정동별 생활인구 분포",
                    f"행정동 인구밀도(명/km²) = 100m 격자 연평균 생활인구 합 ÷ 행정동 면적  ·  5개년 공통 색상 구간"
                    f"\n기장군 생활인구 합계 {fmt(ds['생활인구'].sum())}명")
    ax = base_axes(fig, MAP_RECT, EXTENT)
    add_vworld(ax, EXTENT, AX_PX, VW_LAYER_CHORO)
    d = dong3857.merge(ds[["인구밀도_명km2", "생활인구"]], left_on="dong", right_index=True, how="left")
    d.plot(ax=ax, column="인구밀도_명km2", cmap=dens_cmap, norm=dens_norm, alpha=0.75, linewidth=0, zorder=3)
    draw_boundary(ax, emd3857)
    label_dongs(ax, d, lambda r: f"{r['dong']}\n{fmt(r['인구밀도_명km2'])}명/km²\n생활인구 {fmt(r['생활인구'])}명",
                FS["label"] * 1.1)
    add_scalebar(ax, EXTENT, lat_c, FS["small"]); add_north(ax, EXTENT, FS["label"])
    # 행정동 표 (오른쪽 아래)
    cell = [[dn, fmt(ds.loc[dn, "면적_km2"]) if ds.loc[dn, "면적_km2"] >= 1 else f"{ds.loc[dn, '면적_km2']:.2f}",
             fmt(ds.loc[dn, "생활인구"]), fmt(ds.loc[dn, "인구밀도_명km2"])] for dn in DONGS if dn in ds.index]
    tot_p, tot_a = ds["생활인구"].sum(), ds["면적_km2"].sum()
    cell.append(["합계", fmt(tot_a), fmt(tot_p), fmt(tot_p / tot_a)])
    tax = fig.add_axes([0.60, 0.09, 0.35, 0.022 * (len(cell) + 1)]); tax.axis("off")
    t = tax.table(cellText=cell, colLabels=["행정동", "면적(km²)", "생활인구(명)", "밀도(명/km²)"],
                  loc="center", cellLoc="center", bbox=[0, 0, 1, 1])
    t.auto_set_font_size(False); t.set_fontsize(FS["small"])
    for (r_, c_), cl in t.get_celld().items():
        cl.set_edgecolor("#888"); cl.set_facecolor("#e8eef7" if r_ == 0 else (1, 1, 1, 0.92))
        if r_ == 0 or r_ == len(cell):
            cl.get_text().set_fontweight("bold")
    # 연도별 추이 막대 (오른쪽 위, 당해 연도 강조)
    bax = fig.add_axes([0.075, 0.15, 0.30, 0.15])   # 왼쪽 아래(기장군 경계 밖)
    bax.patch.set_facecolor((1, 1, 1, 0.9))
    xs = np.arange(len(DONGS)); bw = 0.8 / len(YEARS)
    for k, y in enumerate(YEARS):
        bax.bar(xs + (k - (len(YEARS) - 1) / 2) * bw, piv_all[y].values, bw,
                color="#d95f02" if y == yr else "#bdbdbd", edgecolor="white", label=YEAR_LABEL[y] if y == yr else None)
    bax.set_xticks(xs, DONGS, fontsize=FS["small"]); bax.tick_params(axis="y", labelsize=FS["small"] * 0.8)
    bax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:,.0f}"))
    bax.set_title("행정동별 생활인구 5개년 (주황=당해 연도)", fontsize=FS["small"], fontweight="bold")
    bax.spines[["top", "right"]].set_visible(False); bax.grid(axis="y", alpha=0.3)
    cax = fig.add_axes([0.2, 0.045, 0.6, 0.013])
    cb = fig.colorbar(ScalarMappable(dens_norm, dens_cmap), cax=cax, orientation="horizontal",
                      ticks=dens_bounds, spacing="uniform")
    cb.ax.set_xticklabels([f"{b:,.0f}" for b in dens_bounds], fontsize=FS["small"])
    cb.set_label("행정동 생활인구 밀도 (명/km²) · 5개년 공통 구간", fontsize=FS["legend"])
    footer(fig, SRC_NOTE3, FS["small"] * 0.8)
    save(fig, f"03_행정동별_인구분포_{yr}.png")

# ============================================================
# 10. ④ 연도별 행정동 생활인구 지도 — "3_행정구역별 인구분포_Wide.csv" 전용 (100m 격자 자료 미사용)
#     제공 값을 그대로 사용(연환산·가중 없음), 연도별 A1 PNG 1장씩
# ============================================================
print("▶ ④ 연도별 행정동 생활인구 지도 (Wide CSV)")
if not (INFLOW_WIDE_CSV and os.path.exists(INFLOW_WIDE_CSV)):
    raise FileNotFoundError(f"④ 지도용 자료가 없습니다: '{INFLOW_WIDE_CSV}' — 스크립트와 같은 폴더에 두거나 "
                            f"INFLOW_WIDE_CSV 경로를 지정하세요. (현재 작업 폴더: {os.getcwd()})")
for _enc in ("utf-8-sig", "cp949"):
    try:
        wd = pd.read_csv(INFLOW_WIDE_CSV, sep=None, engine="python", encoding=_enc); break
    except UnicodeDecodeError:
        continue
_yc = wd.columns[0]
wd["연도"] = wd[_yc].astype(str).str.extract(r"((?:19|20)\d{2})")[0].astype(int)
pw4 = wd.drop(columns=_yc).melt(id_vars="연도", var_name="dong", value_name="생활인구")
pw4["dong"] = pw4["dong"].map(norm_name)
pw4["생활인구"] = pd.to_numeric(pw4["생활인구"], errors="coerce")
pw4 = pw4[pw4["연도"].isin(YEARS)].merge(dong_poly[["dong", "면적_km2"]], on="dong", how="left")
_miss = sorted(set(pw4["dong"]) - set(dong_poly["dong"]))
if _miss:
    print(f"  [경고] 행정동 경계에 없는 이름: {_miss}")
pw4["밀도"] = pw4["생활인구"] / pw4["면적_km2"]
pw4["비중%"] = pw4["생활인구"] / pw4.groupby("연도")["생활인구"].transform("sum") * 100
pw4 = pw4.sort_values(["dong", "연도"])
pw4["전년대비%"] = pw4.groupby("dong")["생활인구"].pct_change() * 100
pw4.pivot(index="dong", columns="연도", values="생활인구").to_csv(
    os.path.join(OUTPUT_PATH, "행정동별_생활인구_연도별_WideCSV.csv"), encoding="utf-8-sig")

p4_norm = Normalize(vmin=pw4["생활인구"].min() * 0.9, vmax=pw4["생활인구"].max() * 1.03)   # 연도 공통 스케일
p4_cmap = plt.get_cmap(TEMP_CMAP)
SRC_NOTE4 = ("배경지도: 국토교통부 브이월드(VWorld) · 자료: 3_행정구역별 인구분포_Wide.csv "
             "(일별 행정동 유입지별 시간대 생활인구 연평균), 경계: 읍면동(EMD)")
for yr in YEARS:
    ds = pw4[pw4["연도"] == yr].set_index("dong")
    if ds["생활인구"].isna().all():
        continue
    ylab = YEAR_LABEL[yr]
    fig = new_sheet(f"기장군 {ylab} 행정동별 생활인구",
                    f"행정동 생활인구 연평균 (3_행정구역별 인구분포_Wide.csv, 제공 값 그대로)  |  "
                    f"기장군 합계 {fmt(ds['생활인구'].sum())}명")
    ax = base_axes(fig, MAP_RECT, EXTENT)
    add_vworld(ax, EXTENT, AX_PX, VW_LAYER_CHORO)
    d = dong3857.merge(ds[["생활인구", "밀도", "비중%", "전년대비%"]], left_on="dong", right_index=True, how="left")
    d.plot(ax=ax, column="생활인구", cmap=p4_cmap, norm=p4_norm, alpha=0.68, linewidth=0, zorder=3,
           missing_kwds={"color": "#dddddd", "alpha": 0.5})
    draw_boundary(ax, emd3857)
    def lab4(r):
        s_ = f"{r['dong']}\n{fmt(r['생활인구'])}명 ({r['비중%']:.1f}%)\n{fmt(r['밀도'])}명/km²"
        if pd.notna(r["전년대비%"]):
            s_ += f"\n전년比 {r['전년대비%']:+.1f}%"
        return s_
    label_dongs(ax, d, lab4, FS["label"] * 1.1)
    add_scalebar(ax, EXTENT, lat_c, FS["small"]); add_north(ax, EXTENT, FS["label"])
    # 행정동 표
    cell = [[dn, fmt(ds.loc[dn, "생활인구"]), f"{ds.loc[dn, '비중%']:.1f}", fmt(ds.loc[dn, "밀도"]),
             "-" if pd.isna(ds.loc[dn, "전년대비%"]) else f"{ds.loc[dn, '전년대비%']:+.1f}%"]
            for dn in DONGS if dn in ds.index]
    cell.append(["합계", fmt(ds["생활인구"].sum()), "100.0",
                 fmt(ds["생활인구"].sum() / dong_poly["면적_km2"].sum()), "-"])
    tax = fig.add_axes([0.58, 0.09, 0.37, 0.022 * (len(cell) + 1)]); tax.axis("off")
    t = tax.table(cellText=cell, colLabels=["행정동", "생활인구(명)", "비중(%)", "밀도(명/km²)", "전년比"],
                  loc="center", cellLoc="center", bbox=[0, 0, 1, 1])
    t.auto_set_font_size(False); t.set_fontsize(FS["small"])
    for (r_, c_), cl in t.get_celld().items():
        cl.set_edgecolor("#888"); cl.set_facecolor("#e8eef7" if r_ == 0 else (1, 1, 1, 0.92))
        if r_ == 0 or r_ == len(cell):
            cl.get_text().set_fontweight("bold")
    cax = fig.add_axes([0.2, 0.045, 0.6, 0.013])
    cb = fig.colorbar(ScalarMappable(p4_norm, p4_cmap), cax=cax, orientation="horizontal")
    cb.ax.tick_params(labelsize=FS["small"])
    cb.ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:,.0f}"))
    cb.set_label("행정동 생활인구 (명)  ◀ 낮음 ─ 높음 ▶  · 연도 공통 스케일", fontsize=FS["legend"])
    footer(fig, SRC_NOTE4, FS["small"] * 0.8)
    save(fig, f"04_행정동별_생활인구_{yr}.png")
print("완료")
