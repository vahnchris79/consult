# 공공데이터 포털 건축물 대장 API

import time
import requests
import xmltodict
import xml.parsers.expat
import pandas as pd
import geopandas as gpd
from urllib.parse import urlencode
from PublicDataReader import BuildingLicense
import urllib3

urllib3.disable_warnings()

# 설정
SERVICE_KEY = "GW1pXGS2GITHWlSTO4DU18zJ2TUxwH6wpZ1ADOImZ0wWPFMpNTPYdj0HHotEEUKPVD9reiyhB%2BoDnDmS84uG4g%3D%3D"
_translator = BuildingLicense(SERVICE_KEY)
BASE = "http://apis.data.go.kr/1613000/ArchPmsHubService/getApBasisOulnInfo"
TARGET_GUGUN = []
RETRYABLE = {'SERVICETIMEOUT_ERROR','INTERNAL_ERROR','HTTP_ERROR','SERVER_ERROR'}
RES_PATH = r"D:\\02_사업관리\\2026년\\데이터 분석 컨설팅\\20260902_도시계획과\\02_자료수집\\01_건축물정보\\"
GPKG_PATH = r"2026-018_도시계획과.gpkg"
OUTPUT_PATH = r"03_집계결과\\"
SGG = gpd.read_file(GPKG_PATH, layer="NGII_SIG_26")
EMD = gpd.read_file(GPKG_PATH, layer="NGII_EMD_26")

# 요청함수
def _request_page(sgg, bdong, page, num_rows, timeout, max_retry):
    query = urlencode({'numOfRows': num_rows, 'pageNo':page,
                             'sigunguCd':sgg, 'bjdongCd':bdong})
    url = f"{BASE}?serviceKey={SERVICE_KEY}&{query}"
    last = None
    for attempt in range(max_retry + 1):
        try:
            res = requests.get(url, verify=False, timeout=timeout)
            text = res.text.strip()
            if not text:
                last = "빈 응답"; time.sleep(1.5 * (attempt + 1)); continue
            data = xmltodict.parse(text)
            if "response" in data:
                return data
            if "OoenAPI_ServiceResponse" in data:
                msg = data["OpenAPI_ServiceResponse"]["cmmMsgHeader"].get("errMsg")
                if msg in RETRYABLE:
                    last = msg; time.sleep(1.5 * (attempt + 1)); continue
                raise RuntimeError(f"인증/서비스 오류: {msg}")
            last = f"예상외 응답: {text[:60]}"
            time.sleep(1.5 * (attempt + 1))
        except xml.parsers.expat.ExpatError as e:
            last = f"파싱실패: {e}"; time.sleep(1.5 * (attempt + 1))
        except requests.exceptions.RequestException as e:
            last = str(e); time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"재시도 초과: {last}")

# 직접 호출함수 생성
def fetch_basis(sgg, bdong, num_rows=100, timeout=60, max_retry=5):
    rows, page = [], 1
    while True:
        data = _request_page(sgg, bdong, page, num_rows, timeout, max_retry)
        header = data["response"]["header"]
        if str(header.get("resultCode")) not in ("00", "000"):
            raise RuntimeError(f"{header.get('resultCode')} {header.get('resultMsg')}")
        body = data["response"]["body"]
        items = body.get("items")
        if items and items.get("item"):
            item = items["item"]
            rows.extend(item if isinstance(item, list) else [item])
        total = int(body.get("totalCount") or 0)
        if total == 0 or page * num_rows >= total:
            break
        page += 1
    return rows

# GPKG에서 코드 추출
SGGNAME = dict(zip(SGG['SIG_CD'].astype(str), SGG['SIG_KOR_NM']))
EMD['EMD_CD'] = EMD['EMD_CD'].astype(str).apply(lambda x: x.zfill(8))
EMD['sigungu_code'] = EMD['EMD_CD'].astype(str).str[:5]
EMD['bdong_code'] = EMD['EMD_CD'].astype(str).str[5:] + "00"
EMD['시군구명'] = EMD['sigungu_code'].map(SGGNAME)

targets = EMD[['EMD_CD','시군구명','EMD_KOR_NM','sigungu_code','bdong_code']].copy()
if TARGET_GUGUN:
    targets = targets[targets['시군구명'].isin(TARGET_GUGUN)]
targets = targets.reset_index(drop=True)
print(f"수집 대상 읍면동 수: {len(targets)}개 (구군: {targets['시군구명'].nunique()}개)")

# 순회수집 함수
def collect(targets_df):
    frames, failed = [], []
    for i, row in targets_df.iterrows():
        label = f"{row['시군구명']} {row['EMD_KOR_NM']}"
        try:
            items = fetch_basis(row['sigungu_code'], row['bdong_code'])
            if items:
                df = pd.DataFrame(items)
                df = _translator.translate_columns(df)
                df['EMD_CD'] = row['EMD_CD']
                df['시군구명'] = row['시군구명']
                df['읍면동명'] = row['EMD_KOR_NM']
                frames.append(df)
                print(f"[{i+1}/{len(targets)}] {label}: {len(df)}건")
            else:
                print(f"[{i+1}/{len(targets)}] {label}: 0건")
        except Exception as e:
            print(f"[{i+1}/{len(targets)}] {label}: 오류 - {e}")
            failed.append(row)
        time.sleep(0.1)
    return frames, failed

# 추가수집
frames, failed = collect(targets)
if failed:
    print(f"\n실패 {len(failed)}개 재수집 시도...")
    more, failed = collect(pd.DataFrame(failed))
    frames += more

# 수집결과 합치기
if frames:
    result = pd.concat(frames, ignore_index=True)
    print(f"\n총 수집 건수: {len(result)}건")
    print("\n구·군별 건수:")
    print(result["시군구명"].value_counts().sort_index())
    result.to_excel(RES_PATH + "국토교통부_건축인허가_기본개요.xlsx", 
                    engine="openpyxl", index=False)
    print("\n저장 완료: 부산_건축인허가_기본개요.xlsx")
else:
    result = pd.DataFrame()
    print("\n수집된 데이터가 없습니다.")

if failed:
    print("\n최종 실패 {len(failed)}개 (재실행 필요): ")
    for r in failed:
        print(" ", r['시군구명'], r['EMD_KOR_NM'], r['sigungu_code'], r['bdong_code'])
