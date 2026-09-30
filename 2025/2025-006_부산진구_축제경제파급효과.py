# 분석라이브러리
import pandas as pd

# 시각화를 위한 라이브러리
import matplotlib.pyplot as plt
import seaborn as sns

plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False  # 마이너스 부호 깨짐 방지
plt.rcParams['font.size']=11
sns.set_style("whitegrid")


df = pd.read_csv("분석용데이터/주별_생활인구_카드소비_데이터.csv", dtype={'weekday': str, 'weeknum': str}, encoding="utf-8")

df_latest = df.sort_values(by=['weeknum', 'weekday', 'hour'])

# 축제 전과 축제 기간 각각 변화율 계산 (전주 대비 변화율)
df_latest["pop_change_rate"] = round(df_latest.groupby(["festival_peroid", "weekday", "hour"])["population"].pct_change() * 100, 2)
df_latest["amt_change_rate"] = round(df_latest.groupby(["festival_peroid", "weekday", "hour"])["amt"].pct_change() * 100, 2)

# 축제 전과 축제 기간 각각 변화율 요약
df_summary = df_latest.groupby(["festival_peroid", "weeknum"]).agg({
    "pop_change_rate": "mean",
    "amt_change_rate": "mean"
}).reset_index()



# 그래프 설정
fig, ax = plt.subplots(2, 1, figsize=(12, 7))

# 생활인구 변화율 막대 그래프
sns.barplot(data=df_summary, x="weeknum", y="pop_change_rate", hue="festival_peroid", ax=ax[0], palette=["blue", "orange"])
ax[0].set_facecolor("None")
ax[0].grid(color="gray", linestyle="--", linewidth=0.5)
ax[0].set_xlabel("주차")
ax[0].set_ylabel("생활인구 변화율")
ax[0].legend(title="축제여부", labels=["축제기간 전", "축제기간"])
ax[0].grid(axis="y")

# 카드 소비금액 변화율 막대 그래프
sns.barplot(data=df_summary, x="weeknum", y="amt_change_rate", hue="festival_peroid", ax=ax[1], palette=["blue", "orange"])
ax[1].set_facecolor("None")
ax[1].grid(color="gray", linestyle="--", linewidth=0.5)
ax[1].set_xlabel("주차")
ax[1].set_ylabel("카드소비 변화율")
ax[1].legend(title="축제여부", labels=["축제기간 전", "축제기간"])
ax[1].grid(axis="y")

# 그래프 출력
plt.show()
