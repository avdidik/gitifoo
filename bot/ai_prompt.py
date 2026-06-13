SYSTEM_PROMPT = (
    "Ты Лёха AI — участник конкурса прогнозов на ЧМ-2026. "
    "Ты умный аналитик с характером: иногда ставишь на нестандартный счёт или веришь в аутсайдера. "
    "За точный счёт получаешь 3 балла, за точную разницу мячей — 2, за угаданный исход — 1, иначе 0. "
    "Для каждого матча дай краткое обоснование (3–5 предложений). "
    "Используй свои знания о командах и статистику текущего турнира из сообщения пользователя. "
    "Отвечай строго валидным JSON без пояснений вне JSON:\n"
    '{"predictions": [{"match_id": 42, "pred_home": 2, "pred_away": 1, "reason": "..."}, ...]}'
)


def build_prompt(matches: list[dict], standings: list[dict]) -> str:
    lines = ["Сегодня игровой день. Матчи:"]
    for m in matches:
        lines.append(f"- match_id={m['id']}: {m['team_home']} vs {m['team_away']}")

    if standings:
        lines.append("\nТекущее положение в группах (место / команда / И В Н П / очки / голы / РГ):")
        current_group = None
        pos = 0
        for row in standings:
            if row["match_group"] != current_group:
                current_group = row["match_group"]
                lines.append(f"\nГруппа {current_group}:")
                pos = 0
            pos += 1
            gd = int(row["gd"])
            gd_str = f"+{gd}" if gd > 0 else str(gd)
            lines.append(
                f"  {pos}. {row['team']} — "
                f"И:{row['gp']} В:{row['w']} Н:{row['d']} П:{row['l']} | "
                f"{row['pts']} оч | {row['gf']}:{row['ga']} (РГ {gd_str})"
            )
    else:
        lines.append("\nТурнир только начался, исторических данных нет.")

    return "\n".join(lines)
