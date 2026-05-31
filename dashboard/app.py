import pandas as pd
import plotly.express as px
import streamlit as st

from db import get_daily_points, get_scores_by_stage, get_standings, normalize_accuracy

st.set_page_config(page_title="FWC 2026", page_icon="⚽", layout="wide")
st.title("⚽ FWC 2026 — Турнир")

# --- Standings ---
st.subheader("🏆 Таблица очков")
standings = get_standings()

if standings.empty:
    st.info("Данных пока нет — игровые дни ещё не завершены.")
    st.stop()

display = standings.copy()
display.index = range(1, len(display) + 1)
display.index.name = "№"
display.columns = ["Участник", "Очки", "⭐ Точный", "🟢 Разница", "🟡 Победитель", "❌ Мимо"]
st.dataframe(display, use_container_width=True)

# --- Race Chart ---
st.subheader("📈 Гонка очков")
daily = get_daily_points()

if daily.empty:
    st.info("Ещё нет завершённых игровых дней.")
else:
    fig = px.line(
        daily,
        x="game_date",
        y="cumpoints",
        color="name",
        markers=True,
        labels={"game_date": "Дата", "cumpoints": "Очки (накопленные)", "name": "Участник"},
    )
    fig.update_layout(legend_title_text="", hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)

# --- Component comparison ---
st.subheader("📊 Из чего складываются очки")
melted = standings.rename(columns={
    "Участник": "name", "Очки": "total_points",
    "⭐ Точный": "exact", "🟢 Разница": "diff",
    "🟡 Победитель": "winner", "❌ Мимо": "miss",
}).melt(
    id_vars=["name"],
    value_vars=["exact", "diff", "winner", "miss"],
    var_name="type",
    value_name="count",
)
melted["type"] = melted["type"].map({
    "exact": "⭐ Точный счёт (3)",
    "diff": "🟢 Разница (2)",
    "winner": "🟡 Победитель (1)",
    "miss": "❌ Мимо (0)",
})
fig2 = px.bar(
    melted,
    x="type",
    y="count",
    color="name",
    barmode="group",
    labels={"type": "", "count": "Кол-во матчей", "name": "Участник"},
)
fig2.update_layout(legend_title_text="")
st.plotly_chart(fig2, use_container_width=True)

# --- Accuracy stacked bar ---
st.subheader("🎯 Точность (доля типов)")


normalized = normalize_accuracy(melted)
fig3 = px.bar(
    normalized,
    x="name",
    y="pct",
    color="type",
    text="pct",
    labels={"name": "Участник", "pct": "%", "type": ""},
    color_discrete_map={
        "⭐ Точный счёт (3)": "#FFD700",
        "🟢 Разница (2)": "#22C55E",
        "🟡 Победитель (1)": "#EAB308",
        "❌ Мимо (0)": "#EF4444",
    },
)
fig3.update_traces(texttemplate="%{text}%", textposition="inside")
fig3.update_layout(barmode="stack", legend_title_text="", yaxis_ticksuffix="%")
st.plotly_chart(fig3, use_container_width=True)

# --- Per-player drill-down ---
st.subheader("🔍 Детали по участнику")
players = standings["Участник"].tolist()
selected = st.selectbox("Выбери участника", players)

p_row = standings[standings["Участник"] == selected].iloc[0]
total = int(p_row["Очки"])
n_matches = int(p_row[["⭐ Точный", "🟢 Разница", "🟡 Победитель", "❌ Мимо"]].sum())
avg = round(total / n_matches, 2) if n_matches > 0 else 0

col1, col2, col3 = st.columns(3)
col1.metric("Всего очков", total)
col2.metric("Матчей сыграно", n_matches)
col3.metric("Очков за матч (avg)", avg)

if not daily.empty:
    p_daily = daily[daily["name"] == selected].sort_values("game_date")
    if not p_daily.empty:
        best = p_daily.loc[p_daily["day_points"].idxmax()]
        worst = p_daily.loc[p_daily["day_points"].idxmin()]
        col4, col5 = st.columns(2)
        col4.metric("Лучший день", str(best["game_date"].date()), f"{int(best['day_points'])} очков")
        col5.metric("Худший день", str(worst["game_date"].date()), f"{int(worst['day_points'])} очков")

stage_df = get_scores_by_stage()
if not stage_df.empty:
    p_stage = stage_df[stage_df["name"] == selected]
    if not p_stage.empty:
        st.write("**Точность по стадии турнира:**")
        stage_display = p_stage[["stage", "avg_points", "matches"]].copy()
        stage_display.columns = ["Стадия", "Avg очков/матч", "Матчей"]
        stage_display["Стадия"] = stage_display["Стадия"].map(
            {"group": "Групповой этап", "play_off": "Плей-офф"}
        )
        st.dataframe(stage_display.set_index("Стадия"), use_container_width=True)
