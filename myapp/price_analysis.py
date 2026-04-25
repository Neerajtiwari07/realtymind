import numpy as np

from .models import Property


def calculate_price_analysis(properties_queryset):
    prices = np.array(list(properties_queryset.values_list("price", flat=True)), dtype=float)

    if prices.size == 0:
        return {
            "minimum_price": None,
            "average_price": None,
            "maximum_price": None,
            "lowest_rent_property": None,
            "cheapest_properties": [],
        }

    lowest_rent_property = (
        properties_queryset.filter(property_type=Property.PROPERTY_TYPE_RENTAL_ROOM)
        .order_by("price")
        .first()
    )
    cheapest_properties = list(properties_queryset.order_by("price")[:5])

    return {
        "minimum_price": float(np.min(prices)),
        "average_price": float(np.mean(prices)),
        "maximum_price": float(np.max(prices)),
        "lowest_rent_property": lowest_rent_property,
        "cheapest_properties": cheapest_properties,
    }
