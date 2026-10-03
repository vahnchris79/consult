import glob
import os
import threading
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed

import geopandas as gpd
import numpy as np
import pandas as pd
import requests
from dotenv import load_dotenv
from pyproj import Transformer

warnings.filterwarnings('ignore')
pd.set_option("display.max_rows", 100)

DATA_PATH = r"D:\\02_사업관리\\03_분석컨설팅\\2026년\\20260902_도시계획과\\02_자료수집\\"
GPKG_PATH = DATA_PATH + r"2026-018_도시계획과.gpkg"
CACHE_PATH = DATA_PATH + r"02_산업경제\\지오코딩_캐시_5179.csv"
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "env"))
VWORLD_KEY = os.environ["VWORLD_API_KEY"]
VWORLD_URL = "https://api.vworld.kr/req/address"
MAX_WORKERS = 8
RETRY_FAILED = False    # True: 캐시에 실패(NaN)로 기록된 주소도 다시 요청
SAVE_EVERY = 500        # 요청 N건마다 캐시 저장

to_wgs84 = Transformer.from_crs("EPSG:5179", "EPSG:4326", always_xy=True)
session = requests.Session()
cache_lock = threading.Lock()


class QuotaError(Exception):
    """인증키 오류·일일 한도 초과 등 계속 진행할 수 없는 응답"""


# ---------------------------------------------------------------------------
# 법정동 기준표 (GPKG의 GIS건물통합정보 '법정동명' 사용)
# ---------------------------------------------------------------------------
def load_legal_dong(layer="GIS건물통합정보2024C"):
    names = (gpd.read_file(GPKG_PATH, layer=layer, columns=["법정동명"], ignore_geometry=True)["법정동명"]
             .dropna().drop_duplicates().str.split())
    ref = pd.DataFrame({"구군": names.str[1], "법정동": names.str[2:].str.join(" "), "리": names.str[-1]})
    valid = set(zip(ref["구군"], ref["법정동"]))
    # 기장군: 리 이름 → '읍면 리' (정관면 → 정관읍처럼 현재 명칭으로 맞춤)
    gj = ref[ref["구군"] == "기장군"].drop_duplicates("리", keep=False).set_index("리")["법정동"]
    return valid, gj


def to_legal_dong(gu, dong, road_raw, valid, gj):
    """행정동 → 법정동.
    ① 이미 법정동이면 그대로 ② 원본 도로명 괄호 속 참고동 ③ 숫자 제거(당감2동 → 당감동)
    순으로 법정동 목록에 있는 첫 값을 쓰고, 모두 해당 없으면 원래 값 유지"""
    is_gj = gu.eq("기장군")
    paren = road_raw.str.extract(r"\(([^,)]+)")[0].str.strip()
    candidates = [
        dong.where(~is_gj, dong.str.split().str[-1].map(gj)),
        paren.where(~is_gj, paren.map(gj)),
        dong.str.replace(r"^(\D+?)\d+동$", r"\1동", regex=True),
    ]
    legal = pd.Series(np.nan, index=dong.index, dtype=object)
    for c in candidates:
        ok = pd.Series([(g, d) in valid for g, d in zip(gu, c)], index=dong.index)
        legal = legal.where(legal.notna() | ~ok, c)
    return legal.fillna(dong)


# ---------------------------------------------------------------------------
# 주소 전처리
# ---------------------------------------------------------------------------
def preprocess(df, valid_dong, gj_dong):
    """주소_지번(법정동 기준)·주소_도로명을 정리한 사본을 반환. 두 주소가 모두 없는 행은 제외"""
    df0 = df.copy()

    # 주소_지번: 시도 구군 법정동(기장군은 읍면 리) 번지
    addr = df0['주소_지번'].fillna('').str.split()
    is_gj = df0['주소_지번'].str.contains('기장군', na=False)
    sido = addr.str[0].replace({'부산시': '부산', '부산광역시': '부산'})
    gugun = addr.str[1]
    dong = addr.str[2].where(~is_gj, addr.str[2:4].str.join(' '))
    dong = to_legal_dong(gugun, dong, df['주소_도로명'], valid_dong, gj_dong)
    bunji = addr.str[3].where(~is_gj, addr.str[4]).str.extract(r'^((?:산)?\d+(?:-\d+)?)')[0]
    df0['주소_지번'] = sido + ' ' + gugun + ' ' + dong + ' ' + bunji

    # 주소_도로명: 시도 구군 [읍면] 도로명 [지하] 건물번호 까지만 남기고 층·호수·(참고항목) 제거
    road = (df0['주소_도로명'].str.replace(r'^\s*기타\s*', '', regex=True)
            .str.replace(r'\s+', ' ', regex=True).str.strip()
            .str.extract(r'^(?P<시도>\S+) (?P<구군>\S+[구군]) (?:(?P<읍면>\S+[읍면]) )?'
                         r'(?P<도로명>\S+(?:로|길)) ?(?P<지하>지하 )?(?P<건물번호>\d+(?:-\d+)?)?'))
    road['시도'] = road['시도'].replace({'부산시': '부산', '부산광역시': '부산'})
    bldg = road['지하'].fillna('') + road['건물번호']
    df0['주소_도로명'] = (road['시도'] + ' ' + road['구군'] + ' ' + (road['읍면'] + ' ').fillna('')
                          + road['도로명'] + (' ' + bldg).fillna(''))

    return df0.dropna(subset=['주소_지번', '주소_도로명'], how='all')


# ---------------------------------------------------------------------------
# 캐시
# ---------------------------------------------------------------------------
def load_cache():
    if not os.path.exists(CACHE_PATH):
        return {}
    df = pd.read_csv(CACHE_PATH, encoding="utf-8-sig")
    if RETRY_FAILED:
        df = df.dropna(subset=["x", "y"])
    return {(r.주소, r.구분): (r.x, r.y) for r in df.itertuples(index=False)}


def save_cache(cache):
    with cache_lock:
        rows = [(a, t, x, y) for (a, t), (x, y) in cache.items()]
    pd.DataFrame(rows, columns=["주소", "구분", "x", "y"]).to_csv(CACHE_PATH, index=False, encoding="utf-8-sig")


# ---------------------------------------------------------------------------
# 지오코딩 (브이월드)
# ---------------------------------------------------------------------------
def request_vworld(addr, addr_type, retries=3):
    params = dict(service="address", request="getcoord", version="2.0", crs="EPSG:5179",
                  address=addr, refine="true", simple="false", format="json",
                  type=addr_type.lower(), key=VWORLD_KEY)
    for _ in range(retries):
        try:
            res = session.get(VWORLD_URL, params=params, timeout=10).json()["response"]
        except (requests.RequestException, ValueError, KeyError):
            continue
        status = res.get("status")
        if status == "OK":
            point = res["result"]["point"]
            return float(point["x"]), float(point["y"])
        if status == "NOT_FOUND":
            return float("nan"), float("nan")
        raise QuotaError(res.get("error", res))
    return None     # 네트워크 오류 - 캐시에 남기지 않음


def geocode_all(targets, cache):
    """targets: {(주소, 'ROAD'|'PARCEL'), ...} 중 캐시에 없는 것만 요청"""
    todo = [k for k in targets if k not in cache]
    print(f"  요청 대상 {len(todo):,}건 (캐시 적중 {len(targets) - len(todo):,}건)")
    if not todo:
        return
    done = 0
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = {ex.submit(request_vworld, a, t): (a, t) for a, t in todo}
        try:
            for fut in as_completed(futures):
                result = fut.result()
                if result is not None:
                    with cache_lock:
                        cache[futures[fut]] = result
                done += 1
                if done % SAVE_EVERY == 0:
                    save_cache(cache)
                    print(f"  {done:,}/{len(todo):,}")
        except QuotaError as e:
            for f in futures:
                f.cancel()
            save_cache(cache)
            raise QuotaError(f"VWorld 오류로 중단(캐시 저장됨, 재실행 시 이어서 진행): {e}") from None
    save_cache(cache)


def lookup(cache, addr, addr_type):
    if pd.isna(addr):
        return None
    xy = cache.get((addr, addr_type))
    if xy is None or pd.isna(xy[0]):
        return None
    return xy


def _clean(s):
    s = s.str.replace(r"\s+", " ", regex=True).str.strip()
    return s.where(s.ne(""))


# ---------------------------------------------------------------------------
# 데이터프레임 좌표 부여
# ---------------------------------------------------------------------------
def add_coords(df, road_col="주소_도로명", parcel_col="주소_지번", cache=None):
    """전처리된 도로명·지번 주소로 좌표를 구해 x, y(EPSG:5179), 경도, 위도, 좌표_구분 컬럼을 추가한 사본을 반환.
    도로명으로 먼저 찾고, 실패한 건만 지번으로 다시 찾는다."""
    if cache is None:
        cache = load_cache()
        print(f"캐시 {len(cache):,}건 로드")
    road = _clean(df[road_col])
    parcel = _clean(df[parcel_col]).str.replace(r"번지$", "", regex=True)

    # 1차: 도로명
    geocode_all({(a, "ROAD") for a in road.dropna().unique()}, cache)
    road_xy = road.map(lambda a: lookup(cache, a, "ROAD"))

    # 2차: 도로명 실패 건만 지번
    need = road_xy.isna() & parcel.notna()
    geocode_all({(p, "PARCEL") for p in parcel[need].unique()}, cache)
    parcel_xy = parcel.where(need).map(lambda p: lookup(cache, p, "PARCEL"))

    xy = road_xy.where(road_xy.notna(), parcel_xy)
    out = df.copy()
    out["x"] = xy.str[0].astype(float)
    out["y"] = xy.str[1].astype(float)
    out["좌표_구분"] = (pd.Series(None, index=out.index, dtype=object)
                       .mask(parcel_xy.notna(), "PARCEL").mask(road_xy.notna(), "ROAD"))
    out["경도"], out["위도"] = to_wgs84.transform(out["x"].to_numpy(), out["y"].to_numpy())

    ok = out["x"].notna().sum()
    print(f"  성공 {ok:,}/{len(out):,} ({ok / len(out):.1%}) "
          f"- 도로명 {(out['좌표_구분'] == 'ROAD').sum():,}, 지번 {(out['좌표_구분'] == 'PARCEL').sum():,}")
    return out


# ---------------------------------------------------------------------------
# GPKG 저장 (연도별 레이어, 같은 이름 레이어만 덮어씀)
# ---------------------------------------------------------------------------
def save_layer(df, year, layer_prefix="부산사업체현황"):
    has_xy = df["x"].notna()
    geom = gpd.points_from_xy(df["x"], df["y"])
    gdf = gpd.GeoDataFrame(df, geometry=gpd.GeoSeries(geom, index=df.index).where(has_xy), crs="EPSG:5179")
    layer = f"{layer_prefix}_{year}"
    gdf.to_file(GPKG_PATH, layer=layer, driver="GPKG")
    print(f"  GPKG 저장: {layer} ({has_xy.sum():,}/{len(gdf):,}건 좌표 있음)")


if __name__ == "__main__":
    valid_dong, gj_dong = load_legal_dong()
    cache = load_cache()
    print(f"캐시 {len(cache):,}건 로드")

    for year in range(2019, 2026):
        for data in glob.glob(DATA_PATH + rf"02_산업경제\\*_{year}_*.csv"):
            print(f"\n[{year}] {os.path.basename(data)}")
            df = pd.read_csv(data, sep="|", dtype={'설립일자': str}, encoding="utf-16")
            df0 = preprocess(df, valid_dong, gj_dong)
            df0 = add_coords(df0, cache=cache)
            save_layer(df0, year)
