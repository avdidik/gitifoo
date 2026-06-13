import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from db import get_daily_points, get_matches_predictions, get_scores_by_stage, get_standings, normalize_accuracy

COLORS = ["#F21B54", "#4ECBD9", "#F29D35", "#4E63D9", "#172573"]

PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#F1F5F9", size=15),
    xaxis=dict(showgrid=False, linecolor="#2D3148", tickfont=dict(size=14)),
    yaxis=dict(showgrid=False, linecolor="#2D3148", rangemode="tozero", tickfont=dict(size=14)),
    legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=14)),
    margin=dict(l=0, r=0, t=30, b=0),
)

MONTHS = ["янв", "фев", "мар", "апр", "май", "июн", "июл", "авг", "сен", "окт", "ноя", "дек"]

st.set_page_config(page_title="FWC 2026", layout="wide")

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

st.title("FWC 2026")

standings = get_standings()
tab1, tab2 = st.tabs(["Турнир", "Матчи"])

# ── Tab 1: Tournament ────────────────────────────────────────────────────────

with tab1:
    if standings.empty:
        st.info("Данных пока нет — игровые дни ещё не завершены.")
    else:
        # --- Standings ---
        st.subheader("Таблица очков")
        display = standings.copy()
        display.index = range(1, len(display) + 1)
        display.index.name = "№"
        display.columns = ["Участник", "Очки", "Точный", "Разница", "Победитель", "Мимо"]
        st.dataframe(display, use_container_width=True)

        # Canonical participant order — used to keep colors consistent across all charts
        players = standings["name"].tolist()
        NAME_ORDER = {"name": players}

        # --- Race Chart ---
        st.subheader("Гонка очков")
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
                category_orders=NAME_ORDER,
                labels={"game_date": "", "cumpoints": "Очки", "name": "Участник"},
            )
            fig.update_layout(legend_title_text="", hovermode="x unified", **PLOTLY_LAYOUT)
            fig.update_xaxes(tickformat="%d %b", dtick="D1")
            st.plotly_chart(fig, use_container_width=True)

        # --- Component comparison ---
        st.subheader("Из чего складываются очки")
        melted = standings.melt(
            id_vars=["name"],
            value_vars=["exact", "diff", "winner", "miss"],
            var_name="type",
            value_name="count",
        )
        melted["type"] = melted["type"].map({
            "exact": "Точный счёт (3)",
            "diff": "Разница (2)",
            "winner": "Победитель (1)",
            "miss": "Мимо (0)",
        })
        fig2 = px.bar(
            melted,
            x="type",
            y="count",
            color="name",
            barmode="group",
            color_discrete_sequence=COLORS,
            category_orders=NAME_ORDER,
            labels={"type": "", "count": "Матчей", "name": "Участник"},
        )
        fig2.update_layout(legend_title_text="", **PLOTLY_LAYOUT)
        st.plotly_chart(fig2, use_container_width=True)

        # --- Accuracy stacked bar ---
        st.subheader("Точность (доля типов)")
        normalized = normalize_accuracy(melted)
        fig3 = px.bar(
            normalized,
            x="name",
            y="pct",
            color="type",
            text="pct",
            category_orders=NAME_ORDER,
            labels={"name": "Участник", "pct": "%", "type": ""},
            color_discrete_map={
                "Точный счёт (3)": "#4ECBD9",
                "Разница (2)": "#4E63D9",
                "Победитель (1)": "#F29D35",
                "Мимо (0)": "#F21B54",
            },
        )
        fig3.update_traces(texttemplate="%{text}%", textposition="inside")
        fig3.update_layout(barmode="stack", legend_title_text="", yaxis_ticksuffix="%", **PLOTLY_LAYOUT)
        st.plotly_chart(fig3, use_container_width=True)

        # --- Per-player drill-down ---
        st.subheader("Детали по участнику")
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

        daily = get_daily_points()
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

# ── Tab 2: Matches ───────────────────────────────────────────────────────────

with tab2:
    raw = get_matches_predictions()

    if raw.empty:
        st.info("Матчей пока нет.")
    else:
        # Convert kickoff to Moscow time (UTC+3)
        raw["kickoff_at"] = pd.to_datetime(raw["kickoff_at"], utc=True)
        raw["dt_msk"] = raw["kickoff_at"] + pd.Timedelta(hours=3)
        raw["дата"] = raw["dt_msk"].apply(lambda d: f"{d.day} {MONTHS[d.month - 1]}")
        raw["время"] = raw["dt_msk"].dt.strftime("%H:%M")

        # Format result, prediction and points as strings
        raw["результат_str"] = raw.apply(
            lambda r: f"{int(r.result_home)}:{int(r.result_away)}" if pd.notna(r.result_home) else "—",
            axis=1,
        )
        raw["pred_str"] = raw.apply(
            lambda r: f"{int(r.pred_home)}:{int(r.pred_away)}" if pd.notna(r.pred_home) else "—",
            axis=1,
        )
        raw["pts_str"] = raw["points"].apply(lambda x: str(int(x)) if pd.notna(x) else "—")

        # Base: one row per match, sorted by kickoff
        first = raw.drop_duplicates("match_id").sort_values("kickoff_at")
        base = first[["match_id", "match_group", "team_home", "team_away", "дата", "время", "результат_str"]].copy()
        base["Группа"] = base["match_group"].fillna("ПО")
        base["Матч"] = base["team_home"] + " — " + base["team_away"]
        base = base.set_index("match_id")[["Группа", "Матч", "дата", "время", "результат_str"]]
        base.columns = ["Группа", "Матч", "Дата", "Время МСК", "Результат"]

        player_order = standings["name"].tolist() if not standings.empty else sorted(raw["participant_name"].unique())

        # Index raw by match_id × participant for fast lookup
        raw_idx = raw.set_index(["match_id", "participant_name"])

        # Build one dict per row (MultiIndex columns, no match_id in display)
        base_cols = [("", "Группа"), ("", "Матч"), ("", "Дата"), ("", "Время МСК"), ("", "Результат")]
        player_cols = [(name.split()[-1], sub) for name in player_order for sub in ("прогноз", "балл")]

        rows = []
        for _, m in first.iterrows():
            mid = m["match_id"]
            r: dict = {
                ("", "Группа"):     m["match_group"] or "ПО",
                ("", "Матч"):       f"{m['team_home']} — {m['team_away']}",
                ("", "Дата"):       m["дата"],
                ("", "Время МСК"):  m["время"],
                ("", "Результат"):  m["результат_str"],
            }
            for name in player_order:
                short = name.split()[-1]
                try:
                    p = raw_idx.loc[(mid, name)]
                    r[(short, "прогноз")] = p["pred_str"]
                    r[(short, "балл")]    = p["pts_str"]
                except KeyError:
                    r[(short, "прогноз")] = "—"
                    r[(short, "балл")]    = "—"
            rows.append(r)

        # Totals row
        totals: dict = {k: "" for k in base_cols + player_cols}
        totals[("", "Группа")] = "ИТОГО"
        for name in player_order:
            pts = int(raw[raw["participant_name"] == name]["points"].sum())
            totals[(name.split()[-1], "балл")] = str(pts)
        rows.append(totals)

        display = pd.DataFrame(rows, columns=pd.MultiIndex.from_tuples(base_cols + player_cols))

        # Full-page height: no internal scroll
        height = len(display) * 35 + 60
        st.dataframe(display, use_container_width=True, height=height)
