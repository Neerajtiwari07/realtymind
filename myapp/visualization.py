import base64
from io import BytesIO

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_pdf import PdfPages
from django.db.models import Avg


def _figure_to_base64(fig):
    buffer = BytesIO()
    fig.tight_layout()
    fig.savefig(buffer, format="png", dpi=120)
    buffer.seek(0)
    encoded = base64.b64encode(buffer.read()).decode("utf-8")
    buffer.close()
    plt.close(fig)
    return encoded


def _create_price_vs_area_figure(properties_queryset):
    prices = np.array(list(properties_queryset.values_list("price", flat=True)), dtype=float)
    areas = np.array(list(properties_queryset.values_list("area_sqft", flat=True)), dtype=float)
    if prices.size == 0 or areas.size == 0:
        return None

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.scatter(areas, prices, alpha=0.75, color="#0d6efd", edgecolors="black", linewidths=0.5)
    ax.set_title("Price vs Area")
    ax.set_xlabel("Area (sqft)")
    ax.set_ylabel("Price (Rs.)")
    return fig


def _create_location_avg_price_figure(properties_queryset):
    location_data = list(
        properties_queryset.values("location")
        .annotate(avg_price=Avg("price"))
        .order_by("location")
    )
    if not location_data:
        return None

    locations = [item["location"] for item in location_data]
    avg_prices = [float(item["avg_price"]) for item in location_data]

    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.bar(locations, avg_prices, color="#198754")
    ax.set_title("Location-wise Average Price")
    ax.set_xlabel("Location")
    ax.set_ylabel("Average Price (Rs.)")
    ax.tick_params(axis="x", rotation=25)
    for label in ax.get_xticklabels():
        label.set_horizontalalignment("right")
    return fig


def _create_property_type_price_figure(properties_queryset):
    type_data = list(
        properties_queryset.values("property_type")
        .annotate(avg_price=Avg("price"))
        .order_by("property_type")
    )
    if not type_data:
        return None

    labels = [item["property_type"].replace("_", " ").title() for item in type_data]
    avg_prices = [float(item["avg_price"]) for item in type_data]

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(labels, avg_prices, color="#fd7e14")
    ax.set_title("Property Type-wise Average Price")
    ax.set_xlabel("Property Type")
    ax.set_ylabel("Average Price (Rs.)")
    ax.tick_params(axis="x", rotation=20)
    for label in ax.get_xticklabels():
        label.set_horizontalalignment("right")
    return fig


def build_visual_reports(properties_queryset):
    price_vs_area_fig = _create_price_vs_area_figure(properties_queryset)
    location_avg_fig = _create_location_avg_price_figure(properties_queryset)
    property_type_avg_fig = _create_property_type_price_figure(properties_queryset)

    return {
        "price_vs_area_chart": _figure_to_base64(price_vs_area_fig) if price_vs_area_fig else None,
        "location_avg_price_chart": _figure_to_base64(location_avg_fig) if location_avg_fig else None,
        "property_type_avg_price_chart": _figure_to_base64(property_type_avg_fig)
        if property_type_avg_fig
        else None,
    }


def build_visual_report_pdf(properties_queryset, filters):
    prices = np.array(list(properties_queryset.values_list("price", flat=True)), dtype=float)
    total_properties = len(prices)

    buffer = BytesIO()
    with PdfPages(buffer) as pdf:
        summary_fig, summary_ax = plt.subplots(figsize=(8.27, 11.69))
        summary_ax.axis("off")

        filter_parts = []
        for key in ["location", "property_type", "min_price", "max_price"]:
            value = filters.get(key)
            if value:
                filter_parts.append(f"{key}: {value}")
        filter_text = ", ".join(filter_parts) if filter_parts else "No filters applied"

        lines = [
            "RealtyMind Property Visualization Report",
            "",
            f"Total properties: {total_properties}",
            f"Filters: {filter_text}",
            "",
        ]
        if total_properties > 0:
            lines.extend(
                [
                    f"Minimum Price: Rs. {float(np.min(prices)):.2f}",
                    f"Average Price: Rs. {float(np.mean(prices)):.2f}",
                    f"Maximum Price: Rs. {float(np.max(prices)):.2f}",
                ]
            )
        else:
            lines.append("No property data available for selected filters.")

        summary_ax.text(0.05, 0.95, "\n".join(lines), va="top", fontsize=12)
        pdf.savefig(summary_fig)
        plt.close(summary_fig)

        for creator in [
            _create_price_vs_area_figure,
            _create_location_avg_price_figure,
            _create_property_type_price_figure,
        ]:
            fig = creator(properties_queryset)
            if fig is not None:
                pdf.savefig(fig)
                plt.close(fig)

    buffer.seek(0)
    return buffer.read()
