
# 내외국인 관광객 전통시장 카드이용 현황 집계
from dataConfig import Connect
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import glob

data_path = r"D:\02_사업관리\2026년\데이터 분석 컨설팅\20260212_관광마이스산업과\\"
code_path = r"D:\02_사업관리\코드자료\\"
output_path = r"D:\02_사업관리\2026년\데이터 분석 컨설팅\20260212_관광마이스산업과\03_시각화결과\\"
# 전통시장 코드
mkt_code = pd.read_csv(data_path + r"구군_전통시장현황.csv", sep=",", encoding="utf-8")

# 카드사 국적코드
nat_code = pd.read_csv(data_path + r"카드사_국적코드.csv", sep=",", encoding="utf-8")
# print(nat_code.head())
con_lists = set([con_nm for con_nm in nat_code['con_nm']])
# print(con_lists)

# 카드사 업종중분류 코드
ry_code = Connect.query(
    """SELECT ry_l_nm, ry_m_cd, ry_m_nm FROM purchase_data.l0bcc_bccd_sec_code""").drop_duplicates(keep='first')
# print(ry_code)

# 행정동코드
hjdong_code = pd.read_excel(code_path + r"행정경계코드\jscode20260301(말소코드포함)\jscode20260301(말소코드포함)\\KIKcd_H.20260301(말소코드포함).xlsx")
# print(hjdong_code)
hjdong_code['행정동코드'] = hjdong_code['행정동코드'].astype(str)
hjdong_code['cln_cty_cd'] = hjdong_code['행정동코드'].str[:2]
hjdong_code = hjdong_code[(hjdong_code['cln_cty_cd'] != '26') & (~hjdong_code['시도명'].str.contains('출장소')) & (~hjdong_code['시도명'].str.contains('직할시'))]
hjdong_code = hjdong_code[['cln_cty_cd', '시도명']].drop_duplicates()
hjdong_code.rename(columns={'시도명': 'cln_cty_nm'}, inplace=True)

sql = """SELECT std_ym, mkt_cd, ry_l_cd, ry_m_cd, cln_cty_cd, CAST(amt as BIGINT), CAST(cnt AS BIGINT) 
         FROM purchase_data.l0bcc_bccd_m_trmkt_emd WHERE SUBSTR(std_ym,1,4) BETWEEN '2023' AND '2025'
      """

# 내국인 유입시도(권역)별 카드이용 데이터프레임
korean = Connect.query(sql)

# 외국인 국적(대륙)별 카드이요 데이터프레임
data_lists = glob.glob(data_path + r"전통시장 외국인 소비데이터\\*.csv", recursive=True)
values = []
for data in data_lists:
    values.append(pd.read_csv(data, dtype={'std_yy': str}, encoding="utf-8"))
foreign = pd.concat(values, ignore_index=True)
foreign.rename(columns={'std_yy': 'std_year'}, inplace=True)

def code_convert(df):
    if 'std_year' in df.columns:
        pass
    else:
        df['std_year'] = df['std_ym'].str[:4]
    df = pd.merge(df, mkt_code, how="left", on="mkt_cd")
    df = pd.merge(df, ry_code, how="left", on="ry_m_cd")
    if 'cln_cty_cd' in df.columns:
        df = pd.merge(df, hjdong_code, how="left", on="cln_cty_cd")
    if 'nat_cd' in df.columns:
        df = pd.merge(df, nat_code, how="left", on="nat_cd")
    return df

# 시도별 권역 사전
region_dict = {
    '서울특별시': '수도권', '인천광역시': '수도권', '경기도': '수도권', 
    '강원도': '강원권', '강원특별자치도': '강원권',
    '충청북도': '충청권', '충청남도': '충청권', '대전광역시': '충청권', '세종특별자치시': '충청권',
    '경상북도': '영남권', '대구광역시': '영남권',
    '전라북도': '호남권', '전북특별자치도': '호남권', '전라남도': '호남권', '광주광역시': '호남권',
    '경상남도': '동남권', '울산광역시': '동남권',
    '제주도': '제주권', '제주특별자치도': '제주권', 
}
region_lists = [value for value in region_dict.values()]

# 업종 순서 (XLSX 차트 기준)
BIZ_ORDER = ['미용', '음식/주점', '음식료픔', '의료', '의류/잡화', '생활', '여행/숙박', '유통', '여가/문화', '자동차', '교육']
 
# 구군 순서
GU_ORDER = ['중구', '서구', '동구', '영도구', '부산진구', '동래구', '남구', '북구', '해운대구', '사하구', '금정구', '강서구', '연제구', '수영구', '사상구', '기장군']
 
# Plotly 색상 팔레트 (업종별 구분)
COLORS = [
    '#4472C4', '#ED7D31', '#A5A5A5', '#FFC000', '#5B9BD5',
    '#70AD47', '#264478', '#9B59B6', '#FF6384', '#36A2EB', '#2ECC71'
]

def create_stacked_bar(pivot_df, value_label, gu_order=GU_ORDER, biz_order=BIZ_ORDER):
    fig = go.Figure()
    categories = [g for g in gu_order if g in pivot_df.index]

    for i, biz in enumerate(biz_order):
        if biz not in pivot_df.columns:
            continue
        values = [pivot_df.loc[g, biz] if g in pivot_df.index else 0 for g in categories]
        fig.add_trace(go.Bar(
            name=biz, x=categories, y=values, marker_color=COLORS[i % len(COLORS)],
            hovertemplate=f'<b>{biz}</b><br>구군: %{{x}}<br>{value_label}: %{{y:,.0f}}<extra></extra>'))
        fig.update_layout(
            barmode='stack',
            title=dict(font=dict(size=16, family='Malgun Gothic, sans-serif')),
            xaxis=dict(title='구군', tickangle=-45, tickfont=dict(size=11, family='Malgun Gothic, sans-serif')),
            yaxis=dict(title=value_label, tickformat=',', tickfont=dict(size=11)),
            legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='center', x=0.5, font=dict(size=10, family='Malgun Gothic, sans-serif')),
            plot_bgcolor='white', paper_bgcolor='white', width=1100, height=600, margin=dict(t=100, b=100))
        fig.update_xaxes(showgrid=False)
        fig.update_yaxes(showgrid=True, gridcolor='lightgray')
        return fig

def region_chart(df, year, region):
    df = code_convert(df)
    df['region_nm'] = df['cln_cty_nm'].map(region_dict)
    df = df[(df['std_year'] == str(year)) & (df['region_nm'] == region)]
    pivot_amt = df.pivot_table(index='gname', columns='ry_l_nm', values='amt', aggfunc='sum', fill_value=0)
    pivot_cnt = df.pivot_table(index='gname', columns='ry_l_nm', values='cnt', aggfunc='sum', fill_value=0)
    fig_amt = create_stacked_bar(pivot_amt, '이용금액(원)')
    fig_cnt = create_stacked_bar(pivot_cnt, '이용건수(건)')
    return fig_amt, fig_cnt

def nation_chart(df, year, continent):
    df = code_convert(df)
    df = df[(df['std_year'] == str(year)) & (df['con_nm'] == continent)]
    pivot_amt = df.pivot_table(index='gname', columns='ry_l_nm', values='amt', aggfunc='sum', fill_value=0)
    pivot_cnt = df.pivot_table(index='gname', columns='ry_l_nm', values='cnt', aggfunc='sum', fill_value=0)
    fig_amt = create_stacked_bar(pivot_amt, '이용금액(원)')
    fig_cnt = create_stacked_bar(pivot_cnt, '이용건수(건)')
    return fig_amt.show(), fig_cnt.show()

if __name__ == "__main__":
    for year in range(2023, 2026):
        for region in region_lists:
            fig_amt, fig_cnt = region_chart(korean, year, region)
            fig_amt.write_html(output_path + f"{year}년 {region} 이용금액 현황.html")
            fig_cnt.write_html(output_path + f"{year}년 {region} 이용건수 현황.html")
        for con in con_lists:
            try:
                fig_amt, fig_cnt = nation_chart(foreign, year, con)
                fig_amt.write_html(output_path + f"{year}년 {con} 이용금액 현황.html")
                fig_cnt.write_html(output_path + f"{year}년 {con} 이용건수 현황.html")
            except:
                pass