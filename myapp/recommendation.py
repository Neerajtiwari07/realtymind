import numpy as np

from .models import Property, PropertyFeedback


def _build_preference_scores(user):
    feedbacks = list(
        PropertyFeedback.objects.filter(user=user)
        .select_related("property")
        .values_list("property__location", "property__property_type", "action")
    )

    location_scores_raw = {}
    type_scores_raw = {}

    for location, property_type, action in feedbacks:
        label = 1 if action == PropertyFeedback.ACTION_LIKE else -1

        location_key = (location or "").strip().lower()
        type_key = property_type

        location_scores_raw.setdefault(location_key, []).append(label)
        type_scores_raw.setdefault(type_key, []).append(label)

    # Map preference score to [0, 1]. 0.5 means neutral/no history.
    location_scores = {
        key: (float(np.mean(values)) + 1.0) / 2.0 for key, values in location_scores_raw.items()
    }
    type_scores = {
        key: (float(np.mean(values)) + 1.0) / 2.0 for key, values in type_scores_raw.items()
    }
    return location_scores, type_scores, len(feedbacks)


def recommend_properties(user, budget=None, location=None, property_type=None, limit=5):
    properties_qs = Property.objects.all()

    if location:
        properties_qs = properties_qs.filter(location__icontains=location)
    if property_type:
        properties_qs = properties_qs.filter(property_type=property_type)

    properties = list(properties_qs[:200])
    if not properties:
        return [], 0

    location_scores, type_scores, feedback_count = _build_preference_scores(user)

    prices = np.array([float(item.price) for item in properties], dtype=float)
    if budget is None:
        budget_score = np.full(len(properties), 0.5)
    else:
        target_budget = float(budget)
        denominator = max(target_budget, 1.0)
        distance_ratio = np.abs(prices - target_budget) / denominator
        budget_score = np.clip(1.0 - distance_ratio, 0.0, 1.0)

    location_score = np.array(
        [location_scores.get((item.location or "").strip().lower(), 0.5) for item in properties],
        dtype=float,
    )
    property_type_score = np.array(
        [type_scores.get(item.property_type, 0.5) for item in properties],
        dtype=float,
    )

    total_score = 0.5 * budget_score + 0.25 * location_score + 0.25 * property_type_score
    sorted_indices = np.argsort(-total_score)

    recommendations = []
    for idx in sorted_indices[:limit]:
        property_item = properties[idx]
        score = float(total_score[idx] * 100.0)
        recommendations.append((property_item, round(score, 2)))

    return recommendations, feedback_count
