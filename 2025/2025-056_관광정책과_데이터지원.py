
import pandas as pd
import numpy as np

# 유입지 방문인구
pop_path = "D:\\02_사업관리\\2025년\\데이터 구매 및 활용\\12_적재확인\\01_생활인구\\"
# 카드이용
crd_path = "D:\\02_사업관리\\2025년\\데이터 구매 및 활용\\12_적재확인\\02_카드이용\\"


pop10 = pd.read_csv(pop_path + "kt_d_living_emd_inflow_202510.csv", sep="|",
                  dtype={'hcode': str, 'inflow_cd': str}, encoding="utf-8")
pop11 = pd.read_csv(pop_path + "kt_d_living_emd_inflow_202511.csv", sep="|",
                  dtype={'hcode': str, 'inflow_cd': str}, encoding="utf-8")

card10 = pd.read_csv(crd_path + "bccd_d_emd_202510.csv", sep="|", 
                     dtype={'hcode': str}, encoding="utf-8")
card11 = pd.read_csv(crd_path + "bccd_d_emd_202511.csv", sep="|", 
                     dtype={'hcode': str}, encoding="utf-8")

# print("10월 (축제)방문인구")
# pop10['gcode'] = pop10['hcode'].str[:5]
# inner = pop11.loc[(pop11['std_ymd'] >= 20251107) & (pop11['std_ymd'] <= 20251109) & (pop11['gcode'] == '26200') & (pop11['inflow_cd'].str.startswith('26200'))]
# outer = pop11.loc[(pop11['std_ymd'] >= 20251107) & (pop11['std_ymd'] <= 20251109) & (pop11['gcode'] == '26200') & (~pop11['inflow_cd'].str.startswith('26200'))]
# print(round(inner.groupby('gcode')['v_pop'].sum() / 24))
# print(round(outer.groupby('gcode')['v_pop'].sum() / 24))

print("10월 (비교)방문인구")
pop10['gcode'] = pop10['hcode'].str[:5]
inner = pop10.loc[(pop10['std_ymd'] >= 20251024) & (pop10['std_ymd'] <= 20251026) & (pop10['gcode'] == '26140') & (pop10['inflow_cd'].str.startswith('26140'))]
outer = pop10.loc[(pop10['std_ymd'] >= 20251024) & (pop10['std_ymd'] <= 20251026) & (pop10['gcode'] == '26140') & (~pop10['inflow_cd'].str.startswith('26140'))]
print(round(inner.groupby('gcode')['v_pop'].sum() / 24))
print(round(outer.groupby('gcode')['v_pop'].sum() / 24))

# print("11월 (축제)방문인구")
# pop11['gcode'] = pop11['hcode'].str[:5]
# inner = pop11.loc[(pop11['std_ymd'] >= 20251107) & (pop11['std_ymd'] <= 20251109) & (pop11['gcode'] == '26200') & (pop11['inflow_cd'].str.startswith('26200'))]
# outer = pop11.loc[(pop11['std_ymd'] >= 20251107) & (pop11['std_ymd'] <= 20251109) & (pop11['gcode'] == '26200') & (~pop11['inflow_cd'].str.startswith('26200'))]
# print(round(inner.groupby('gcode')['v_pop'].sum() / 24))
# print(round(outer.groupby('gcode')['v_pop'].sum() / 24))

# print("11월 (비교)방문인구")
# pop10['gcode'] = pop10['hcode'].str[:5]
# pop10 = pop10.loc[(pop10['std_ymd'] == 20251031) & (pop10['gcode'] == '26200')]
# pop11 = pop11.loc[(pop11['std_ymd'] <= 20251102) & (pop11['gcode'] == '26200')]

# (축제)기간이 걸쳐있는 경우
print("(축제)기간이 걸쳐있는 경우")
pop = pd.concat([pop10, pop11], ignore_index=True)
inner = pop.loc[(pop['std_ymd'] >= 20251031) & (pop['std_ymd'] <= 20251102) & (pop['gcode'] == '26140') & (pop['inflow_cd'].str.startswith('26140'))]
outer = pop.loc[(pop['std_ymd'] >= 20251031) & (pop['std_ymd'] <= 20251102) & (pop['gcode'] == '26140') & (~pop['inflow_cd'].str.startswith('26140'))]
print(round(inner.groupby('gcode')['v_pop'].sum() / 24))
print(round(outer.groupby('gcode')['v_pop'].sum() / 24))

# print("10월 카드이용(축제)")
# card10_1 = card10.loc[(card10['std_ymd'] >= 20251024) & (card10['std_ymd'] <= 20251026) & (card10['hcode'].str.startswith('26140'))]
# card10_1['gcode'] = card10_1['hcode'].str[:5]
# print(card10_1.groupby('gcode')[['amt','cnt']].sum())

print("10월 카드이용(비교)")
card10_2 = card10.loc[(card10['std_ymd'] >= 20251024) & (card10['std_ymd'] <= 20251026) & (card10['hcode'].str.startswith('26140'))]
card10_2['gcode'] = card10_2['hcode'].str[:5]
print(card10_2.groupby('gcode')[['amt','cnt']].sum())

# print("11월 카드이용(축제)")
# card11 = card11.loc[(card11['std_ymd'] >= 20251107) & (card11['std_ymd'] <= 20251109) & (card11['hcode'].str.startswith('26200'))]
# card11['gcode'] = card11['hcode'].str[:5]
# print(card11.groupby('gcode')[['amt','cnt']].sum())

# print("11월 카드이용(비교)")
# card11 = card11.loc[(card11['std_ymd'] <= 20251102) & (card11['hcode'].str.startswith('26200'))]
# card11['scode'] = card11['hcode'].str[:2]

# (축제)기간이 걸쳐있는 경우
print("(축제)기간이 걸쳐있는 경우")
card_1 = pd.concat([card10, card11], ignore_index=True)
card_1 = card_1.loc[(card_1['std_ymd'] >= 20251031) & (card_1['std_ymd'] <= 20251102) & (card_1['hcode'].str.startswith('26140'))]
card_1['gcode'] = card_1['hcode'].str[:5]
print(card_1.groupby('gcode')[['amt','cnt']].sum())