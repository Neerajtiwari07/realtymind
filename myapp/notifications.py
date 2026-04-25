from django.contrib.auth import get_user_model
from django.core.mail import send_mail


def send_new_property_email(property_item):
    User = get_user_model()
    recipients = list(
        User.objects.filter(is_active=True)
        .exclude(email__isnull=True)
        .exclude(email__exact="")
        .values_list("email", flat=True)
    )

    if not recipients:
        return 0

    subject = f"New Property Added: {property_item.get_property_type_display()}"
    message = (
        "A new property has been added on RealtyMind.\n\n"
        f"Property Type: {property_item.get_property_type_display()}\n"
        f"Location: {property_item.location}\n"
        f"Price / Rent: Rs. {property_item.price}\n"
    )

    return send_mail(
        subject=subject,
        message=message,
        from_email=None,  # Uses DEFAULT_FROM_EMAIL
        recipient_list=recipients,
        fail_silently=False,
    )
