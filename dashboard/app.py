import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from db import get_daily_points, get_scores_by_stage, get_standings, normalize_accuracy

COLORS = ["#818CF8", "#34D399", "#F472B6", "#FBBF24"]

PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#F1F5F9", size=15),
    xaxis=dict(showgrid=False, linecolor="#2D3148"),
    yaxis=dict(showgrid=False, linecolor="#2D3148", rangemode="tozero"),
    legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=14)),
    margin=dict(l=0, r=0, t=30, b=0),
)

st.set_page_config(page_title="FWC 2026", page_icon="⚽", layout="wide")

st.markdown("""
<style>
[data-testid="stMetric"] {
    background: #1E2130;
    border-radius: 12px;
    padding: 16px 20px;
}
[data-testid="stMetricValue"] { color: #818CF8; }
section[data-testid="stSidebar"] { background: #1E2130; }
[data-testid="stDataFrame"] * { font-size: 16px !important; }
</style>
""", unsafe_allow_html=True)

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
    daily["game_date"] = pd.to_datetime(daily["game_date"]).dt.date
    fig = px.line(
        daily,
        x="game_date",
        y="cumpoints",
        color="name",
        markers=True,
        color_discrete_sequence=COLORS,
        labels={"game_date": "", "cumpoints": "Очки", "name": "Участник"},
    )
    fig.update_layout(legend_title_text="", hovermode="x unified", **PLOTLY_LAYOUT)
    fig.update_xaxes(tickformat="%d %b", dtick="D1")
    st.plotly_chart(fig, use_container_width=True)

# --- Component comparison ---
st.subheader("📊 Из чего складываются очки")
melted = standings.melt(
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
    color_discrete_sequence=COLORS,
    labels={"type": "", "count": "Матчей", "name": "Участник"},
)
fig2.update_layout(legend_title_text="", **PLOTLY_LAYOUT)
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
        "⭐ Точный счёт (3)": "#818CF8",
        "🟢 Разница (2)": "#34D399",
        "🟡 Победитель (1)": "#FBBF24",
        "❌ Мимо (0)": "#F472B6",
    },
)
fig3.update_traces(texttemplate="%{text}%", textposition="inside")
fig3.update_layout(barmode="stack", legend_title_text="", yaxis_ticksuffix="%", **PLOTLY_LAYOUT)
st.plotly_chart(fig3, use_container_width=True)

# --- Per-player drill-down ---
st.subheader("🔍 Детали по участнику")
players = standings["name"].tolist()
selected = st.selectbox("Выбери участника", players)

p_row = standings[standings["name"] == selected].iloc[0]
total = int(p_row["total_points"])
n_matches = int(p_row[["exact", "diff", "winner", "miss"]].sum())
avg = round(total / n_matches, 2) if n_matches > 0 else 0

col1, col2, col3 = st.columns(3)
col1.metric("Всего очков", total)
col2.metric("Матчей сыграно", n_matches)
col3.metric("Очков за матч", avg)

if not daily.empty:
    p_daily = daily[daily["name"] == selected].sort_values("game_date")
    if not p_daily.empty:
        best = p_daily.loc[p_daily["day_points"].idxmax()]
        worst = p_daily.loc[p_daily["day_points"].idxmin()]
        col4, col5 = st.columns(2)
        col4.metric("Лучший день", str(best["game_date"]), f"{int(best['day_points'])} очков")
        col5.metric("Худший день", str(worst["game_date"]), f"{int(worst['day_points'])} очков")

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
