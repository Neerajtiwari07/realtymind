import re

from django.db.models import Count

from .models import Property


def _extract_location(message):
    text = message.lower().strip()
    if "this area" in text:
        return "this area"

    match = re.search(
        r"\bin\s+([a-z0-9 ,\-]+?)(?:\s+(under|below|less than|above|over|more than|between)\b|$)",
        text,
    )
    if match:
        return match.group(1).strip()
    return None


def _extract_property_type(message):
    text = message.lower()
    mapping = {
        "plot": Property.PROPERTY_TYPE_PLOT,
        "land": Property.PROPERTY_TYPE_LAND,
        "flat": Property.PROPERTY_TYPE_FLAT,
        "rental room": Property.PROPERTY_TYPE_RENTAL_ROOM,
        "rent room": Property.PROPERTY_TYPE_RENTAL_ROOM,
        "room": Property.PROPERTY_TYPE_RENTAL_ROOM,
    }
    for keyword, property_type in mapping.items():
        if keyword in text:
            return property_type
    return None


def _extract_budget_intent(message):
    text = message.lower()
    low_budget_keywords = ["cheap", "low", "low budget", "affordable", "rent"]
    high_budget_keywords = ["premium", "luxury", "high budget", "expensive"]

    if any(keyword in text for keyword in low_budget_keywords):
        return "low"
    if any(keyword in text for keyword in high_budget_keywords):
        return "high"
    return None


def _to_number(value_text):
    return int(value_text.replace(",", ""))


def _extract_price_range(message):
    text = message.lower()

    between_match = re.search(r"\bbetween\s+([\d,]+)\s+and\s+([\d,]+)\b", text)
    if between_match:
        min_price = _to_number(between_match.group(1))
        max_price = _to_number(between_match.group(2))
        if min_price > max_price:
            min_price, max_price = max_price, min_price
        return min_price, max_price

    under_match = re.search(r"\b(under|below|less than)\s+([\d,]+)\b", text)
    if under_match:
        return None, _to_number(under_match.group(2))

    above_match = re.search(r"\b(above|over|more than)\s+([\d,]+)\b", text)
    if above_match:
        return _to_number(above_match.group(2)), None

    return None, None


def detect_intent(message):
    text = message.lower().strip()
    if not text:
        return "empty"
    if re.search(r"\b(hi|hello|hey)\b", text):
        return "greeting"
    if any(word in text for word in ["flat", "plot", "land", "room", "rent", "cheap", "property"]):
        return "property_search"
    return "unknown"


def search_properties_by_message(message, user):
    intent = detect_intent(message)
    if intent != "property_search":
        return intent, [], "Please ask about properties, for example: 'low rent flat in sector 45'."

    property_type = _extract_property_type(message)
    budget_intent = _extract_budget_intent(message)
    location = _extract_location(message)
    min_price, max_price = _extract_price_range(message)

    properties = Property.objects.all()

    if property_type:
        properties = properties.filter(property_type=property_type)

    if location and location != "this area":
        properties = properties.filter(location__icontains=location)
    elif location == "this area":
        common_user_location = (
            Property.objects.filter(owner=user)
            .values("location")
            .annotate(total=Count("id"))
            .order_by("-total", "location")
            .first()
        )
        if common_user_location:
            properties = properties.filter(location__icontains=common_user_location["location"])

    if min_price is not None:
        properties = properties.filter(price__gte=min_price)
    if max_price is not None:
        properties = properties.filter(price__lte=max_price)

    if budget_intent == "low":
        properties = properties.order_by("price")
    elif budget_intent == "high":
        properties = properties.order_by("-price")
    else:
        properties = properties.order_by("-created_at")

    top_properties = list(properties[:5])
    return "property_search", top_properties, None


def format_chatbot_reply(intent, properties, fallback_message):
    if intent == "empty":
        return "Type a property query, for example: 'cheap land in Jaipur'."

    if intent == "greeting":
        return "Hello! You can ask me things like: 'low rent flat' or 'cheap land in this area'."

    if intent != "property_search":
        return fallback_message or "I could not understand your request."

    if not properties:
        return "No matching property found. Try changing property type, location, or budget words."

    lines = ["I found these properties:"]
    for item in properties:
        lines.append(
            f"- {item.get_property_type_display()} | {item.title} | {item.location} | Rs. {item.price}"
        )
    return "\n".join(lines)
