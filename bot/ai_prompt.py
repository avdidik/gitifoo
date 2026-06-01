SYSTEM_PROMPT = (
    "Ты Лёха AI — участник конкурса прогнозов на ЧМ-2026. "
    "Ты умный аналитик, но с характером: иногда ставишь на нестандартный счёт "
    "или веришь в аутсайдера. Анализируй данные турнира, но не бойся рискнуть. "
    "Отвечай строго JSON-массивом без пояснений."
)


def build_prompt(matches: list[dict], standings: list[dict]) -> str:
    lines = ["Сегодня игровой день. Матчи:"]
    for m in matches:
        lines.append(f"- match_id={m['id']}: {m['team_home']} vs {m['team_away']}")

    if standings:
        lines.append("\nТекущая статистика турнира по группам:")
        current_group = None
        for row in standings:
            if row["match_group"] != current_group:
                current_group = row["match_group"]
                lines.append(f"Группа {current_group}:")
            lines.append(
                f"  {row['team']} — {row['pts']} очков (GF:{row['gf']}, GA:{row['ga']})"
            )
    else:
        lines.append("\nТурнир только начался, исторических данных нет.")

    lines.append(
        "\nПредскажи счёт каждого матча. Формат ответа:\n"
        '[{"match_id": 42, "pred_home": 2, "pred_away": 1}, ...]'
    )
    return "\n".join(lines)
