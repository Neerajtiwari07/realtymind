from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.db.models import Count
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse

from .forms import (
    FraudComplaintForm,
    PropertyRatingForm,
    PropertyForm,
    PropertySearchForm,
    RecommendationForm,
    ServiceFeedbackForm,
    SignUpForm,
)
from .models import FraudComplaint, Property, PropertyFeedback, PropertyRating, ServiceFeedback
from .nlp import format_chatbot_reply, search_properties_by_message
from .notifications import send_new_property_email
from .price_analysis import calculate_price_analysis
from .recommendation import recommend_properties
from .visualization import build_visual_report_pdf, build_visual_reports


def home(request):
    return render(request, "myapp/home.html")


def about(request):
    return render(request, "myapp/about.html")


def contact(request):
    return render(request, "myapp/contact.html")


def signup_view(request):
    if request.user.is_authenticated:
        return redirect("services")

    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("services")
    else:
        form = SignUpForm()

    return render(request, "myapp/signup.html", {"form": form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect("services")

    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            return redirect("services")
    else:
        form = AuthenticationForm(request)

    return render(request, "myapp/login.html", {"form": form})


def logout_view(request):
    logout(request)
    return redirect("login")


@login_required
def services(request):
    property_counts = (
        Property.objects.filter(owner=request.user)
        .values("property_type")
        .annotate(total=Count("id"))
        .order_by("property_type")
    )
    return render(
        request,
        "myapp/services.html",
        {
            "property_counts": property_counts,
            "total_properties": sum(item["total"] for item in property_counts),
        },
    )


@login_required
def property_upload(request):
    if request.method == "POST":
        form = PropertyForm(request.POST)
        if form.is_valid():
            property_item = form.save(commit=False)
            property_item.owner = request.user
            property_item.save()
            email_sent_count = 0
            try:
                email_sent_count = send_new_property_email(property_item)
            except Exception:
                messages.warning(
                    request,
                    "Property uploaded, but email notification could not be sent.",
                )
            else:
                if email_sent_count > 0:
                    messages.info(
                        request,
                        f"Email notification sent to {email_sent_count} registered users.",
                    )
                else:
                    messages.info(
                        request,
                        "Property uploaded. No user email found for notification.",
                    )
            messages.success(request, "Property uploaded successfully.")
            return redirect("property_upload")
    else:
        form = PropertyForm()

    return render(request, "myapp/property_upload.html", {"form": form})


@login_required
def my_properties(request):
    properties = Property.objects.filter(owner=request.user)
    return render(request, "myapp/my_properties.html", {"properties": properties})


@login_required
def _filter_properties_from_request(request):
    form = PropertySearchForm(request.GET or None)
    properties = Property.objects.all()

    if form.is_valid():
        location = form.cleaned_data.get("location")
        property_type = form.cleaned_data.get("property_type")
        min_price = form.cleaned_data.get("min_price")
        max_price = form.cleaned_data.get("max_price")

        if location:
            properties = properties.filter(location__icontains=location)
        if property_type:
            properties = properties.filter(property_type=property_type)
        if min_price is not None:
            properties = properties.filter(price__gte=min_price)
        if max_price is not None:
            properties = properties.filter(price__lte=max_price)

    return form, properties


@login_required
def property_search(request):
    form, properties = _filter_properties_from_request(request)
    properties = properties.order_by("price")[:30]
    return render(
        request,
        "myapp/property_search.html",
        {"form": form, "properties": properties},
    )


@login_required
def property_price_analysis(request):
    form, properties = _filter_properties_from_request(request)

    analysis_data = calculate_price_analysis(properties)
    chart_data = []
    if analysis_data["minimum_price"] is not None:
        chart_data = [
            analysis_data["minimum_price"],
            analysis_data["average_price"],
            analysis_data["maximum_price"],
        ]
    return render(
        request,
        "myapp/property_price_analysis.html",
        {
            "form": form,
            "analysis": analysis_data,
            "chart_data": chart_data,
        },
    )


@login_required
def property_visualization(request):
    form, properties = _filter_properties_from_request(request)

    charts = build_visual_reports(properties)
    return render(
        request,
        "myapp/property_visualization.html",
        {
            "form": form,
            "charts": charts,
            "total_properties": properties.count(),
        },
    )


@login_required
def property_visualization_export_pdf(request):
    form, properties = _filter_properties_from_request(request)
    filters = form.cleaned_data if form.is_valid() else {}
    pdf_bytes = build_visual_report_pdf(properties, filters)

    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="property_visual_report.pdf"'
    return response


@login_required
def property_recommendation(request):
    form = RecommendationForm(request.GET or None)
    recommendations = []
    feedback_count = 0

    if form.is_valid():
        budget = form.cleaned_data.get("budget")
        location = form.cleaned_data.get("location")
        property_type = form.cleaned_data.get("property_type")
        recommendations, feedback_count = recommend_properties(
            request.user,
            budget=budget,
            location=location,
            property_type=property_type,
            limit=6,
        )

    return render(
        request,
        "myapp/property_recommendation.html",
        {
            "form": form,
            "recommendations": recommendations,
            "feedback_count": feedback_count,
            "query_string": request.GET.urlencode(),
        },
    )


@login_required
def property_recommendation_feedback(request):
    if request.method != "POST":
        return redirect("property_recommendation")

    property_id = request.POST.get("property_id")
    action = request.POST.get("action")
    next_query = request.POST.get("next_query", "")

    if action not in [PropertyFeedback.ACTION_LIKE, PropertyFeedback.ACTION_DISLIKE]:
        messages.error(request, "Invalid feedback action.")
        return redirect("property_recommendation")

    property_item = Property.objects.filter(id=property_id).first()
    if not property_item:
        messages.error(request, "Property not found.")
        return redirect("property_recommendation")

    PropertyFeedback.objects.update_or_create(
        user=request.user,
        property=property_item,
        defaults={"action": action},
    )
    messages.success(request, "Feedback saved. Recommendations will improve over time.")

    if next_query:
        return redirect(f"{reverse('property_recommendation')}?{next_query}")
    return redirect("property_recommendation")


@login_required
def fraud_complaint_report(request):
    initial_data = {}
    property_id_param = request.GET.get("property_id")
    if property_id_param and property_id_param.isdigit():
        initial_data["property_id"] = int(property_id_param)

    if request.method == "POST":
        form = FraudComplaintForm(request.POST)
        if form.is_valid():
            complaint = form.save(request.user)
            messages.success(
                request,
                f"Complaint submitted successfully for Property ID {complaint.property_id}.",
            )
            return redirect("fraud_complaint_report")
    else:
        form = FraudComplaintForm(initial=initial_data)

    recent_complaints = FraudComplaint.objects.filter(reporter=request.user)[:5]
    return render(
        request,
        "myapp/fraud_complaint_report.html",
        {"form": form, "recent_complaints": recent_complaints},
    )


@login_required
def fraud_complaint_list(request):
    complaints = FraudComplaint.objects.filter(reporter=request.user)
    return render(request, "myapp/fraud_complaint_list.html", {"complaints": complaints})


@login_required
def feedback_rating(request):
    initial_rating = {}
    property_id_param = request.GET.get("property_id")
    if property_id_param and property_id_param.isdigit():
        initial_rating["property_id"] = int(property_id_param)

    service_form = ServiceFeedbackForm()
    rating_form = PropertyRatingForm(initial=initial_rating)

    if request.method == "POST":
        form_type = request.POST.get("form_type")
        if form_type == "service_feedback":
            service_form = ServiceFeedbackForm(request.POST)
            if service_form.is_valid():
                feedback_obj = service_form.save(commit=False)
                feedback_obj.user = request.user
                feedback_obj.save()
                messages.success(request, "Service feedback submitted successfully.")
                return redirect("feedback_rating")
        elif form_type == "property_rating":
            rating_form = PropertyRatingForm(request.POST)
            if rating_form.is_valid():
                rating_obj = rating_form.save(request.user)
                messages.success(
                    request,
                    f"Property ID {rating_obj.property_id} rated successfully.",
                )
                return redirect("feedback_rating")

    recent_service_feedbacks = ServiceFeedback.objects.filter(user=request.user)[:5]
    recent_property_ratings = PropertyRating.objects.filter(user=request.user).select_related("property")[:5]

    return render(
        request,
        "myapp/feedback_rating.html",
        {
            "service_form": service_form,
            "rating_form": rating_form,
            "recent_service_feedbacks": recent_service_feedbacks,
            "recent_property_ratings": recent_property_ratings,
        },
    )


@login_required
def chatbot_view(request):
    user_message = ""
    detected_intent = ""
    chatbot_reply = ""

    if request.method == "POST":
        user_message = request.POST.get("message", "").strip()
        detected_intent, properties, fallback_message = search_properties_by_message(
            user_message, request.user
        )
        chatbot_reply = format_chatbot_reply(detected_intent, properties, fallback_message)

    return render(
        request,
        "myapp/chatbot.html",
        {
            "user_message": user_message,
            "detected_intent": detected_intent,
            "chatbot_reply": chatbot_reply,
        },
    )
