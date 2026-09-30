

# 산복하늘 빛의 거리, 부산 크리스마스트리 문화축제 유동인구 증감량 분석
# 카드사용내역(업종 : 요식/유흥, 한식, 일식/중식/양식, 제과/커피/패스트푸드, 기타요식) 현황분석

import pandas as pd
import geopandas as gpd

# 요청기간(2021.11.22 ~ 2022.1.9)/증감비교기간(2021.10.4~2021.11.21)
# 요청기간(2021.11.22 ~ 2022.1.9)/증감비교기간(2021.10.4~2021.11.21)
# 산복하늘 빛의 거리 행사기간 내 성연령/시간대 현황
print("산복하늘 빛의 거리 내 성연령/시간대 유동인구 데이터 변환 시작")
pop11 = gpd.read_file("analysis_junggu_data.gpkg", layer="성연령_유동인구_산복하늘빛의거리_211004-220109", encoding="utf-8")
pop12 = gpd.read_file("analysis_junggu_data.gpkg", layer="시간대_유동인구_산복하늘빛의거리_211004-220109", encoding="utf-8")
print("산복하늘 빛의 거리 내 성연령/시간대 유동인구 데이터 변환 완료")
print("=" * 100)

# 산복하늘 빛의 거리 행사기간 내 카드이용 현황 : 21. 12.31까지 적용
print("산복하늘 빛의 거리 행사기간 내 카드이용 데이터 변환 시작")
card11 = gpd.read_file("analysis_junggu_data.gpkg", layer="업종별_카드이용_산복하늘빛의거리_211004-220109", encoding="utf-8")
card11.rename(columns={'CARD_USE_AMOUNT':'이용금액', 'CARD_USE_CO':'이용건수'}, inplace=True)
print("산복하늘 빛의 거리 행사기간 내 카드이용 데이터 변환 완료")
print("=" * 100)

# 요청기간(2021.12.4 ~ 2022.1.9)/감 비교 기간(2021.10.4~2021.11.21)
# 요청기간(2021.12.4 ~ 2022.1.9)/감 비교 기간(2021.10.4~2021.11.21)
# 부산크리스마스트리 문화센터
print("부산크리스마스트리 내 성연령/시간대 유동인구 데이터 변환 시작")
pop21 = gpd.read_file("analysis_junggu_data.gpkg", layer="성연령_유동인구_부산크리스마스트리_211028-220109", encoding="utf-8")
pop22 = gpd.read_file("analysis_junggu_data.gpkg", layer="시간대_유동인구_부산크리스마스트리_211028-220109", encoding="utf-8")
print("부산크리스마스트리 내 성연령/시간대 유동인구 데이터 변환 완료")
print("=" * 100)

# 부산크리스마스트리 행사기간 내 카드이용 현황 : 21. 12.31까지 적용
print("부산크리스마스트리 행사기간 내 카드이용 데이터 변환 시작")
card21 = gpd.read_file("analysis_junggu_data.gpkg", layer="업종별_카드이용_부산크리스마스트리_211028-220109", encoding="utf-8")
card21.rename(columns={'CARD_USE_AMOUNT':'이용금액', 'CARD_USE_CO':'이용건수'}, inplace=True)
print("부산크리스마스트리 행사기간 내 카드이용 데이터 변환 완료")
print("=" * 100)

# 성연령별(10세 단위) 이동량 집계
# 남자 10세 단위 집계
print("남자 10세 단위 집계 시작")
def man_10age_agg(df):
    df['M_1019'] = df['H_M_1014'] + df['H_M_1519'] + df['W_M_1014'] + df['W_M_1519'] + df['V_M_1014'] + df['V_M_1519']
    df['M_2029'] = df['H_M_2024'] + df['H_M_2529'] + df['W_M_2024'] + df['W_M_2529'] + df['V_M_2024'] + df['V_M_2529']
    df['M_3039'] = df['H_M_3034'] + df['H_M_3539'] + df['W_M_3034'] + df['W_M_3539'] + df['V_M_3034'] + df['V_M_3539']
    df['M_4049'] = df['H_M_4044'] + df['H_M_4549'] + df['W_M_4044'] + df['W_M_4549'] + df['V_M_4044'] + df['V_M_4549']
    df['M_5059'] = df['H_M_5054'] + df['H_M_5559'] + df['W_M_5054'] + df['W_M_5559'] + df['V_M_5054'] + df['V_M_5559']
    df['M_6069'] = df['H_M_6064'] + df['H_M_6569'] + df['W_M_6064'] + df['W_M_6569'] + df['V_M_6064'] + df['V_M_6569']
    df['M_7000'] = df['H_M_7000'] + df['H_M_7000'] + df['W_M_7000'] + df['W_M_7000'] + df['V_M_7000'] + df['V_M_7000']
man_10age_agg(pop11)
man_10age_agg(pop21)
print("남자 10세 단위 집계 완료")
print("=" * 100)

# 여자 10세 단위 집계
print("여자 10세 단위 집계 시작")
def wmn_10age_agg(df):
    df['W_1019'] = df['H_W_1014'] + df['H_W_1519'] + df['W_W_1014'] + df['W_W_1519'] + df['V_W_1014'] + df['V_W_1519']
    df['W_2029'] = df['H_W_2024'] + df['H_W_2529'] + df['W_W_2024'] + df['W_W_2529'] + df['V_W_2024'] + df['V_W_2529']
    df['W_3039'] = df['H_W_3034'] + df['H_W_3539'] + df['W_W_3034'] + df['W_W_3539'] + df['V_W_3034'] + df['V_W_3539']
    df['W_4049'] = df['H_W_4044'] + df['H_W_4549'] + df['W_W_4044'] + df['W_W_4549'] + df['V_W_4044'] + df['V_W_4549']
    df['W_5059'] = df['H_W_5054'] + df['H_W_5559'] + df['W_W_5054'] + df['W_W_5559'] + df['V_W_5054'] + df['V_W_5559']
    df['W_6069'] = df['H_W_6064'] + df['H_W_6569'] + df['W_W_6064'] + df['W_W_6569'] + df['V_W_6064'] + df['V_W_6569']
    df['W_7000'] = df['H_W_7000'] + df['H_W_7000'] + df['W_W_7000'] + df['W_W_7000'] + df['V_W_7000'] + df['V_W_7000']
wmn_10age_agg(pop11)
wmn_10age_agg(pop21)
print("여자 10세 단위 집계 완료")
print("=" * 100)

# 시간대별 집계
print("시간대별 유동인구 집계 시작")
def time_agg(df):
    df['SUM_18'] = df['H_T_18'] + df['W_T_18'] + df['V_T_18']
    df['SUM_19'] = df['H_T_19'] + df['W_T_19'] + df['V_T_19']
    df['SUM_20'] = df['H_T_20'] + df['W_T_20'] + df['V_T_20']
    df['SUM_21'] = df['H_T_21'] + df['W_T_21'] + df['V_T_21']
time_agg(pop12)
time_agg(pop22)
print("시간대별 유동인구 집계 완료")
print("=" * 100)

# 데이터타입 변환
print("데이터타입 변환 시작")
def convert_type(df):
    df['STD_YMD'] = df['STD_YMD'].astype(str)
convert_type(pop11)
convert_type(pop12)
convert_type(pop21)
convert_type(pop22)
print("데이터타입 변환 완료")
print("=" * 100)

# 기준연월일 기준으로 주 단위 표시
print("행사(축제)대상기간을 주 단위로 표시 시작")
def collect_week(df):
    df.loc[df['STD_YMD'].str.contains('20211004|20211005|20211006|20211007|20211008|20211009|20211010'), '대상기간(주)'] = '21년10월1주'
    df.loc[df['STD_YMD'].str.contains('20211011|20211012|20211013|20211014|20211015|20211016|20211017'), '대상기간(주)'] = '21년10월2주'
    df.loc[df['STD_YMD'].str.contains('20211018|20211019|20211020|20211021|20211022|20211023|20211024'), '대상기간(주)'] = '21년10월3주'
    df.loc[df['STD_YMD'].str.contains('20211025|20211026|20211027|20211028|20211029|20211030|20211031'), '대상기간(주)'] = '21년10월4주'
    df.loc[df['STD_YMD'].str.contains('20211101|20211102|20211103|20211104|20211105|20211106|20211107'), '대상기간(주)'] = '21년11월1주'
    df.loc[df['STD_YMD'].str.contains('20211108|20211109|20211110|20211111|20211112|20211113|20211114'), '대상기간(주)'] = '21년11월2주'
    df.loc[df['STD_YMD'].str.contains('20211115|20211116|20211117|20211118|20211119|20211120|20211121'), '대상기간(주)'] = '21년11월3주'
    df.loc[df['STD_YMD'].str.contains('20211122|20211123|20211124|20211125|20211126|20211127|20211128'), '대상기간(주)'] = '21년11월4주'
    df.loc[df['STD_YMD'].str.contains('20211129|20211130|20211201|20211202|20211203|20211204|20211205'), '대상기간(주)'] = '21년11월5주'
    df.loc[df['STD_YMD'].str.contains('20211206|20211207|20211208|20211209|20211210|20211211|20211212'), '대상기간(주)'] = '21년12월1주'
    df.loc[df['STD_YMD'].str.contains('20211213|20211214|20211215|20211216|20211217|20211218|20211219'), '대상기간(주)'] = '21년12월2주'
    df.loc[df['STD_YMD'].str.contains('20211220|20211221|20211222|20211223|20211224|20211225|20211226'), '대상기간(주)'] = '21년12월3주'
    df.loc[df['STD_YMD'].str.contains('20211227|20211228|20211229|20211230|20211231|20220101|20220102'), '대상기간(주)'] = '21년12월4주'
    df.loc[df['STD_YMD'].str.contains('20220103|20220104|20220105|20220106|20220107|20220108|20220109'), '대상기간(주)'] = '22년01월1주'
collect_week(pop11)
collect_week(pop12)
collect_week(card11)
collect_week(pop21)
collect_week(pop22)
collect_week(card21)
print("행사(축제)대상기간을 주 단위로 표시 완료")
print(pop11.head())
print(pop12.head())
print(card11.head())
print(pop21.head())
print(pop22.head())
print(card21.head())
print("=" * 100)

# 카드이용 데이터 정제
# 업종별 코드값 추가
print("업종별 카드이용 데이터 정제 시작")
def code_values(df):
    df.loc[df['INDUTY_SE_MLSFC'].str.contains('M001'), '업종중분류'] = '한식'
    df.loc[df['INDUTY_SE_MLSFC'].str.contains('M002'), '업종중분류'] = '일식/중식/양식'
    df.loc[df['INDUTY_SE_MLSFC'].str.contains('M003'), '업종중분류'] = '제과/커피/패스트푸드'
    df.loc[df['INDUTY_SE_MLSFC'].str.contains('M004'), '업종중분류'] = '기타요식'
    df.loc[df['SEXDSTN_CODE'].str.contains('M'), '남여별'] = '남'
    df.loc[df['SEXDSTN_CODE'].str.contains('F'), '남여별'] = '여'
    df.loc[df['AGRDE_CODE'].str.contains('1'), '연령별'] = '20대미만'
    df.loc[df['AGRDE_CODE'].str.contains('2'), '연령별'] = '20대'
    df.loc[df['AGRDE_CODE'].str.contains('3'), '연령별'] = '30대'
    df.loc[df['AGRDE_CODE'].str.contains('4'), '연령별'] = '40대'
    df.loc[df['AGRDE_CODE'].str.contains('5'), '연령별'] = '50대'
    df.loc[df['AGRDE_CODE'].str.contains('6'), '연령별'] = '60대'
    df.loc[df['AGRDE_CODE'].str.contains('7'), '연령별'] = '70대초과'
    df.loc[df['TMZON_CODE'].str.contains('18'), '시간대'] = '18시'
    df.loc[df['AGRDE_CODE'].str.contains('19'), '시간대'] = '19시'
    df.loc[df['AGRDE_CODE'].str.contains('20'), '시간대'] = '20시'
    df.loc[df['AGRDE_CODE'].str.contains('21'), '시간대'] = '21시'
code_values(card11)
code_values(card21)
print("업종별 카드이용 데이터 정제 완료")
print(card11.head())
print(card21.head())
print("=" * 100)

# 성별 집계 추가 
print("행사(축제)별 행사기간 내 성별 집계 시작")
def gender_sum(df):
    df['SUM_M'] = df['M_1019'] + df['M_2029'] + df['M_3039'] + df['M_4049'] + df['M_5059'] + df['M_6069'] + df['M_7000']
    df['SUM_W'] = df['W_1019'] + df['W_2029'] + df['W_3039'] + df['W_4049'] + df['W_5059'] + df['W_6069'] + df['W_7000']
gender_sum(pop11)
gender_sum(pop21)
print("행사(축제)별 행사기간 내 성별 집계 완료")
print(pop11.head())
print(pop21.head())
print("=" * 100)

# 전체, 성별, 연령별 집계
print("행사(축제)별 기간 내 전체 이동량 집계 시작")
def pop_sum_all(df):
    df['SUM_ALL'] = df['SUM_M'] + df['SUM_W']
pop_sum_all(pop11)
pop_sum_all(pop21)
print("행사(축제)별 기간 내 전체 이동량 집계 완료")
print(pop11.head())
print(pop21.head())
print("=" * 100)

# 연령별 집계
print("행사(축제)별 행사기간 내 연령별 집계 시작")
def age_sum(df):
    df['SUM_1019'] = df['M_1019'] + df['W_1019']
    df['SUM_2029'] = df['M_2029'] + df['W_2029']
    df['SUM_3039'] = df['M_3039'] + df['W_3039']
    df['SUM_4049'] = df['M_4049'] + df['W_4049']
    df['SUM_5059'] = df['M_5059'] + df['W_5059']
    df['SUM_6069'] = df['M_6069'] + df['W_6069']
    df['SUM_7000'] = df['M_7000'] + df['W_7000']
age_sum(pop11)
age_sum(pop21)
print("행사(축제)별 행사기간 내 연령별 집계 완료")
print(pop11.head())
print(pop21.head())
print("=" * 100)

# 성연령별 집계를 위한 컬럼 정제
print("성연령별 유동인구 컬럼 정제 시작")
pop11_all1 = pop11[['대상기간(주)','SUM_ALL']]
pop11_gen1 = pop11[['대상기간(주)','SUM_M','SUM_W']]
pop11_age1 = pop11[['대상기간(주)','SUM_1019','SUM_2029','SUM_3039','SUM_4049','SUM_5059','SUM_6069','SUM_7000']]
pop21_all1 = pop21[['대상기간(주)','SUM_ALL']]
pop21_gen1 = pop21[['대상기간(주)','SUM_M','SUM_W']]
pop21_age1 = pop21[['대상기간(주)','SUM_1019','SUM_2029','SUM_3039','SUM_4049','SUM_5059','SUM_6069','SUM_7000']]
print(pop11_all1.head())
print(pop11_gen1.head())
print(pop11_age1.head())
print(pop21_all1.head())
print(pop21_gen1.head())
print(pop21_age1.head())
print("=" * 100)

# 시간대별 집계를 위한 컬럼 정제
print("시간대별 유동인구 컬럼 정제 시작")
pop12_tm1 = pop12[['대상기간(주)','SUM_18','SUM_19','SUM_20','SUM_21']]
pop22_tm1 = pop22[['대상기간(주)','SUM_18','SUM_19','SUM_20','SUM_21']]
print("시간대별 유동인구 컬럼 정제 완료")
print(pop12_tm1.head())
print(pop22_tm1.head())
print("=" * 100)

# 카드이용내역 집계를 위한 컬럼 정제
print("카드이용내역 컬럼 정제 시작")
card11_cls = card11[['대상기간(주)','업종중분류','남여별','연령별','시간대','이용금액','이용건수']]
card21_cls = card21[['대상기간(주)','업종중분류','남여별','연령별','시간대','이용금액','이용건수']]
print("카드이용내역 컬럼 정제 완료")
print(card11_cls.head())
print(card21_cls.head())
print("=" * 100)

# 데이터 재구조화
# 성연령별 집계 데이터 재구조화
print("성연령별 집계 데이터 재구조화 시작")
pop11_all2 = pd.melt(pop11_all1, id_vars='대상기간(주)', value_vars='SUM_ALL', var_name='유동인구전체', value_name='이동량(집계)')
pop11_gen2 = pd.melt(pop11_gen1, id_vars='대상기간(주)', value_vars=['SUM_M','SUM_W'], var_name='남여별', value_name='이동량(집계)')
pop11_age2 = pd.melt(pop11_age1, id_vars='대상기간(주)', value_vars=['SUM_1019','SUM_2029','SUM_3039','SUM_4049','SUM_5059','SUM_6069','SUM_7000'],
                     var_name='연령별', value_name='이동량(집계)')
pop21_all2 = pd.melt(pop21_all1, id_vars='대상기간(주)', value_vars='SUM_ALL', var_name='유동인구전체', value_name='이동량(집계)')
pop21_gen2 = pd.melt(pop21_gen1, id_vars='대상기간(주)', value_vars=['SUM_M','SUM_W'], var_name='남여별', value_name='이동량(집계)')
pop21_age2 = pd.melt(pop21_age1, id_vars='대상기간(주)', value_vars=['SUM_1019','SUM_2029','SUM_3039','SUM_4049','SUM_5059','SUM_6069','SUM_7000'],
                     var_name='연령별', value_name='이동량(집계)')
print("성연령별 집계 데이터 재구조화 완료")
print(pop11_all2)
print(pop11_gen2)
print(pop11_age2)
print(pop21_all2)
print(pop21_gen2)
print(pop21_age2)
print("=" * 100)

# 시간대 집계 데이터 재구조화
print("시간대별 집계 데이터 재구조화 시작")
pop12_tm2 = pd.melt(pop12_tm1, id_vars='대상기간(주)', value_vars=['SUM_18','SUM_19','SUM_20','SUM_21'], var_name='시간대', value_name='이동량(집계)')
pop22_tm2 = pd.melt(pop22_tm1, id_vars='대상기간(주)', value_vars=['SUM_18','SUM_19','SUM_20','SUM_21'], var_name='시간대', value_name='이동량(집계)')
print("시간대별 집계 데이터 재구조화 완료")
print(pop12_tm2)
print(pop22_tm2)
print("=" * 100)

# 데이터 확인
print(pop11_gen2)
print(pop11_age2)
print(pop12_tm2)
print(pop21_gen2)
print(pop21_age2)
print(pop22_tm2)
print("=" * 100)

# 시각화를 위한 집계 : 유동인구
print("시각화용 집계데이터 생성 시작")
pop11_all3 = pop11_all2.groupby(['대상기간(주)','유동인구전체'])['이동량(집계)'].sum().reset_index()
pop11_gen3 = pop11_gen2.groupby(['대상기간(주)','남여별'])['이동량(집계)'].sum().reset_index()
pop11_age3 = pop11_age2.groupby(['대상기간(주)','연령별'])['이동량(집계)'].sum().reset_index()
pop12_tm3 = pop12_tm2.groupby(['대상기간(주)','시간대'])['이동량(집계)'].sum().reset_index()
pop21_all3 = pop21_all2.groupby(['대상기간(주)','유동인구전체'])['이동량(집계)'].sum().reset_index()
pop21_gen3 = pop21_gen2.groupby(['대상기간(주)','남여별'])['이동량(집계)'].sum().reset_index()
pop21_age3 = pop21_age2.groupby(['대상기간(주)','연령별'])['이동량(집계)'].sum().reset_index()
pop22_tm3 = pop22_tm2.groupby(['대상기간(주)','시간대'])['이동량(집계)'].sum().reset_index()
print("CSV파일 변환 시작")
#pop11_all3.to_csv("D:/03_분석업무/중구 홍보교육과_축제유동인구 현황/분석결과/산복하늘 빛의 거리_유동인구전체_집계.csv", encoding="cp949")
#pop11_gen3.to_csv("D:/03_분석업무/중구 홍보교육과_축제유동인구 현황/분석결과/산복하늘 빛의 거리_남여별_집계.csv", encoding="cp949")
#pop11_age3.to_csv("D:/03_분석업무/중구 홍보교육과_축제유동인구 현황/분석결과/산복하늘 빛의 거리_연령별_집계.csv", encoding="cp949")
#pop12_tm3.to_csv("D:/03_분석업무/중구 홍보교육과_축제유동인구 현황/분석결과/산복하늘 빛의 거리_시간대_집계.csv", encoding="cp949")
#pop21_all3.to_csv("D:/03_분석업무/중구 홍보교육과_축제유동인구 현황/분석결과/부산크리스마스트리_유동인구전체_집계.csv", encoding="cp949")
#pop21_gen3.to_csv("D:/03_분석업무/중구 홍보교육과_축제유동인구 현황/분석결과/부산크리스마스트리_남여별_집계.csv", encoding="cp949")
#pop21_age3.to_csv("D:/03_분석업무/중구 홍보교육과_축제유동인구 현황/분석결과/부산크리스마스트리_연령별_집계.csv", encoding="cp949")
#pop22_tm3.to_csv("D:/03_분석업무/중구 홍보교육과_축제유동인구 현황/분석결과/부산크리스마스트리_시간대_집계.csv", encoding="cp949")
print("시각화용 집계데이터 생성 완료")
print(pop11_all3.head())
print(pop11_gen3.head())
print(pop11_age3.head())
print(pop12_tm3.head())
print(pop21_all3.head())
print(pop21_gen3.head())
print(pop21_age3.head())
print(pop22_tm3.head())
print("=" * 100)

# 시각화를 위한 집계 : 카드이용내역
print("업종중분류/성별/연령별/시간대 카드사용내역 집계 시작")
card11_kind = card11.groupby(['대상기간(주)','업종중분류',])['이용건수','이용금액'].sum().reset_index()
card21_kind = card21.groupby(['대상기간(주)','업종중분류',])['이용건수','이용금액'].sum().reset_index()
card11_gen = card11.groupby(['대상기간(주)','남여별',])['이용건수','이용금액'].sum().reset_index()
card21_gen = card21.groupby(['대상기간(주)','남여별',])['이용건수','이용금액'].sum().reset_index()
card11_age = card11.groupby(['대상기간(주)','연령별',])['이용건수','이용금액'].sum().reset_index()
card21_age = card21.groupby(['대상기간(주)','연령별',])['이용건수','이용금액'].sum().reset_index()
card11_tm = card11.groupby(['대상기간(주)','시간대',])['이용건수','이용금액'].sum().reset_index()
card21_tm = card21.groupby(['대상기간(주)','시간대',])['이용건수','이용금액'].sum().reset_index()
print("업종중분류/성별/연령별/시간대 카드사용내역 집계 완료")
print(card11_kind.head())
print(card21_kind.head())
print(card11_gen.head())
print(card21_gen.head())
print(card11_age.head())
print(card21_age.head())
print(card11_tm.head())
print(card21_tm.head())
print("=" * 100)

# 이용건수, 금액 단위조정(시인성 확보)
print("카드사용내역 집계단위 조정 시작")
def change_units(df):
    df['이용건수(백  건)'] = round(df['이용건수'] / 100)
    df['이용금액(백만원)'] = round(df['이용금액'] / 1000000)
change_units(card11_kind)
change_units(card11_gen)
change_units(card11_age)
change_units(card11_tm)
change_units(card21_kind)
change_units(card21_gen)
change_units(card21_age)
change_units(card21_tm)
print("카드사용내역 집계단위 조정 완료")
print("=" * 100)

# 카드이용내역 집계데이터 CSV파일 변환
print("카드이용내역 집계데이터 CSV파일 변환 시작")
card11_kind.to_csv("D:/03_분석업무/중구 홍보교육과_축제유동인구 현황/분석결과/산복하늘 빛의 거리_업종별_이용현황_집계.csv", encoding="cp949")
card11_gen.to_csv("D:/03_분석업무/중구 홍보교육과_축제유동인구 현황/분석결과/산복하늘 빛의 거리_남여별_이용현황_집계.csv", encoding="cp949")
card11_age.to_csv("D:/03_분석업무/중구 홍보교육과_축제유동인구 현황/분석결과/산복하늘 빛의 거리_연령별_이용현황_집계.csv", encoding="cp949")
card11_tm.to_csv("D:/03_분석업무/중구 홍보교육과_축제유동인구 현황/분석결과/산복하늘 빛의 거리_시간대_이용현황_집계.csv", encoding="cp949")
card21_kind.to_csv("D:/03_분석업무/중구 홍보교육과_축제유동인구 현황/분석결과/부산크리스마스트리_업종별_이용현황_집계.csv", encoding="cp949")
card21_gen.to_csv("D:/03_분석업무/중구 홍보교육과_축제유동인구 현황/분석결과/부산크리스마스트리_남여별_이용현황_집계.csv", encoding="cp949")
card21_age.to_csv("D:/03_분석업무/중구 홍보교육과_축제유동인구 현황/분석결과/부산크리스마스트리_연령별_이용현황_집계.csv", encoding="cp949")
card21_tm.to_csv("D:/03_분석업무/중구 홍보교육과_축제유동인구 현황/분석결과/부산크리스마스트리_시간대_이용현황_집계.csv", encoding="cp949")
print("카드이용내역 집계데이터 CSV파일 변환 완료")
print("=" * 100)