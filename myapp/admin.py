from django.contrib import admin
from django.contrib.admin.models import LogEntry
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
from django.utils import timezone

from .models import FraudComplaint, Property, PropertyFeedback, PropertyRating, ServiceFeedback, UserActivity


class BaseReadOnlyAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.action(description="Approve selected properties")
def approve_properties(modeladmin, request, queryset):
    queryset.update(
        approval_status=Property.STATUS_APPROVED,
        reviewed_by=request.user,
        reviewed_at=timezone.now(),
    )


@admin.action(description="Reject selected properties")
def reject_properties(modeladmin, request, queryset):
    queryset.update(
        approval_status=Property.STATUS_REJECTED,
        reviewed_by=request.user,
        reviewed_at=timezone.now(),
    )


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "property_type",
        "location",
        "price",
        "approval_status",
        "owner",
        "reviewed_by",
        "created_at",
    )
    list_filter = ("approval_status", "property_type", "location", "created_at")
    search_fields = ("title", "location", "description")
    actions = [approve_properties, reject_properties]
    readonly_fields = ("created_at", "reviewed_at")

    def save_model(self, request, obj, form, change):
        if obj.approval_status in [Property.STATUS_APPROVED, Property.STATUS_REJECTED]:
            obj.reviewed_by = request.user
            obj.reviewed_at = timezone.now()
        super().save_model(request, obj, form, change)


@admin.register(PropertyFeedback)
class PropertyFeedbackAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "property", "action", "updated_at")
    list_filter = ("action",)
    search_fields = ("user__username", "property__title")


@admin.action(description="Mark selected complaints as In Review")
def mark_complaints_in_review(modeladmin, request, queryset):
    queryset.update(
        status=FraudComplaint.STATUS_IN_REVIEW,
        reviewed_by=request.user,
        reviewed_at=timezone.now(),
    )


@admin.action(description="Mark selected complaints as Action Taken")
def mark_complaints_action_taken(modeladmin, request, queryset):
    queryset.update(
        status=FraudComplaint.STATUS_ACTION_TAKEN,
        reviewed_by=request.user,
        reviewed_at=timezone.now(),
    )


@admin.action(description="Reject selected complaints")
def reject_complaints(modeladmin, request, queryset):
    queryset.update(
        status=FraudComplaint.STATUS_REJECTED,
        reviewed_by=request.user,
        reviewed_at=timezone.now(),
    )


@admin.register(FraudComplaint)
class FraudComplaintAdmin(admin.ModelAdmin):
    list_display = ("id", "property", "reporter", "status", "reviewed_by", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("property__title", "reporter__username", "reason", "admin_action")
    readonly_fields = ("created_at", "reviewed_at")
    actions = [mark_complaints_in_review, mark_complaints_action_taken, reject_complaints]

    def save_model(self, request, obj, form, change):
        status = obj.status
        if status in [FraudComplaint.STATUS_IN_REVIEW, FraudComplaint.STATUS_ACTION_TAKEN, FraudComplaint.STATUS_REJECTED]:
            if not obj.reviewed_by:
                obj.reviewed_by = request.user
            if not obj.reviewed_at:
                obj.reviewed_at = timezone.now()
        super().save_model(request, obj, form, change)


@admin.register(ServiceFeedback)
class ServiceFeedbackAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "service_rating", "created_at")
    list_filter = ("service_rating", "created_at")
    search_fields = ("user__username", "feedback_text")


@admin.register(PropertyRating)
class PropertyRatingAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "property", "rating", "updated_at")
    list_filter = ("rating", "updated_at")
    search_fields = ("user__username", "property__title", "feedback_text")


@admin.register(LogEntry)
class ActivityLogAdmin(BaseReadOnlyAdmin):
    list_display = ("action_time", "user", "content_type", "object_repr", "action_flag")
    list_filter = ("action_flag", "content_type", "action_time")
    search_fields = ("object_repr", "change_message", "user__username")
    ordering = ("-action_time",)


@admin.register(UserActivity)
class UserActivityAdmin(BaseReadOnlyAdmin):
    list_display = ("created_at", "user", "method", "path", "status_code", "ip_address")
    list_filter = ("method", "status_code", "created_at")
    search_fields = ("user__username", "path", "user_agent", "ip_address")
    ordering = ("-created_at",)


User = get_user_model()


class CustomUserAdmin(UserAdmin):
    list_display = (
        "username",
        "email",
        "is_staff",
        "is_active",
        "date_joined",
        "last_login",
        "uploaded_properties_count",
        "complaints_count",
    )
    list_filter = ("is_staff", "is_active", "date_joined")

    def uploaded_properties_count(self, obj):
        return obj.properties.count()

    uploaded_properties_count.short_description = "Properties"

    def complaints_count(self, obj):
        return obj.fraud_complaints.count()

    complaints_count.short_description = "Complaints"


admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
