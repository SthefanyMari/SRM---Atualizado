from collections import Counter

from app.models import Content, Interaction, RecommendationFeedback, UserPreference


INTERACTION_WEIGHTS = {
    "view": 0.08,
    "click": 0.14,
    "rating": 0.20,
    "recommendation": 0.02,
}


def rank_contents(
    contents: list[Content],
    preference: UserPreference | None,
    interactions: list[Interaction],
    feedbacks: list[RecommendationFeedback] | None = None,
) -> list[tuple[Content, float, str]]:
    profile = preference.profile if preference else {}
    preferred_domains = set(profile.get("preferred_domains", []))
    preferred_categories = {item.lower() for item in profile.get("preferred_categories", [])}

    domain_history: Counter[str] = Counter()
    category_history: Counter[str] = Counter()
    interacted_content_ids: set[int] = set()
    for interaction in interactions:
        if interaction.content is None:
            continue
        if interaction.interaction_type != "recommendation":
            interacted_content_ids.add(interaction.content_id)
        weight = INTERACTION_WEIGHTS.get(interaction.interaction_type, 0.03)
        if interaction.interaction_type == "rating" and interaction.value:
            weight *= max(interaction.value / 5.0, 0.2)
        domain_history[interaction.content.domain] += weight
        category_history[interaction.content.category.lower()] += weight

    ranked: list[tuple[Content, float, str]] = []
    feedback_by_content = {item.content_id: item.relevant for item in (feedbacks or [])}
    for content in contents:
        score = 0.25
        reasons: list[str] = []
        if content.domain in preferred_domains:
            score += 0.80
            reasons.append("combina com um domínio escolhido por você")
        elif preferred_domains:
            score -= 0.35
        if content.category.lower() in preferred_categories:
            score += 0.25
            reasons.append("faz parte de uma categoria que você prefere")
        if domain_history[content.domain]:
            score += min(domain_history[content.domain], 0.25)
            reasons.append("é parecido com conteúdos que você acessou")
        if category_history[content.category.lower()]:
            score += min(category_history[content.category.lower()], 0.18)
        if content.id in interacted_content_ids:
            score -= 0.10
        if feedback_by_content.get(content.id) is True:
            score += 0.55
            reasons.append("você marcou este conteúdo como relevante")
        elif feedback_by_content.get(content.id) is False:
            score -= 1.10

        reason = ", ".join(dict.fromkeys(reasons)) or "é uma opção variada do catálogo"
        ranked.append((content, round(max(score, 0.01), 4), reason.capitalize() + "."))

    return sorted(ranked, key=lambda item: (-item[1], item[0].title.lower()))
