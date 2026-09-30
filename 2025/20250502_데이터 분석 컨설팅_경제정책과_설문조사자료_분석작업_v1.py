
# 데이터 분석 컨설팅
# 경제정책과, 수출애로요인 설문조사 자료분석

import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from ydata_profiling import profile_report

pd.set_option("display.max_rows", 100)
pd.set_option("display.max_columns", 20)

sns.set_theme(style='whitegrid', palette='muted',
              font='NanumGothic', font_scale=0.8)

a = pd.read_excel("☆(4월조사)부산시 수출애로요인 조사(응답)_전처리.xlsx", sheet_name="설문지 응답 시트1", engine="openpyxl")
#print(a.columns)

# 항목삭제
# 개인정보동의여부, 
# '1. 귀사의 업체명과 응답자의 성함, 직책, 연락처를 기재해 주십시오.', 
# '8. 추가로 의견을 주고 싶으신 부분이 있으시면 자유롭게 작성해 주세요.'

a = a[['타임스탬프',
       '2. 귀사의 주요 업종(생산품)은 다음 중 어디에 해당합니까?',
       '3. 귀사의 주요 수출품과 수입품은 무엇인가요?',
       '4. 귀사는 해외에 공장을 가지고 있습니까?',
       '4-1. 해외공장이 있는 경우, 공장이 있는 국가를 적어주세요.',
       '1. 귀사의 규모를 선택해 주십시오.', 
       '2. 귀사의 주요 수출 대상국은 어디입니까?',
       '3. 귀사의 수출 비중은 전체 매출의 몇 %입니까?',
       '4. 미 관세정책 발효로 인해 귀사에서 겪고 있는 주요 어려움은 무엇입니까?',
       '5. 귀사에서 관세정책에 대한 대응을 위해 시행한 조치가 있다면 무엇입니까?',
       '6. 정부(지자체)의 지원 정책이 필요한 부분은 무엇입니까?',
       '7. 귀사가 부산시가 추진하는 수출지원정책에 대해 알게 되는 경로는 무엇인가요?',]]

# 시각화 시인성을 위해 설문조사 질의항목을 변경, 기준 질의내용 유지
a.rename(columns={'타임스탬프': '조사대상분류', 
                  '2. 귀사의 주요 업종(생산품)은 다음 중 어디에 해당합니까?': '주요업종', 
                  '3. 귀사의 주요 수출품과 수입품은 무엇인가요?': '주요수출입 물품',
                  '4. 귀사는 해외에 공장을 가지고 있습니까?': '해외공장 운영여부',
                  '4-1. 해외공장이 있는 경우, 공장이 있는 국가를 적어주세요.': '해외공장 운영국가',
                  '1. 귀사의 규모를 선택해 주십시오.': '기업규모',
                  '2. 귀사의 주요 수출 대상국은 어디입니까?': '주요수출 대상국',
                  '3. 귀사의 수출 비중은 전체 매출의 몇 %입니까?': '매출액 대비 수출비중',
                  '4. 미 관세정책 발효로 인해 귀사에서 겪고 있는 주요 어려움은 무엇입니까?': '관세정책 발효로 인한 어려움',
                  '5. 귀사에서 관세정책에 대한 대응을 위해 시행한 조치가 있다면 무엇입니까?': '기업차원 대응조치',
                  '6. 정부(지자체)의 지원 정책이 필요한 부분은 무엇입니까?': '필요한 행정지원',
                  '7. 귀사가 부산시가 추진하는 수출지원정책에 대해 알게 되는 경로는 무엇인가요?': '수출지원 정책정보 입수경로'},
                  inplace=True)

# 주요수출입 물품을 주요수출 물품, 주요수입 물품으로 분류함.
#a = a.fillna('NaN')
a_fill = a.fillna('무응답')
#a_filter = a.loc[(a['주요업종'] != 'NaN') | (a['주요수출입 물품'] != 'NaN') & (a['해외공장 운영국가'] != 'NaN')].copy()
a_fill['주요수출품'] = ''
a_fill['주요수입품'] = ''
for i in a_fill.index:
    if '|' in a_fill.loc[i, '주요수출입 물품']:
        a_fill.loc[i, '주요수출품'] = a_fill.loc[i, '주요수출입 물품'].split('|')[0].replace('수출:', '')
        a_fill.loc[i, '주요수입품'] = a_fill.loc[i, '주요수출입 물품'].split('|')[1].replace('수입:', '')
    if '|' not in a_fill.loc[i, '주요수출입 물품']:
        a_fill.loc[i, '주요수출품'] = '무응답'
        a_fill.loc[i, '주요수입품'] = '무응답'
    if '없음' in a_fill.loc[i, '해외공장 운영여부']:
        a_fill.loc[i, '해외공장 운영여부'] = '아니오'
    else:
        pass

# 컬럼 정비
b = a_fill[['조사대상분류', '기업규모', '주요업종', '주요수출품', '주요수입품', '해외공장 운영여부', '해외공장 운영국가', 
              '주요수출 대상국', '매출액 대비 수출비중', '관세정책 발효로 인한 어려움', '기업차원 대응조치', '필요한 행정지원',
              '수출지원 정책정보 입수경로']]
industry_dicts = {
    '선박(조선기자재)': '선박제조업', '자동차·자동차부품': '자동차제조업', '자동차부품': '자동차제조업', '기계·기계부품': '기계제조업', '무응답': '무응답', 
    '사진영상 기자재 개발 및 제조': '제조업', '축산업 가금류': '기타 축산업', '주방용품': '도매및소매업', '산업용 고무제품': '제조업', 
    '금융': '금융및보험업', '신발': '신발제조업', '철강·비철금속': '철강제조업', '페인트 제조': '제조업', 'PE 제품 생산': '제조업', 
    '신발제조업': '신발제조업', '전자부품': '전자제조업', 'IT': '정보통신업', '항공기부품': '제조업', '신발제조업': '신발제조업', 
    '신발부품': '신발제조업', '신발': '신발제조업', '소비재': '개인서비스업', 'LED 조명': '제조업', '신발소재': '신발제조업',
    '신발자재': '신발제조업', '기타': '제조업', '신발제조': '신발제조업', '신발부품,인솔': '신발제조업', '신발용 원부자재': '신발제조업',
    '신발 shoes ': '신발제조업'}

for key, value in industry_dicts.items():
    for i in b.index:
        if key in b.loc[i, '주요업종']:
            b.loc[i, '표준산업분류'] = value
        else:
            pass
b.to_excel("부산시 수출애로요인 조사(응답)_전처리.xlsx", index=False)

# 전처리 결과에 대한 EDA 생성
report = b.profile_report()
#report.to_file("(경제정책과)부산시_수출애로요인_설문조사_EDA.html")

# 워드클라우드 시각화용 함수
# 단일 셀에 여러 품목이 있는 경우 분리 (예: 쉼표, 슬래시 기준)
def split_items(series):
    items = []
    for entry in series:
        # 쉼표와 슬래시를 기준으로 분리
        for item in entry.replace('/', ',').split(','):
            cleaned = item.strip()
            if cleaned:
                items.append(cleaned)
    return items

# 워드클라우드 생성 함수
def generate_wordcloud(frequencies, title):
    wordcloud = WordCloud(font_path='C:/Windows/Fonts/NanumGothic.ttf',
                          width=800, height=400, background_color='white').generate_from_frequencies(frequencies)
    plt.figure(figsize=(10, 5))
    plt.imshow(wordcloud, interpolation='bilinear')
    plt.axis('off')
    plt.title(title, fontsize=16)
    plt.savefig(f"시각화/{title}.png", dpi=300)

# 주요업종별 현황 시각화
print("기업일반 사항: 업종선택")
group2 = b.groupby('표준산업분류')['표준산업분류'].count().reset_index(name='집계결과').sort_values(by='집계결과', ascending=False)
#print(group2)
#group2 = group2.loc[group2['집계결과'] > 2].copy()
#plt.figure(figsize=(12, 5))
#group2bar = sns.barplot(data=group2, x='표준산업분류', y='집계결과', width=0.5, color='magenta')
#group2bar.set(xlabel = '표준산업분류', ylabel='집계결과')
#for i in group2bar.containers:
#    group2bar.bar_label(i, fontsize=8, )
#plt.grid(True, linewidth=0.5, linestyle=':')
#plt.savefig("시각화/1_주요업종(표준산업분류)별 집계현황2.png", dpi=300)
print()

# 주요수출품과 주요수입품 현황
from wordcloud import WordCloud
import matplotlib.pyplot as plt

# 주요수출품과 주요수입품 열에서 무응답 제외 및 결측치 제거
print("기업일반 사항: 주요 수출입 품목")
export_items = b['주요수출품'].dropna()
import_items = b['주요수입품'].dropna()
export_items = export_items[~export_items.str.strip().isin(['무응답', ''])]
import_items = import_items[~import_items.str.strip().isin(['무응답', ''])]
export_list = split_items(export_items)
import_list = split_items(import_items)
export_freq = pd.Series(export_list).value_counts()
import_freq = pd.Series(import_list).value_counts()
#generate_wordcloud(export_freq, "기업일반 사항_주요 수출품 빈도")
#generate_wordcloud(import_freq, "기업일반 사항_주요 수입품 빈도")
print()
#해외공장 운영여부와 해외공장 운영국가 빈도
print("기업인반 사항: 해외공장 유무")
outfac_operate = b['해외공장 운영여부'].dropna()
outfac_nation = b['해외공장 운영국가'].dropna()
outfac_operate_list = split_items(outfac_operate)
outfac_nation_list = split_items(outfac_nation)
outfac_operate_freq = pd.Series(outfac_operate_list).value_counts()
#generate_wordcloud(outfac_operate_freq, "기업일반 사항_해외공장 운영유무")
print()
print("기업인반 사항: 해외공장 국가명")
outfac_nation_df = pd.DataFrame({'해외공장 운영국가': outfac_nation_list})
group03 = outfac_nation_df.groupby('해외공장 운영국가')['해외공장 운영국가'].count().reset_index(name='집계결과').sort_values(by='집계결과', ascending=False)
group03 = group03.loc[group03['집계결과'] > 1].copy() # 러시아, 슬로바키아, 일본, 체코 각 1개
#plt.figure(figsize=(14, 5))
#group03bar = sns.barplot(data=group03, x='해외공장 운영국가', y='집계결과', width=0.5, color='magenta')
#for i in group03bar.containers:
#    group03bar.bar_label(i, fontsize=8)
#plt.grid(True, linewidth=0.5, linestyle=':')
#plt.savefig("시각화/기업일반 사항_해외공장 운영국가 현황.png", dpi=300)
print()
# 기업규모별 현황 시각화
print("1. 귀사의 규모를 선택해 주십시오.")
group1 = b.groupby('기업규모')['기업규모'].count().reset_index(name='집계결과').sort_values(by='집계결과', ascending=False)
#plt.figure(figsize=(12, 5))
#group1bar = sns.barplot(data=group1, x='기업규모', y='집계결과', width=0.5, color='magenta')
#group1bar.set(xlabel = '기업규모', ylabel='집계결과')
#for i in group1bar.containers:
#    group1bar.bar_label(i, fontsize=8, )
#plt.grid(True, linewidth=0.5, linestyle=':')
#plt.savefig("시각화/1_기업규모_집계현황.png", dpi=300)
print()
#주요 수출대상국 현황
print("2. 귀사의 주요 수출 대상국은 어디입니까?")
outnation = b['주요수출 대상국'].dropna()
outnation_list = split_items(outnation)
outnation_df = pd.DataFrame({'주요수출 대상국': outnation_list})
group2 = outnation_df.groupby('주요수출 대상국')['주요수출 대상국'].count().reset_index(name='집계결과').sort_values(by='집계결과', ascending=False)
group2 = group2.loc[group2['집계결과'] > 1].copy() # 우크라이나,이스라엘,인도네시아,방글라데시,멕시코,중남미,필리핀,대만 등이 각 1개
plt.figure(figsize=(14, 5))
group2bar = sns.barplot(data=group2, x='주요수출 대상국', y='집계결과', width=0.5, color='magenta')
group2bar.set(xlabel = '주요수출 대상국', ylabel='집계결과')
for i in group2bar.containers:
    group2bar.bar_label(i, fontsize=8)
plt.grid(True, linewidth=0.5, linestyle=':')
plt.savefig("시각화/2_주요수출대상국_현황.png", dpi=300)
print()
#매출액 대비 수출비중 현황
print("3. 귀사의 수출 비중은 전체 매출의 몇 %입니까?")
group3 = b.groupby('매출액 대비 수출비중')['매출액 대비 수출비중'].count().reset_index(name='집계결과').sort_values(by='집계결과', ascending=False)
#plt.figure(figsize=(12, 5))
#group3bar = sns.barplot(data=group3, x='매출액 대비 수출비중', y='집계결과', width=0.5, color='magenta')
#group3bar.set(xlabel='매출액 대비 수출비중', ylabel='집계결과')
#for i in group3bar.containers:
#    group3bar.bar_label(i, fontsize=8)
#plt.grid(True, linewidth=0.5, linestyle=':')
#plt.savefig("시각화/3_전체매출액대비_수출비중.png", dpi=300)
print()
#관세정책 발효로 인한 어려움
print("4. 미 관세정책 발효로 인해 귀사에서 겪고 있는 주요 어려움은 무엇입니까?")
hardship = b['관세정책 발효로 인한 어려움'].dropna()
hardship_list = split_items(hardship)
hardship_df = pd.DataFrame({'관세정책 발효로 인한 어려움': hardship_list})
group4 = hardship_df.groupby('관세정책 발효로 인한 어려움')['관세정책 발효로 인한 어려움'].count().reset_index(name='집계결과').sort_values(by='집계결과', ascending=False)
group4 = group4.loc[group4['집계결과'] > 1] # 관세정책 원인으로 어려움 없음, 원자재 수급 어려움, 자금부족 각 1건 제외
#plt.figure(figsize=(16, 5))
#group4bar = sns.barplot(data=group4, x='관세정책 발효로 인한 어려움', y='집계결과', width=0.5, color='magenta')
#group4bar.set(xlabel='관세정책 발효로 인한 어려움', ylabel='집계결과')
#for i in group4bar.containers:
#    group4bar.bar_label(i, fontsize=8)
#plt.grid(True, linewidth=0.5, linestyle=':')
#plt.savefig("시각화/4_관세정책 발효로 인한 어려움.png", dpi=300)
print()
#기업차원 대응조치 현황
print("5. 귀사에서 관세정책에 대한 대응을 위해 시행한 조치가 있다면 무엇입니까?")
reaction = b['기업차원 대응조치'].dropna()
reaction_list = split_items(reaction)
reaction_df = pd.DataFrame({'기업차원 대응조치': reaction_list})
group5 = reaction_df.groupby('기업차원 대응조치')['기업차원 대응조치'].count().reset_index(name='집계결과').sort_values(by='집계결과', ascending=False)
group5 = group5.loc[group5['집계결과'] > 2] # 관세정책 추이관망(2), 대미 투자확대(2), 가격경쟁력 확보방안 모색(1), 원산지증명 재확인(1), 정책시행 전 수출(1) 제외
#plt.figure(figsize=(16, 5))
#group5bar = sns.barplot(data=group5, x='기업차원 대응조치', y='집계결과', width=0.5, color='magenta')
#group5bar.set(xlabel='기업차원 대응조치', ylabel='집계결과')
#for i in group5bar.containers:
#    group5bar.bar_label(i, fontsize=8)
#plt.grid(True, linewidth=0.5, linestyle=':')
#plt.savefig("시각화/5_기업차원 대응조치 현황.png", dpi=300)
print()
# 필요한 행정지원 현황
print("6. 정부(지자체)의 지원 정책이 필요한 부분은 무엇입니까?")
supports = b['필요한 행정지원'].dropna()
supports_list = split_items(supports)
supports_df = pd.DataFrame({'필요한 행정지원': supports_list})
group6 = supports_df.groupby('필요한 행정지원')['필요한 행정지원'].count().reset_index(name='집계결과').sort_values(by='집계결과', ascending=False)
# 가격인상, 법률지원, 베트남 정부의 세금,관세지원, 수출 지원 등은 응답수가 1건 이라 제외
#group6 = group6.loc[group6['집계결과'] > 1].copy()
#plt.figure(figsize=(14, 5))
#group6bar = sns.barplot(data=group6, x='필요한 행정지원', y='집계결과', width=0.5, color='magenta')
#group6bar.set(xlabel='필요한 행정지원', ylabel='집계결과')
#for i in group6bar.containers:
#    group6bar.bar_label(i, fontsize=8)
#plt.grid(True, linewidth=0.5, linestyle=':')
#plt.savefig("시각화/6_필요한 행정지원 현황2.png", dpi=300)
print()
#수출지원 정책정보 입수경로
print("7. 귀사가 부산시가 추진하는 수출지원정책에 대해 알게 되는 경로는 무엇인가요?")
supports = b['필요한 행정지원'].dropna()
inforoute = b['수출지원 정책정보 입수경로'].dropna()
inforoute_list = split_items(inforoute)
inforoute_df = pd.DataFrame({'수출지원 정책정보 입수경로': inforoute_list})
group7 = inforoute_df.groupby('수출지원 정책정보 입수경로')['수출지원 정책정보 입수경로'].count().reset_index(name='집계결과').sort_values(by='집계결과', ascending=False)
# 금융지원(2), 모름(2), 무응답(2), 물류지원(1), 방문(1), 베트남 대표무역사무소 직접 방문(1), 부산시 대표무역사무소 소개(1) 제외
group7 = group7.loc[group7['집계결과'] > 2].copy()
#plt.figure(figsize=(14, 5))
#group7bar = sns.barplot(data=group7, x='수출지원 정책정보 입수경로', y='집계결과', width=0.5, color='magenta')
#group7bar.set(xlabel='수출지원 정책정보 입수경로', ylabel='집계결과')
#for i in group7bar.containers:
#    group7bar.bar_label(i, fontsize=8)
#plt.grid(True, linewidth=0.5, linestyle=':')
#plt.savefig("시각화/7_수출지원 정책정보 입수경로 현황.png", dpi=300)