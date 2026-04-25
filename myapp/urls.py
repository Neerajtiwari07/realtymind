from django.urls import path

from . import views

urlpatterns = [
    path("", views.services, name="services"),
    path("home/", views.home, name="home"),
    path("about/", views.about, name="about"),
    path("contact/", views.contact, name="contact"),
    path("signup/", views.signup_view, name="signup"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("properties/upload/", views.property_upload, name="property_upload"),
    path("properties/search/", views.property_search, name="property_search"),
    path("properties/price-analysis/", views.property_price_analysis, name="property_price_analysis"),
    path("properties/visualization/", views.property_visualization, name="property_visualization"),
    path("properties/recommendation/", views.property_recommendation, name="property_recommendation"),
    path(
        "properties/recommendation/feedback/",
        views.property_recommendation_feedback,
        name="property_recommendation_feedback",
    ),
    path(
        "properties/visualization/export-pdf/",
        views.property_visualization_export_pdf,
        name="property_visualization_export_pdf",
    ),
    path("complaints/report/", views.fraud_complaint_report, name="fraud_complaint_report"),
    path("complaints/my/", views.fraud_complaint_list, name="fraud_complaint_list"),
    path("feedback-rating/", views.feedback_rating, name="feedback_rating"),
    path("properties/my/", views.my_properties, name="my_properties"),
    path("chatbot/", views.chatbot_view, name="chatbot"),
]
