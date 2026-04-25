from django.conf import settings
from django.db import models


class Property(models.Model):
    PROPERTY_TYPE_PLOT = "plot"
    PROPERTY_TYPE_LAND = "land"
    PROPERTY_TYPE_FLAT = "flat"
    PROPERTY_TYPE_RENTAL_ROOM = "rental_room"

    PROPERTY_TYPE_CHOICES = [
        (PROPERTY_TYPE_PLOT, "Plot"),
        (PROPERTY_TYPE_LAND, "Land"),
        (PROPERTY_TYPE_FLAT, "Flat"),
        (PROPERTY_TYPE_RENTAL_ROOM, "Rental room"),
    ]
    STATUS_PENDING = "pending"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_REJECTED, "Rejected"),
    ]

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="properties",
    )
    property_type = models.CharField(max_length=20, choices=PROPERTY_TYPE_CHOICES)
    title = models.CharField(max_length=120)
    description = models.TextField()
    location = models.CharField(max_length=200)
    area_sqft = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=12, decimal_places=2)
    approval_status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )
    approval_note = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_properties",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["location"]),
            models.Index(fields=["price"]),
            models.Index(fields=["property_type"]),
            models.Index(fields=["approval_status"]),
        ]

    def __str__(self):
        return f"{self.title} ({self.get_property_type_display()})"


class PropertyFeedback(models.Model):
    ACTION_LIKE = "like"
    ACTION_DISLIKE = "dislike"
    ACTION_CHOICES = [
        (ACTION_LIKE, "Like"),
        (ACTION_DISLIKE, "Dislike"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="property_feedbacks",
    )
    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name="feedbacks",
    )
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "property")
        indexes = [
            models.Index(fields=["user", "action"]),
            models.Index(fields=["property", "action"]),
        ]

    def __str__(self):
        return f"{self.user} - {self.property.title} - {self.action}"


class FraudComplaint(models.Model):
    STATUS_PENDING = "pending"
    STATUS_IN_REVIEW = "in_review"
    STATUS_ACTION_TAKEN = "action_taken"
    STATUS_REJECTED = "rejected"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_IN_REVIEW, "In Review"),
        (STATUS_ACTION_TAKEN, "Action Taken"),
        (STATUS_REJECTED, "Rejected"),
    ]

    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="fraud_complaints",
    )
    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name="fraud_complaints",
    )
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    admin_action = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_fraud_complaints",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["reporter", "status"]),
        ]

    def __str__(self):
        return f"Complaint #{self.id} - Property {self.property_id} - {self.status}"


class ServiceFeedback(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="service_feedbacks",
    )
    service_rating = models.PositiveSmallIntegerField()
    feedback_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["service_rating"]),
            models.Index(fields=["user", "created_at"]),
        ]

    def __str__(self):
        return f"ServiceFeedback #{self.id} by {self.user}"


class PropertyRating(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="property_ratings",
    )
    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name="ratings",
    )
    rating = models.PositiveSmallIntegerField()
    feedback_text = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "property")
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["property", "rating"]),
            models.Index(fields=["user", "rating"]),
        ]

    def __str__(self):
        return f"{self.user} rated Property {self.property_id}: {self.rating}"


class UserActivity(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="activities",
    )
    path = models.CharField(max_length=255)
    method = models.CharField(max_length=10)
    status_code = models.PositiveSmallIntegerField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["path", "created_at"]),
            models.Index(fields=["status_code"]),
        ]

    def __str__(self):
        username = self.user.username if self.user else "anonymous"
        return f"{username} {self.method} {self.path} [{self.status_code}]"
