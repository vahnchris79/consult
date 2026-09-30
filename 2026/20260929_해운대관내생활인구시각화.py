# -*- coding: utf-8 -*-
"""
해운대 관내 행정동별·시간대별 생활인구 밀집도 시각화
===================================================

입력
  1) 생활인구 CSV  : '해운대 관내 시간대 생활인구 현황.csv'
                    (구분자 '|', 컬럼 month|weekday|hname|id|14H|15H|16H,
                     시간대별 값이 서로 다른 행에 나뉘어 있음 → 자동 합산)
  2) GeoPackage    : '해운대 관내 생활인구 이동패턴 분석.gpkg'
       - 행정경계   : 행정동 경계 (폴리곤)
       - 보행자도로 : 보행자도로 (라인/폴리곤)
       - GRID100M   : 100m 격자 (국가지점번호 격자, 예: '마라470896')

  3) 배경지도      : 브이월드(VWorld) WMTS 'Base' 타일
                    - 인증키: --vworld-key 또는 환경변수 VWORLD_API_KEY
                    - 키 발급: https://www.vworld.kr (오픈API > 인증키 발급)

출력 (--out-dir, 기본 ./output)
  - 밀집도_<행정동>_<요일>_<시간>_<기간>.png : 행정동·요일·시간대별 지도 1장씩
    (예: 2개 동 × 토·일 × 14·15·16시 = 12장, 같은 동은 동일 색상 구간)
  - 시간대별_총생활인구_<기간>.png : 행정동·요일별 시간대 총량 비교

사용 예
  python haeundae_population_density.py \
      --csv "해운대 관내 시간대 생활인구 현황.csv" \
      --gpkg "해운대 관내 생활인구 이동패턴 분석.gpkg" \
      --vworld-key 발급받은_인증키
  # 월별 이미지도 함께 생성
  python haeundae_population_density.py --csv ... --gpkg ... --by-month

필요 패키지: pip install geopandas pyogrio matplotlib pandas numpy requests pillow
"""
from __future__ import annotations

import argparse
import io
import math
import os
import re
import sys
import warnings
from pathlib import Path

import geopandas as gpd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker
import numpy as np
import pandas as pd
from matplotlib import font_manager
from matplotlib.colors import BoundaryNorm, ListedColormap
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from shapely.geometry import box

try:
    import requests
    from PIL import Image
except ImportError:  # 배경지도 없이도 동작하도록
    requests = None
    Image = None

warnings.filterwarnings("ignore", category=UserWarning)

# ============================================================================
# ★ 사용자 설정 — 여기만 수정하면 됩니다 ★
#   (Windows 경로는 앞에 r 을 붙여 r"C:\폴더\파일.csv" 처럼 쓰세요)
#   명령줄 옵션(--csv, --gpkg, --out-dir, --vworld-key)을 주면 그 값이 우선합니다.
# ============================================================================
WORK_PATH = r"D:/04_자료제출/2026년/김미애 국회의원 자료요청/"
CSV_PATH = WORK_PATH + r"집계결과/해운대 관내 시간대 생활인구 현황.csv"        # 생활인구 CSV 파일
GPKG_PATH = WORK_PATH + r"해운대 관내 생활인구 이동패턴 분석.gpkg"             # GeoPackage 파일
OUTPUT_DIR = WORK_PATH + r"PNG/"    # 결과 이미지 저장 폴더
VWORLD_KEY = "A991416E-F2EE-3959-99F3-C71FFC190B72"                                            # 브이월드 인증키 (비워두면 환경변수 VWORLD_API_KEY 사용)

# gpkg 레이어 이름
BOUNDARY_LAYER = "행정동경계"
ROAD_LAYER = "보행자도로"
GRID_LAYER = "GRID100M"

BY_MONTH = False         # True: 6~8월 평균 외에 월별 이미지도 생성

# ----------------------------------------------------------------------------
# 기본 설정
# ----------------------------------------------------------------------------
HOURS = ["14H", "15H", "16H"]
HOUR_LABEL = {"14H": "14시", "15H": "15시", "16H": "16시"}
WEEKDAYS = ["토요일", "일요일"]
DEFAULT_CRS = "EPSG:5179"          # 국가지점번호 격자 기준 좌표계 (UTM-K)
GRID_ID_PATTERN = re.compile(r"^[가-힣]{2}\d{6}$")

# 단일 색상(주황-적색) 순차 팔레트: 밝음 = 낮은 밀도, 어두움 = 높은 밀도
# (브이월드 Base 지도의 파란 수계·녹지와 구분되도록 난색 계열 사용)
SEQ_RAMP = ["#ffe3b8", "#fdbf6f", "#fb9a3c", "#f0701a",
            "#d24d0c", "#a8330a", "#751f06"]
ZERO_COLOR = "#bdbdb8"             # 생활인구 0 격자
ROAD_COLOR = "#3d3d3a"             # 보행자도로 (배경지도 도로와 구분되는 짙은 회색)
BOUNDARY_COLOR = "#111111"
CONTEXT_EDGE = "#6b6b68"           # 인접 행정동 경계선

# 투명도: 격자 아래 배경지도(도로·건물·지명)가 비쳐 보이는 수준
GRID_ALPHA = 0.60                  # 생활인구 > 0 격자
ZERO_ALPHA = 0.25                  # 생활인구 0 격자

# 브이월드 WMTS (Web Mercator, EPSG:3857 타일)
VWORLD_URL = "https://api.vworld.kr/req/wmts/1.0.0/{key}/{layer}/{z}/{y}/{x}.{ext}"
WEB_MERCATOR = "EPSG:3857"
R_MERC = 6378137.0
TEXT = "#222222"
TEXT_MUTED = "#6b6b68"

# ----------------------------------------------------------------------------
# 유틸
# ----------------------------------------------------------------------------
def set_korean_font() -> None:
    """OS에 설치된 한글 폰트를 찾아 matplotlib 기본 폰트로 지정."""
    candidates = ["Malgun Gothic", "맑은 고딕", "AppleGothic", "Apple SD Gothic Neo",
                  "NanumGothic", "나눔고딕", "NanumBarunGothic",
                  "Noto Sans CJK KR", "Noto Sans KR", "Noto Sans CJK JP"]
    installed = {f.name for f in font_manager.fontManager.ttflist}
    for name in candidates:
        if name in installed:
            plt.rcParams["font.family"] = name
            break
    else:
        print("[경고] 한글 폰트를 찾지 못했습니다. 글자가 깨질 수 있습니다.")
    plt.rcParams["axes.unicode_minus"] = False


def read_text_table(path: Path, sep: str) -> pd.DataFrame:
    for enc in ("utf-8-sig", "cp949", "euc-kr"):
        try:
            return pd.read_csv(path, sep=sep, encoding=enc, dtype=str)
        except UnicodeDecodeError:
            continue
    raise ValueError(f"CSV 인코딩을 판별할 수 없습니다: {path}")


def find_column(gdf: gpd.GeoDataFrame, predicate, prefer: list[str] | None = None) -> str | None:
    """predicate(series)->일치율 이 가장 높은 컬럼명 반환."""
    cols = [c for c in gdf.columns if c != gdf.geometry.name]
    if prefer:
        cols = [c for c in prefer if c in cols] + [c for c in cols if c not in prefer]
    best, best_score = None, 0.0
    for c in cols:
        s = gdf[c].dropna().astype(str)
        if s.empty:
            continue
        score = predicate(s)
        if score > best_score:
            best, best_score = c, score
    return best if best_score > 0 else None


def safe_name(s: str) -> str:
    return re.sub(r'[\\/:*?"<>|\s]+', "_", s).strip("_")

# ----------------------------------------------------------------------------
# 1. 생활인구 CSV 로드 및 정리
# ----------------------------------------------------------------------------
def load_population(csv_path: Path) -> pd.DataFrame:
    """long 형태 반환: month, weekday, hname, id, hour, pop"""
    df = read_text_table(csv_path, sep="|")
    df.columns = [c.strip() for c in df.columns]
    need = {"month", "weekday", "hname", "id", *HOURS}
    missing = need - set(df.columns)
    if missing:
        raise ValueError(f"CSV에 필요한 컬럼이 없습니다: {missing}")

    for c in ["month", "weekday", "hname", "id"]:
        df[c] = df[c].astype(str).str.strip()
    for h in HOURS:
        df[h] = pd.to_numeric(df[h], errors="coerce")

    # 중간에 끼어 있는 헤더 행(예: '06month|weekday|...') 등 비정상 행 제거
    df = df.dropna(subset=HOURS, how="all")
    df = df[df["id"].str.match(GRID_ID_PATTERN)]

    long = df.melt(id_vars=["month", "weekday", "hname", "id"],
                   value_vars=HOURS, var_name="hour", value_name="pop")
    # 시간대별 값이 서로 다른 행에 분리되어 있으므로 합산해 1행으로 통합
    long = (long.groupby(["month", "weekday", "hname", "id", "hour"], as_index=False)["pop"]
                .sum(min_count=1).fillna(0))
    print(f"[CSV] 행정동 {sorted(long.hname.unique())}, 월 {sorted(long.month.unique())}, "
          f"요일 {sorted(long.weekday.unique())}, 격자 {long.id.nunique():,}개")
    return long


def period_tables(long: pd.DataFrame, by_month: bool) -> dict[str, pd.DataFrame]:
    """{기간라벨: DataFrame(weekday,hname,id,hour,pop)}"""
    months = sorted(long["month"].unique())
    label = f"{months[0]}~{months[-1]} 평균" if len(months) > 1 else months[0]
    out = {label: (long.groupby(["weekday", "hname", "id", "hour"], as_index=False)["pop"].mean())}
    if by_month:
        for m in months:
            out[m] = long[long["month"] == m].drop(columns="month")
    return out

# ----------------------------------------------------------------------------
# 2. GeoPackage 레이어 로드
# ----------------------------------------------------------------------------
def grid_from_ids(ids) -> gpd.GeoDataFrame:
    """국가지점번호(100m) → EPSG:5179 격자 폴리곤 (GRID100M 조인 실패 시 대체용)."""
    letters = "가나다라마바사아"
    geoms, keep = [], []
    for gid in ids:
        try:
            x0 = 700000 + letters.index(gid[0]) * 100000 + int(gid[2:5]) * 100
            y0 = 1300000 + letters.index(gid[1]) * 100000 + int(gid[5:8]) * 100
        except (ValueError, IndexError):
            continue
        geoms.append(box(x0, y0, x0 + 100, y0 + 100))
        keep.append(gid)
    return gpd.GeoDataFrame({"id": keep}, geometry=geoms, crs=DEFAULT_CRS)


def load_layers(gpkg: Path, args, csv_ids: set[str], dong_names: list[str]):
    layers = gpd.list_layers(gpkg)["name"].tolist() if hasattr(gpd, "list_layers") else None
    if layers is not None:
        print(f"[GPKG] 레이어: {layers}")
        for lyr in (args.boundary_layer, args.road_layer, args.grid_layer):
            if lyr not in layers:
                raise ValueError(f"'{lyr}' 레이어가 없습니다. --*-layer 옵션으로 이름을 지정하세요.")

    grid = gpd.read_file(gpkg, layer=args.grid_layer)
    bnd = gpd.read_file(gpkg, layer=args.boundary_layer)
    roads = gpd.read_file(gpkg, layer=args.road_layer)

    for name, g in (("GRID100M", grid), ("행정경계", bnd), ("보행자도로", roads)):
        if g.crs is None:
            print(f"[경고] {name} 레이어 좌표계 정보가 없어 {DEFAULT_CRS}로 가정합니다.")
            g.set_crs(DEFAULT_CRS, inplace=True)
    target_crs = grid.crs
    bnd, roads = bnd.to_crs(target_crs), roads.to_crs(target_crs)

    # --- 격자 ID 컬럼 자동 탐지 (CSV id 와 가장 많이 일치하는 컬럼)
    id_col = args.grid_id_col or find_column(
        grid, lambda s: s.str.strip().isin(csv_ids).mean(),
        prefer=["gid", "GID", "id", "ID", "grid_id", "GRID_ID"])
    matched = 0
    if id_col:
        grid = grid.rename(columns={id_col: "id"}) if id_col != "id" else grid
        grid["id"] = grid["id"].astype(str).str.strip()
        grid = grid[grid["id"].isin(csv_ids)][["id", "geometry"]].dissolve("id").reset_index()
        matched = len(grid)
    print(f"[GRID100M] ID 컬럼='{id_col}', CSV 격자 {len(csv_ids):,}개 중 {matched:,}개 매칭")
    if matched < 0.5 * len(csv_ids):
        print("[경고] 격자 매칭률이 낮아 국가지점번호로 격자를 직접 생성합니다.")
        grid = grid_from_ids(csv_ids).to_crs(target_crs)

    # --- 행정동 이름 컬럼 자동 탐지
    dong_col = args.dong_col or find_column(
        bnd, lambda s: np.mean([s.str.contains(d, regex=False).any() for d in dong_names]),
        prefer=["ADM_NM", "adm_nm", "EMD_KOR_NM", "HJD_NM", "hname", "dong", "행정동명"])
    if not dong_col:
        raise ValueError("행정경계 레이어에서 행정동 이름 컬럼을 찾지 못했습니다. --dong-col 로 지정하세요.")
    bnd["dong"] = bnd[dong_col].astype(str).str.split().str[-1]   # '부산광역시 해운대구 반여1동' → '반여1동'
    print(f"[행정경계] 이름 컬럼='{dong_col}', 피처 {len(bnd)}개")

    roads = roads[~roads.geometry.is_empty & roads.geometry.notna()]
    print(f"[보행자도로] 피처 {len(roads):,}개")
    return grid, bnd, roads


# ----------------------------------------------------------------------------
# 3. 브이월드 배경지도
# ----------------------------------------------------------------------------
class VWorldBasemap:
    """브이월드 WMTS 타일을 받아 하나의 이미지로 합성 (EPSG:3857).

    타일은 cache_dir 에 저장해 재실행 시 다시 받지 않습니다.
    """

    def __init__(self, key: str, layer: str = "Base", cache_dir: Path | None = None,
                 domain: str | None = None, max_zoom: int = 19):
        self.key, self.layer, self.max_zoom = key, layer, max_zoom
        self.ext = "jpeg" if layer.lower() == "satellite" else "png"
        self.cache_dir = cache_dir
        if cache_dir:
            cache_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers["User-Agent"] = "Mozilla/5.0 (haeundae_population_density)"
        if domain:  # 인증키 발급 시 등록한 서비스 URL (필요한 경우)
            self.session.headers["Referer"] = domain

    @staticmethod
    def _tile_range(bounds, z):
        n = 2 ** z
        size = 2 * math.pi * R_MERC / n
        minx, miny, maxx, maxy = bounds
        x0 = int((minx + math.pi * R_MERC) // size)
        x1 = int((maxx + math.pi * R_MERC) // size)
        y0 = int((math.pi * R_MERC - maxy) // size)
        y1 = int((math.pi * R_MERC - miny) // size)
        return x0, x1, y0, y1, size

    def _fetch(self, z, x, y):
        cache = self.cache_dir / f"{self.layer}_{z}_{x}_{y}.{self.ext}" if self.cache_dir else None
        if cache and cache.exists():
            return Image.open(cache).convert("RGB")
        url = VWORLD_URL.format(key=self.key, layer=self.layer, z=z, x=x, y=y, ext=self.ext)
        r = self.session.get(url, timeout=15)
        ctype = r.headers.get("Content-Type", "")
        if r.status_code != 200 or "image" not in ctype:
            msg = r.text[:200].replace("\n", " ") if "image" not in ctype else ""
            raise RuntimeError(f"HTTP {r.status_code} {msg}")
        if cache:
            cache.write_bytes(r.content)
        return Image.open(io.BytesIO(r.content)).convert("RGB")

    def image(self, bounds, target_px: int = 1000):
        """bounds(EPSG:3857) 영역 이미지와 imshow extent 반환."""
        width = bounds[2] - bounds[0]
        z = math.ceil(math.log2(2 * math.pi * R_MERC * target_px / (256 * width)))
        z = max(6, min(self.max_zoom, z))
        x0, x1, y0, y1, size = self._tile_range(bounds, z)
        if (x1 - x0 + 1) * (y1 - y0 + 1) > 400:
            raise RuntimeError("요청 타일 수가 너무 많습니다.")
        mosaic = Image.new("RGB", ((x1 - x0 + 1) * 256, (y1 - y0 + 1) * 256), "white")
        for x in range(x0, x1 + 1):
            for y in range(y0, y1 + 1):
                mosaic.paste(self._fetch(z, x, y), ((x - x0) * 256, (y - y0) * 256))
        left = -math.pi * R_MERC + x0 * size
        top = math.pi * R_MERC - y0 * size
        extent = (left, left + (x1 - x0 + 1) * size, top - (y1 - y0 + 1) * size, top)
        print(f"  [배경지도] 브이월드 {self.layer} z={z}, 타일 {(x1-x0+1)*(y1-y0+1)}장")
        return np.asarray(mosaic), extent


# ----------------------------------------------------------------------------
# 4. 시각화
# ----------------------------------------------------------------------------
def class_breaks(values: np.ndarray, n: int) -> np.ndarray:
    """0 초과 값의 분위수 기반 구간 (보기 좋은 정수로 반올림)."""
    v = values[values > 0]
    if v.size == 0:
        return np.array([0, 1])
    qs = np.quantile(v, np.linspace(0, 1, n + 1))
    qs[0] = 0
    step = 10 if qs[-1] > 200 else 1
    qs[1:-1] = np.round(qs[1:-1] / step) * step
    qs[-1] = np.ceil(qs[-1] / step) * step
    return np.unique(qs)


def plot_dong(dong, table, grid, bnd, roads, period, out_dir: Path, dpi: int,
              basemap: VWorldBasemap | None = None) -> list[Path]:
    """행정동 1곳에 대해 요일 × 시간대 조합마다 지도 이미지 1장씩 생성.

    같은 행정동의 이미지들은 동일한 색상 구간을 사용하므로 서로 비교할 수 있습니다.
    """
    sel = bnd[bnd["dong"] == dong]
    if sel.empty:
        print(f"[경고] 행정경계에서 '{dong}'을 찾지 못해 격자 범위로 표시합니다.")
    data = table[table["hname"] == dong]
    gdf = grid.merge(data, on="id", how="inner")
    gdf["area_ha"] = gdf.geometry.area / 10_000
    gdf["density"] = gdf["pop"] / gdf["area_ha"].where(gdf["area_ha"] > 0, 1)   # 명/ha

    # 배경지도 타일 좌표계(EPSG:3857)로 변환 (밀도는 원 좌표계 면적으로 계산 완료)
    if basemap is not None:
        gdf, sel, bnd, roads = (g.to_crs(WEB_MERCATOR) for g in (gdf, sel, bnd, roads))

    extent_geom = sel.union_all() if not sel.empty else gdf.union_all()
    extent_geom = extent_geom.union(gdf.union_all())
    minx, miny, maxx, maxy = extent_geom.bounds
    pad = max(maxx - minx, maxy - miny) * 0.04
    view = box(minx - pad, miny - pad, maxx + pad, maxy + pad)

    ctx = bnd[bnd.intersects(view) & (bnd["dong"] != dong)]
    rd = roads[roads.intersects(view)].clip(view)

    # 배경지도는 행정동마다 한 번만 받아서 모든 이미지에 재사용
    map_w = 8.0                                         # 지도 가로 크기 (inch)
    bg = None
    if basemap is not None:
        try:
            bg = basemap.image(view.bounds, target_px=int(map_w * dpi))
        except Exception as e:  # 인증키 오류, 네트워크 문제 등
            print(f"  [경고] 브이월드 배경지도를 불러오지 못했습니다: {e}")

    # 행정동 내 모든 요일·시간대에 공통 색상 구간 적용
    breaks = class_breaks(gdf["density"].to_numpy(), len(SEQ_RAMP))
    ncls = len(breaks) - 1
    cmap = ListedColormap(SEQ_RAMP[-ncls:] if ncls < len(SEQ_RAMP) else SEQ_RAMP)
    norm = BoundaryNorm(breaks, cmap.N)

    handles = [Patch(facecolor=cmap(i), alpha=GRID_ALPHA, edgecolor="none",
                     label=f"{breaks[i]:,.0f} – {breaks[i + 1]:,.0f}") for i in range(ncls)]
    handles.insert(0, Patch(facecolor=ZERO_COLOR, alpha=ZERO_ALPHA, edgecolor="#9a9a96", label="0"))
    ref = [Line2D([], [], color=BOUNDARY_COLOR, lw=1.4, label=f"{dong} 경계"),
           Line2D([], [], color=ROAD_COLOR, lw=1, label="보행자도로"),
           Line2D([], [], color=CONTEXT_EDGE, lw=0.8, ls=(0, (4, 2)), label="인접 행정동 경계")]

    vx0, vy0, vx1, vy1 = view.bounds
    map_h = map_w * (vy1 - vy0) / (vx1 - vx0)          # 지도 비율에 맞춘 높이
    top_in, bottom_in = 1.0, 1.5                        # 제목 / 범례 영역 (inch)
    fig_h = map_h + top_in + bottom_in

    weekdays = [w for w in WEEKDAYS if w in set(gdf["weekday"])]
    outputs = []
    for wd in weekdays:
        for hr in HOURS:
            sub = gdf[(gdf["weekday"] == wd) & (gdf["hour"] == hr)]
            fig = plt.figure(figsize=(map_w + 0.4, fig_h))
            ax = fig.add_axes([0.2 / (map_w + 0.4), bottom_in / fig_h,
                               map_w / (map_w + 0.4), map_h / fig_h])

            if bg is not None:
                ax.imshow(bg[0], extent=bg[1], interpolation="bilinear", zorder=0)
            if not ctx.empty:
                ctx.boundary.plot(ax=ax, color=CONTEXT_EDGE, linewidth=0.8,
                                  linestyle=(0, (4, 2)), zorder=1)
            zero, pos = sub[sub["density"] <= 0], sub[sub["density"] > 0]
            if not zero.empty:
                zero.plot(ax=ax, color=ZERO_COLOR, alpha=ZERO_ALPHA, edgecolor="none", zorder=2)
            if not pos.empty:
                pos.plot(ax=ax, column="density", cmap=cmap, norm=norm, alpha=GRID_ALPHA,
                         edgecolor=(1, 1, 1, 0.5), linewidth=0.3, zorder=3)
            if not rd.empty:
                rd.plot(ax=ax, color=ROAD_COLOR, linewidth=0.6, alpha=0.7, zorder=4)
            if not sel.empty:
                sel.boundary.plot(ax=ax, color=BOUNDARY_COLOR, linewidth=1.6, zorder=5)
            ax.set_xlim(vx0, vx1)
            ax.set_ylim(vy0, vy1)
            ax.set_aspect("equal")
            ax.set_axis_off()

            # 제목
            total = sub["pop"].sum()
            peak = sub["density"].max() if not sub.empty else 0
            fig.text(0.025, 1 - 0.35 / fig_h, f"{dong} {wd} {HOUR_LABEL[hr]} 생활인구 밀집도",
                     fontsize=16, color=TEXT, va="center")
            fig.text(0.025, 1 - 0.75 / fig_h,
                     f"{period}  ·  총 {total:,.0f}명  ·  최고 {peak:,.0f}명/ha",
                     fontsize=10.5, color=TEXT_MUTED, va="center")

            # 범례
            leg = fig.legend(handles=handles, title="생활인구 밀도 (명/ha, 100m 격자)",
                             loc="upper left", bbox_to_anchor=(0.02, (bottom_in - 0.1) / fig_h),
                             ncol=math.ceil(len(handles) / 2), frameon=False, fontsize=9,
                             title_fontsize=10, handlelength=1.6, columnspacing=1.2)
            leg._legend_box.align = "left"
            fig.legend(handles=ref, loc="lower left", bbox_to_anchor=(0.02, 0.02 / fig_h * 10),
                       ncol=3, frameon=False, fontsize=9)
            if bg is not None:
                fig.text(0.98, 0.1 / fig_h * 2, "배경지도: 브이월드(VWorld) Base © 국토교통부",
                         ha="right", fontsize=8, color=TEXT_MUTED)

            out = out_dir / (f"밀집도_{safe_name(dong)}_{wd}_{HOUR_LABEL[hr]}_"
                             f"{safe_name(period)}.png")
            fig.savefig(out, dpi=dpi, facecolor="white")
            plt.close(fig)
            outputs.append(out)
    return outputs


def plot_summary(table, period, out_dir: Path, dpi: int) -> Path:
    """행정동별·요일별 시간대 총 생활인구 (보조 차트)."""
    agg = table.groupby(["hname", "weekday", "hour"])["pop"].sum().reset_index()
    dongs = sorted(agg["hname"].unique())
    colors = {"토요일": "#2a78d6", "일요일": "#e8743b"}
    fig, axes = plt.subplots(1, len(dongs), figsize=(5.2 * len(dongs), 4), squeeze=False)
    x = np.arange(len(HOURS))
    for ax, dong in zip(axes[0], dongs):
        for wd in WEEKDAYS:
            s = agg[(agg.hname == dong) & (agg.weekday == wd)].set_index("hour").reindex(HOURS)["pop"]
            if s.isna().all():
                continue
            ax.plot(x, s.values, color=colors[wd], lw=2, marker="o", ms=8,
                    markeredgecolor="white", markeredgewidth=2, label=wd)
            ax.annotate(f"{s.values[-1]:,.0f}", (x[-1], s.values[-1]), xytext=(8, 0),
                        textcoords="offset points", va="center", fontsize=9, color=TEXT)
        ax.set_xticks(x, [HOUR_LABEL[h] for h in HOURS])
        ax.set_xlim(-0.3, len(HOURS) - 0.4)
        ax.set_title(dong, loc="left", fontsize=13, color=TEXT)
        ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:,.0f}"))
        ax.grid(axis="y", color="#e6e6e3", lw=0.8)
        for sp in ("top", "right", "left"):
            ax.spines[sp].set_visible(False)
        ax.tick_params(colors=TEXT_MUTED, length=0)
        ax.set_ylabel("총 생활인구 (명)", color=TEXT_MUTED)
    fig.suptitle(f"행정동별 시간대 총 생활인구 ({period})", x=0.02, ha="left", fontsize=15, color=TEXT)
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper right", ncol=2, frameon=False, bbox_to_anchor=(0.98, 1.0))
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    out = out_dir / f"시간대별_총생활인구_{safe_name(period)}.png"
    fig.savefig(out, dpi=dpi, facecolor="white")
    plt.close(fig)
    return out


# ----------------------------------------------------------------------------
# main
# ----------------------------------------------------------------------------
def _in_notebook() -> bool:
    try:
        from IPython import get_ipython
        return get_ipython() is not None and "IPKernelApp" in get_ipython().config
    except Exception:
        return False


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="행정동별 시간대별 생활인구 밀집도 지도 생성")
    p.add_argument("--csv", default=CSV_PATH)
    p.add_argument("--gpkg", default=GPKG_PATH)
    p.add_argument("--boundary-layer", default=BOUNDARY_LAYER)
    p.add_argument("--road-layer", default=ROAD_LAYER)
    p.add_argument("--grid-layer", default=GRID_LAYER)
    p.add_argument("--grid-id-col", help="GRID100M 의 격자 ID 컬럼 (미지정 시 자동 탐지)")
    p.add_argument("--dong-col", help="행정경계 의 행정동명 컬럼 (미지정 시 자동 탐지)")
    p.add_argument("--out-dir", default=OUTPUT_DIR)
    p.add_argument("--by-month", action="store_true", default=BY_MONTH,
                   help="월별 이미지도 추가 생성")
    p.add_argument("--dpi", type=int, default=200)
    p.add_argument("--vworld-key", default=VWORLD_KEY or os.environ.get("VWORLD_API_KEY"),
                   help="브이월드 인증키 (미지정 시 환경변수 VWORLD_API_KEY)")
    p.add_argument("--vworld-layer", default="Base",
                   help="브이월드 WMTS 레이어 (Base, white, midnight, Hybrid, Satellite)")
    p.add_argument("--vworld-domain", help="인증키 발급 시 등록한 서비스 URL (Referer 헤더로 전송)")
    p.add_argument("--tile-cache", default=".vworld_cache", help="타일 캐시 폴더")
    p.add_argument("--no-basemap", action="store_true", help="배경지도 없이 생성")
    if argv is None and _in_notebook():
        argv = []                     # 주피터 커널 인자(-f ...) 무시
    args, _ = p.parse_known_args(argv)

    set_korean_font()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    long = load_population(Path(args.csv))
    dongs = sorted(long["hname"].unique())
    grid, bnd, roads = load_layers(Path(args.gpkg), args, set(long["id"]), dongs)

    basemap = None
    if not args.no_basemap:
        if requests is None or Image is None:
            print("[경고] requests / pillow 가 없어 배경지도 없이 생성합니다.")
        elif not args.vworld_key:
            print("[경고] 브이월드 인증키가 없어 배경지도 없이 생성합니다. "
                  "(--vworld-key 또는 환경변수 VWORLD_API_KEY)")
        else:
            basemap = VWorldBasemap(args.vworld_key, args.vworld_layer,
                                    Path(args.tile_cache), args.vworld_domain)

    for period, table in period_tables(long, args.by_month).items():
        for dong in dongs:
            for out in plot_dong(dong, table, grid, bnd, roads, period, out_dir,
                                 args.dpi, basemap):
                print("  생성:", out)
        print("  생성:", plot_summary(table, period, out_dir, args.dpi))
    print("완료")
    return 0


if __name__ == "__main__":
    if _in_notebook():
        main()                        # 주피터랩 셀에서 실행 (sys.exit 로 커널 경고가 나지 않도록)
    else:
        sys.exit(main())
