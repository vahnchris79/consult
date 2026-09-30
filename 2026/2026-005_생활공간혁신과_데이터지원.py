
# 세븐브릿지투어 성과보고 보도자료 내 외국인 주요관광분야 9월 한달 지출액 요청

import pandas as pd

data_path = r"D:\02_사업관리\2025년\데이터 구매 및 활용\12_적재확인\02_카드이용\\"
df = pd.read_csv(data_path + "bccd_m_tour_fore_202509.csv", sep="|", encoding="utf-8")

print(df.info())