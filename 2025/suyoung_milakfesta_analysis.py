"""
수영구 밀락더마켓 축제 생활인구·카드이용 분석
"""

import calendar
import glob
from datetime import date

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely import wkt
from shapely.geometry.base import BaseGeometry

pd.options.display.float_format = "{:.5f}".format

# ─────────────────────────────────────────────
# 경로 설정
# ─────────────────────────────────────────────

BASE = r"D:\02_사업관리"
ANALYSIS_BASE = rf"{BASE}\2025년\데이터 분석 컨설팅\20250402_수영구청\문화관광과"

emd_lists   = glob.glob(rf"{BASE}\적재확인\01_생활인구\*_emd_p_*.csv",  recursive=True)
card_lists  = glob.glob(rf"{BASE}\적재확인\02_카드이용\*_sec_p_*.csv",  recursive=True)
area        = pd.read_csv(rf"{ANALYSIS_BASE}\2_분석영역\study_area_20250402_v1.csv",  sep="|", encoding="utf-8")
grid        = pd.read_csv(rf"{BASE}\코드자료\grid50_busan.csv",          encoding="utf-8")
rycode      = pd.read_csv(rf"{BASE}\코드자료\bccd_sec_code.csv",         encoding="utf-8")
output_path = rf"{ANALYSIS_BASE}\3_집계결과\\"

# ─────────────────────────────────────────────
# 공간 처리
# ─────────────────────────────────────────────

def to_geodataframe(df: pd.DataFrame) -> gpd.GeoDataFrame:
    """WKT 문자열 → GeoDataFrame 변환 (이미 geometry 객체면 그대로 사용)"""
    df = df.copy()
    if not isinstance(df["geometry"].iloc[0], BaseGeometry):
        df["geometry"] = df["geometry"].apply(wkt.loads)
        return gpd.GeoDataFrame(df, geometry="geometry", crs=5179)


def get_study_grid() -> gpd.GeoDataFrame:
    """분석 영역과 교차하는 그리드 ID 목록 반환 (1회만 계산)"""
    return gpd.overlay(to_geodataframe(grid), to_geodataframe(area), how="intersection")


_study_grid: gpd.GeoDataFrame | None = None  # 캐시


def study_grid() -> gpd.GeoDataFrame:
    global _study_grid
    if _study_grid is None:
        _study_grid = get_study_grid()
        return _study_grid


    # ─────────────────────────────────────────────
    # 날짜 유틸
    # ─────────────────────────────────────────────

def _week_of_month_vec(
    year: int, month: int, day: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    월 내 주차(목요일 기준 ISO 보정)를 벡터 연산으로 계산.
    반환: (보정된 year 배열, 보정된 month 배열, 주차 배열)
    """
    first_dow = date(year, month, 1).weekday()
    flag = 1 if first_dow > 3 else 0
    cal_arr = np.array(calendar.monthcalendar(year, month))

    day_to_week = {
        d: row_idx + 1
        for row_idx, week_row in enumerate(cal_arr)
        for d in week_row
        if d != 0
    }

    raw_weeks = np.array([day_to_week[d] for d in day])
    weeks = raw_weeks - flag

    out_years  = np.full(len(day), year,  dtype=int)
    out_months = np.full(len(day), month, dtype=int)
    out_weeks  = weeks.copy()

    for i, (d, w) in enumerate(zip(day, weeks)):
        dow = date(year, month, int(d)).weekday()

        if w == 0:
            if dow > 3:  # 이전 달 마지막 주로 귀속
                py, pm = (year - 1, 12) if month == 1 else (year, month - 1)
                ld   = calendar.monthrange(py, pm)[1]
                pcal = np.array(calendar.monthcalendar(py, pm))
                pflag = 1 if date(py, pm, 1).weekday() > 3 else 0
                pw = np.where(pcal == ld)[0][0] + 1 - pflag
                out_years[i], out_months[i], out_weeks[i] = py, pm, pw
            else:
                out_weeks[i] = 1  # 이번 달 1주로 보정

        elif w == 5:
            ny, nm = (year + 1, 1) if month == 12 else (year, month + 1)
            if date(ny, nm, 1).weekday() <= 3:  # 다음 달 1주로 귀속
                out_years[i], out_months[i], out_weeks[i] = ny, nm, 1

                return out_years, out_months, out_weeks


def create_week_info(df: pd.DataFrame) -> pd.DataFrame:
    """
    날짜 컬럼(std_ymd)으로부터 연·월·주차·요일·주내일수 테이블 생성.
    std_ymd 파싱 실패 시 빈 DataFrame을 안전하게 반환.
    """
    dates = (
        pd.to_datetime(df["std_ymd"], format="%Y%m%d", errors="coerce")
        .dropna()
        .drop_duplicates()
        .sort_values()
        .reset_index(drop=True)
    )

    if dates.empty:
        raise ValueError("std_ymd 컬럼에서 유효한 날짜를 파싱하지 못했습니다. 포맷을 확인하세요.")

    records = []
    for (y, m), grp in dates.groupby([dates.dt.year, dates.dt.month]):
        days = grp.dt.day.values
        yrs, mos, wks = _week_of_month_vec(int(y), int(m), days)
        for dt, ry, rm, rw in zip(grp, yrs, mos, wks):
            records.append(
                {
                    "std_ymd" : dt.strftime("%Y-%m-%d"),
                    "_year"   : int(ry),
                    "_month"  : int(rm),
                    "_week"   : int(rw),
                    "weekname": dt.day_name(locale="ko_KR"),
                }
            )

            result = pd.DataFrame(records)
            result["year"]    = result["_year"].astype(str)  + "년"
            result["month"]   = result["_month"].apply(lambda x: str(x).zfill(2) + "월")
            result["weeklbl"] = result["_week"].astype(str)  + "주"

            ymw = result["year"] + result["month"] + result["weeklbl"]
            result["days_in_week"] = ymw.map(ymw.value_counts())

            return (
        result[["std_ymd", "year", "month", "weeklbl", "weekname", "days_in_week"]]
        .drop_duplicates()
        .reset_index(drop=True)
    )


    # ─────────────────────────────────────────────
    # 데이터 전처리
    # ─────────────────────────────────────────────

def dataprocessing(df: pd.DataFrame) -> pd.DataFrame:
    """공간 교차 필터링 + 수치 컬럼 타입 변환 + 날짜 포맷 통일"""
    df = pd.merge(study_grid(), df, how="inner", on="id").drop(columns=["geometry"], errors="ignore")

    num_cols = [c for c in df.columns if c[:2] in ("h_", "w_", "v_")]
    df[num_cols] = df[num_cols].astype(float)

    df["std_ymd"] = (
        pd.to_datetime(df["std_ymd"], format="%Y%m%d", errors="coerce")
        .dt.strftime("%Y-%m-%d")
    )
    return df


def _add_group_cols(df: pd.DataFrame, col_map: dict[str, list[str]]) -> pd.DataFrame:
    """col_map에 정의된 원본 컬럼들을 합산하여 신규 컬럼 추가"""
    for new_col, src_cols in col_map.items():
        valid = [c for c in src_cols if c in df.columns]
        if valid:
            df[new_col] = df[valid].sum(axis=1)
            return df


def _prepare(df: pd.DataFrame) -> pd.DataFrame:
    """공통 전처리: dataprocessing → week_info 병합"""
    week_info = create_week_info(df)        # 원본 df로 날짜 정보 생성
    df = dataprocessing(df)                 # 공간 필터링·타입 변환 (std_ymd가 %Y-%m-%d로 바뀜)
    return df.merge(
week_info[["std_ymd", "year", "month", "weeklbl", "weekname"]],
on="std_ymd",
how="left",
)


_GROUP_KEY = ["year", "month", "weeklbl", "weekname", "areanm"]


# ─────────────────────────────────────────────
# 집계 함수
# ─────────────────────────────────────────────

def aggregate_gender(df: pd.DataFrame) -> pd.DataFrame:
    gender_map = {
        "m_sum": [c for c in df.columns if "_m_" in c],
        "w_sum": [c for c in df.columns if "_w_" in c],
    }
    df = _prepare(df)
    df = _add_group_cols(df, gender_map)
    return (
df.groupby(_GROUP_KEY)[["m_sum", "w_sum"]]
.sum()
.reset_index()
.sort_values(["year", "month", "weeklbl"])
)


def aggregate_ages(df: pd.DataFrame) -> pd.DataFrame:
    age_map = {
        "20le_sum": [c for c in df.columns if c[-4:] in {"0009", "1014", "1519"}],
        "20eq_sum": [c for c in df.columns if c[-4:] in {"2024", "2529"}],
        "30eq_sum": [c for c in df.columns if c[-4:] in {"3034", "3539"}],
        "40eq_sum": [c for c in df.columns if c[-4:] in {"4044", "4549"}],
        "50eq_sum": [c for c in df.columns if c[-4:] in {"5054", "5559"}],
        "60gt_sum": [c for c in df.columns if c[-4:] in {"6064", "6569", "7000"}],
    }
    df = _prepare(df)
    df = _add_group_cols(df, age_map)
    return (
df.groupby(_GROUP_KEY)[list(age_map.keys())]
.sum()
.reset_index()
.sort_values(["year", "month", "weeklbl"])
)


def aggregate_carduse(df: pd.DataFrame) -> pd.DataFrame:
    df = _prepare(df)
    df = df.merge(rycode, on="ry_m_cd", how="left")
    df[["amt", "cnt"]] = df[["amt", "cnt"]].astype(float)
    return (
df.groupby(["year", "month", "weeklbl", "weekname", "ry_m_nm", "areanm"])[["amt", "cnt"]]
.sum()
.reset_index()
.sort_values(["year", "month", "weeklbl"])
)


# ─────────────────────────────────────────────
# 실행
# ─────────────────────────────────────────────

if __name__ == "__main__":
    # 생활인구 집계
    emd_dfs = [pd.read_csv(p, sep="|", encoding="utf-8") for p in emd_lists]
    if emd_dfs:
        emd_all = pd.concat(emd_dfs, ignore_index=True)
        aggregate_gender(emd_all).to_csv(output_path + "월별 성별 방문인구 현황.csv",  sep="|", encoding="utf-8", index=False)
        aggregate_ages(emd_all).to_csv(  output_path + "월별 연령 방문인구 현황.csv", sep="|", encoding="utf-8", index=False)

        # 카드이용 집계
        card_dfs = [pd.read_csv(p, sep="|", encoding="utf-8") for p in card_lists]
        if card_dfs:
            card_all = pd.concat(card_dfs, ignore_index=True)
            aggregate_carduse(card_all).to_csv(output_path + "월별 업종별 카드이용 현황.csv", sep="|", encoding="utf-8", index=False)