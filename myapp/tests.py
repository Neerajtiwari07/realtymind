from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase
from django.urls import reverse

from .models import FraudComplaint, Property, PropertyFeedback, PropertyRating, ServiceFeedback
from .nlp import detect_intent
from .recommendation import recommend_properties


class AuthenticationModuleTests(TestCase):
    def test_services_requires_login(self):
        response = self.client.get(reverse("services"))
        self.assertRedirects(response, "/login/?next=/")

    def test_user_can_signup_and_access_services(self):
        response = self.client.post(
            reverse("signup"),
            {
                "username": "newuser",
                "password1": "ComplexPass123!",
                "password2": "ComplexPass123!",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(User.objects.filter(username="newuser").exists())
        self.assertContains(response, "Only registered and logged-in users can see this services page.")

    def test_user_can_login(self):
        User.objects.create_user(username="john", password="StrongPass123!")
        response = self.client.post(
            reverse("login"),
            {"username": "john", "password": "StrongPass123!"},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Welcome john")

    def test_property_upload_requires_login(self):
        response = self.client.get(reverse("property_upload"))
        self.assertRedirects(response, "/login/?next=/properties/upload/")

    def test_logged_in_user_can_upload_property(self):
        user = User.objects.create_user(username="owner1", password="StrongPass123!")
        self.client.login(username="owner1", password="StrongPass123!")

        response = self.client.post(
            reverse("property_upload"),
            {
                "property_type": "plot",
                "title": "Corner Plot",
                "description": "Prime location residential plot.",
                "location": "Sector 45",
                "area_sqft": 1800,
                "price": "2500000.00",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(Property.objects.filter(title="Corner Plot", owner=user).exists())
        self.assertEqual(
            Property.objects.get(title="Corner Plot", owner=user).approval_status,
            Property.STATUS_PENDING,
        )
        self.assertContains(response, "Property uploaded successfully.")

    def test_my_properties_requires_login(self):
        response = self.client.get(reverse("my_properties"))
        self.assertRedirects(response, "/login/?next=/properties/my/")

    def test_property_search_requires_login(self):
        response = self.client.get(reverse("property_search"))
        self.assertRedirects(response, "/login/?next=/properties/search/")

    def test_property_price_analysis_requires_login(self):
        response = self.client.get(reverse("property_price_analysis"))
        self.assertRedirects(response, "/login/?next=/properties/price-analysis/")

    def test_property_visualization_requires_login(self):
        response = self.client.get(reverse("property_visualization"))
        self.assertRedirects(response, "/login/?next=/properties/visualization/")

    def test_property_visualization_export_pdf_requires_login(self):
        response = self.client.get(reverse("property_visualization_export_pdf"))
        self.assertRedirects(response, "/login/?next=/properties/visualization/export-pdf/")

    def test_property_recommendation_requires_login(self):
        response = self.client.get(reverse("property_recommendation"))
        self.assertRedirects(response, "/login/?next=/properties/recommendation/")

    def test_property_recommendation_feedback_requires_login(self):
        response = self.client.post(reverse("property_recommendation_feedback"))
        self.assertRedirects(response, "/login/?next=/properties/recommendation/feedback/")

    def test_fraud_complaint_pages_require_login(self):
        report_response = self.client.get(reverse("fraud_complaint_report"))
        self.assertRedirects(report_response, "/login/?next=/complaints/report/")
        list_response = self.client.get(reverse("fraud_complaint_list"))
        self.assertRedirects(list_response, "/login/?next=/complaints/my/")

    def test_feedback_rating_requires_login(self):
        response = self.client.get(reverse("feedback_rating"))
        self.assertRedirects(response, "/login/?next=/feedback-rating/")

    def test_user_can_upload_all_property_types(self):
        user = User.objects.create_user(username="owner2", password="StrongPass123!")
        self.client.login(username="owner2", password="StrongPass123!")

        property_types = ["plot", "land", "flat", "rental_room"]
        for index, property_type in enumerate(property_types, start=1):
            response = self.client.post(
                reverse("property_upload"),
                {
                    "property_type": property_type,
                    "title": f"Property {index}",
                    "description": "Demo description",
                    "location": "Demo location",
                    "area_sqft": 1000 + index,
                    "price": "100000.00",
                },
            )
            self.assertEqual(response.status_code, 302)

        self.assertEqual(Property.objects.filter(owner=user).count(), 4)

    def test_price_must_be_positive(self):
        user = User.objects.create_user(username="owner3", password="StrongPass123!")
        self.client.login(username="owner3", password="StrongPass123!")

        response = self.client.post(
            reverse("property_upload"),
            {
                "property_type": "plot",
                "title": "Invalid Property",
                "description": "Invalid price test",
                "location": "Nowhere",
                "area_sqft": 1200,
                "price": "-1.00",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Price must be greater than 0.")

    def test_property_search_by_location_type_and_price(self):
        user = User.objects.create_user(username="searchuser", password="StrongPass123!")
        self.client.login(username="searchuser", password="StrongPass123!")

        Property.objects.create(
            owner=user,
            property_type="flat",
            title="Flat A",
            description="A flat",
            location="Jaipur",
            area_sqft=800,
            price="700000.00",
        )
        Property.objects.create(
            owner=user,
            property_type="flat",
            title="Flat B",
            description="A costly flat",
            location="Jaipur",
            area_sqft=900,
            price="1500000.00",
        )
        Property.objects.create(
            owner=user,
            property_type="land",
            title="Land C",
            description="Land",
            location="Jaipur",
            area_sqft=1200,
            price="600000.00",
        )

        response = self.client.get(
            reverse("property_search"),
            {
                "location": "Jaipur",
                "property_type": "flat",
                "min_price": "500000",
                "max_price": "1000000",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Flat A")
        self.assertNotContains(response, "Flat B")
        self.assertNotContains(response, "Land C")

    def test_chatbot_requires_login(self):
        response = self.client.get(reverse("chatbot"))
        self.assertRedirects(response, "/login/?next=/chatbot/")

    def test_detect_intent_for_property_search(self):
        self.assertEqual(detect_intent("low rent flat"), "property_search")

    def test_chatbot_low_rent_flat_query(self):
        user = User.objects.create_user(username="chatuser1", password="StrongPass123!")
        self.client.login(username="chatuser1", password="StrongPass123!")

        Property.objects.create(
            owner=user,
            property_type="flat",
            title="Budget Flat",
            description="Affordable flat",
            location="Sector 45",
            area_sqft=900,
            price="850000.00",
        )

        response = self.client.post(
            reverse("chatbot"),
            {"message": "low rent flat"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Detected intent:")
        self.assertContains(response, "property_search")
        self.assertContains(response, "Budget Flat")

    def test_chatbot_cheap_land_in_this_area_query(self):
        user = User.objects.create_user(username="chatuser2", password="StrongPass123!")
        self.client.login(username="chatuser2", password="StrongPass123!")

        Property.objects.create(
            owner=user,
            property_type="land",
            title="My Area Land",
            description="Reference property",
            location="Jaipur",
            area_sqft=1400,
            price="1200000.00",
        )
        Property.objects.create(
            owner=user,
            property_type="land",
            title="Cheap Jaipur Land",
            description="Cheap option",
            location="Jaipur",
            area_sqft=1200,
            price="900000.00",
        )
        Property.objects.create(
            owner=user,
            property_type="land",
            title="Other City Land",
            description="Not in same area",
            location="Delhi",
            area_sqft=1200,
            price="700000.00",
        )

        response = self.client.post(
            reverse("chatbot"),
            {"message": "cheap land in this area"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "property_search")
        self.assertContains(response, "Cheap Jaipur Land")
        self.assertNotContains(response, "Other City Land")

    def test_chatbot_query_with_price_limit(self):
        user = User.objects.create_user(username="chatuser3", password="StrongPass123!")
        self.client.login(username="chatuser3", password="StrongPass123!")

        Property.objects.create(
            owner=user,
            property_type="flat",
            title="Affordable Flat",
            description="Budget option",
            location="Pune",
            area_sqft=850,
            price="800000.00",
        )
        Property.objects.create(
            owner=user,
            property_type="flat",
            title="Luxury Flat",
            description="Expensive option",
            location="Pune",
            area_sqft=1250,
            price="2500000.00",
        )

        response = self.client.post(
            reverse("chatbot"),
            {"message": "flat in pune under 1000000"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Affordable Flat")
        self.assertNotContains(response, "Luxury Flat")

    def test_price_analysis_calculates_min_avg_max_and_lowest_rent(self):
        user = User.objects.create_user(username="analysisuser", password="StrongPass123!")
        self.client.login(username="analysisuser", password="StrongPass123!")

        Property.objects.create(
            owner=user,
            property_type="flat",
            title="Flat 1",
            description="Flat price",
            location="Mumbai",
            area_sqft=700,
            price="100000.00",
        )
        Property.objects.create(
            owner=user,
            property_type="land",
            title="Land 1",
            description="Land price",
            location="Mumbai",
            area_sqft=1200,
            price="300000.00",
        )
        Property.objects.create(
            owner=user,
            property_type="rental_room",
            title="Rental 1",
            description="Rental room",
            location="Mumbai",
            area_sqft=200,
            price="50000.00",
        )

        response = self.client.get(reverse("property_price_analysis"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Minimum Price")
        self.assertContains(response, "50000.00")
        self.assertContains(response, "Average Price")
        self.assertContains(response, "150000.00")
        self.assertContains(response, "Maximum Price")
        self.assertContains(response, "300000.00")
        self.assertContains(response, "Lowest Rent Property")
        self.assertContains(response, "Rental 1")
        self.assertContains(response, "Cheapest Properties")
        self.assertContains(response, "priceAnalysisChart")

    def test_property_visualization_shows_matplotlib_charts(self):
        user = User.objects.create_user(username="vizuser", password="StrongPass123!")
        self.client.login(username="vizuser", password="StrongPass123!")

        Property.objects.create(
            owner=user,
            property_type="flat",
            title="Viz Flat",
            description="Flat",
            location="Noida",
            area_sqft=750,
            price="900000.00",
        )
        Property.objects.create(
            owner=user,
            property_type="land",
            title="Viz Land",
            description="Land",
            location="Noida",
            area_sqft=1400,
            price="1500000.00",
        )
        Property.objects.create(
            owner=user,
            property_type="plot",
            title="Viz Plot",
            description="Plot",
            location="Pune",
            area_sqft=1000,
            price="800000.00",
        )

        response = self.client.get(reverse("property_visualization"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Data Visualization Reports (Matplotlib)")
        self.assertContains(response, "Price vs Area")
        self.assertContains(response, "Location-wise Price Analysis")
        self.assertContains(response, "Property Type Comparison")
        self.assertContains(response, "data:image/png;base64")

    def test_property_visualization_pdf_export_downloads_file(self):
        user = User.objects.create_user(username="pdfuser", password="StrongPass123!")
        self.client.login(username="pdfuser", password="StrongPass123!")

        Property.objects.create(
            owner=user,
            property_type="flat",
            title="PDF Flat",
            description="For report",
            location="Gurgaon",
            area_sqft=900,
            price="1100000.00",
        )

        response = self.client.get(reverse("property_visualization_export_pdf"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn("property_visual_report.pdf", response["Content-Disposition"])
        self.assertTrue(response.content.startswith(b"%PDF"))

    def test_ml_recommendation_filters_by_budget_location_and_type(self):
        user = User.objects.create_user(username="mluser1", password="StrongPass123!")
        self.client.login(username="mluser1", password="StrongPass123!")

        Property.objects.create(
            owner=user,
            property_type="flat",
            title="Best Match Flat",
            description="Match",
            location="Jaipur",
            area_sqft=900,
            price="1000000.00",
        )
        Property.objects.create(
            owner=user,
            property_type="flat",
            title="Wrong Location Flat",
            description="Wrong location",
            location="Delhi",
            area_sqft=900,
            price="990000.00",
        )
        Property.objects.create(
            owner=user,
            property_type="land",
            title="Wrong Type Land",
            description="Wrong type",
            location="Jaipur",
            area_sqft=1100,
            price="1000000.00",
        )

        response = self.client.get(
            reverse("property_recommendation"),
            {"budget": "1000000", "location": "Jaipur", "property_type": "flat"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Best Match Flat")
        self.assertNotContains(response, "Wrong Location Flat")
        self.assertNotContains(response, "Wrong Type Land")

    def test_recommendation_feedback_saved_and_used_for_learning(self):
        user = User.objects.create_user(username="mluser2", password="StrongPass123!")
        self.client.login(username="mluser2", password="StrongPass123!")

        disliked_property = Property.objects.create(
            owner=user,
            property_type="flat",
            title="Disliked Flat",
            description="Dislike sample",
            location="Pune",
            area_sqft=850,
            price="1000000.00",
        )
        liked_property = Property.objects.create(
            owner=user,
            property_type="flat",
            title="Liked Flat",
            description="Like sample",
            location="Mumbai",
            area_sqft=850,
            price="1000000.00",
        )

        self.client.post(
            reverse("property_recommendation_feedback"),
            {"property_id": disliked_property.id, "action": "dislike"},
            follow=True,
        )
        self.client.post(
            reverse("property_recommendation_feedback"),
            {"property_id": liked_property.id, "action": "like"},
            follow=True,
        )

        self.assertEqual(PropertyFeedback.objects.filter(user=user).count(), 2)

        recommendations, feedback_count = recommend_properties(
            user,
            budget=1000000,
            property_type="flat",
            limit=2,
        )
        self.assertEqual(feedback_count, 2)
        self.assertEqual(recommendations[0][0].title, "Liked Flat")

    def test_property_upload_sends_email_to_registered_users(self):
        owner = User.objects.create_user(
            username="emailowner",
            email="owner@example.com",
            password="StrongPass123!",
        )
        User.objects.create_user(
            username="user1",
            email="user1@example.com",
            password="StrongPass123!",
        )
        User.objects.create_user(
            username="user2",
            email="user2@example.com",
            password="StrongPass123!",
        )
        self.client.login(username="emailowner", password="StrongPass123!")

        response = self.client.post(
            reverse("property_upload"),
            {
                "property_type": "flat",
                "title": "Email Flat",
                "description": "Email notification test",
                "location": "Noida",
                "area_sqft": 950,
                "price": "1250000.00",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertIn("New Property Added: Flat", email.subject)
        self.assertIn("Property Type: Flat", email.body)
        self.assertIn("Location: Noida", email.body)
        self.assertIn("Price / Rent: Rs. 1250000.00", email.body)
        self.assertCountEqual(
            email.to,
            ["owner@example.com", "user1@example.com", "user2@example.com"],
        )

    def test_user_can_submit_fraud_complaint(self):
        user = User.objects.create_user(username="complainer", password="StrongPass123!")
        self.client.login(username="complainer", password="StrongPass123!")
        property_item = Property.objects.create(
            owner=user,
            property_type="plot",
            title="Suspicious Plot",
            description="Seems fake",
            location="Ghaziabad",
            area_sqft=1000,
            price="700000.00",
        )

        response = self.client.post(
            reverse("fraud_complaint_report"),
            {"property_id": property_item.id, "reason": "Owner asked for token without visit."},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(FraudComplaint.objects.count(), 1)
        complaint = FraudComplaint.objects.first()
        self.assertEqual(complaint.reporter, user)
        self.assertEqual(complaint.property, property_item)
        self.assertEqual(complaint.status, FraudComplaint.STATUS_PENDING)
        self.assertContains(response, "Complaint submitted successfully")

    def test_fraud_complaint_invalid_property_id(self):
        user = User.objects.create_user(username="complainer2", password="StrongPass123!")
        self.client.login(username="complainer2", password="StrongPass123!")

        response = self.client.post(
            reverse("fraud_complaint_report"),
            {"property_id": 999999, "reason": "This property does not exist."},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Property with this ID does not exist.")

    def test_user_can_submit_service_feedback(self):
        user = User.objects.create_user(username="servicefb", password="StrongPass123!")
        self.client.login(username="servicefb", password="StrongPass123!")

        response = self.client.post(
            reverse("feedback_rating"),
            {
                "form_type": "service_feedback",
                "service_rating": 5,
                "feedback_text": "Support response was quick and helpful.",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ServiceFeedback.objects.count(), 1)
        feedback = ServiceFeedback.objects.first()
        self.assertEqual(feedback.user, user)
        self.assertEqual(feedback.service_rating, 5)
        self.assertContains(response, "Service feedback submitted successfully.")

    def test_user_can_rate_property_and_update_rating(self):
        user = User.objects.create_user(username="rater1", password="StrongPass123!")
        self.client.login(username="rater1", password="StrongPass123!")
        property_item = Property.objects.create(
            owner=user,
            property_type="flat",
            title="Rateable Flat",
            description="For rating test",
            location="Noida",
            area_sqft=900,
            price="1100000.00",
        )

        self.client.post(
            reverse("feedback_rating"),
            {
                "form_type": "property_rating",
                "property_id": property_item.id,
                "rating": 4,
                "feedback_text": "Good location",
            },
            follow=True,
        )
        self.assertEqual(PropertyRating.objects.count(), 1)
        rating = PropertyRating.objects.first()
        self.assertEqual(rating.rating, 4)

        self.client.post(
            reverse("feedback_rating"),
            {
                "form_type": "property_rating",
                "property_id": property_item.id,
                "rating": 2,
                "feedback_text": "Updated review",
            },
            follow=True,
        )
        self.assertEqual(PropertyRating.objects.count(), 1)
        rating.refresh_from_db()
        self.assertEqual(rating.rating, 2)
        self.assertEqual(rating.feedback_text, "Updated review")

    def test_property_rating_invalid_property_id(self):
        user = User.objects.create_user(username="rater2", password="StrongPass123!")
        self.client.login(username="rater2", password="StrongPass123!")

        response = self.client.post(
            reverse("feedback_rating"),
            {
                "form_type": "property_rating",
                "property_id": 999999,
                "rating": 3,
                "feedback_text": "Invalid property",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Property with this ID does not exist.")
