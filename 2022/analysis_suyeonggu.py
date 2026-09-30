

# 수영구 데이터 분석컨설팅
# 3. 연도별 업무 문서 키워드 분석

# 라이브러리 불러오기
from konlpy.tag import Okt
from collections import Counter
from matplotlib.image import NonUniformImage
import pandas as pd
import pandas_profiling

# 기록물시스템 데이터 변환
df = pd.read_csv("기록물 이용자_생산이력 추가.txt", encoding="utf-8")

# pandas-profiling을 통한 EDA report 생성
#pr = df.profile_report()
#pr.to_file("(수영구)프로파일링_결과보고서.html")

# 프로파일링 결과보고서 검토결과, 생산일자의 히스토그램이 2000~2020년 사이에 집중되어 있음
df_2k = df.loc[(df['생산일자']>=2000) & (df['생산일자']<=2021)].copy()

# 빈도분석에 필요한 컬럼만 추출
df_2k_ext = df_2k[['문서번호','로그인명','생산일자','건제목']]

# 건제목에서 명사추출 후 빈도확인, 결과는 CSV파일로 저장
okt = Okt()

df_2k_ext_spl = df_2k_ext[:8000] # 샘플추출

# 건제목의 값을 명사단위로 추출하여 words 리스트에 저장
words = []

for i in df_2k_ext_spl.index:
    nounses = okt.nouns(df_2k_ext_spl.loc[i, '건제목'])
    for nouns in nounses:
        if len(nouns) >= 2 and nouns not in words:
            words.append(nouns)
