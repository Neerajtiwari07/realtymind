from .models import UserActivity


class UserActivityMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if request.user.is_authenticated and not request.path.startswith("/static/"):
            user_agent = request.META.get("HTTP_USER_AGENT", "")[:300]
            ip_address = request.META.get("REMOTE_ADDR")
            UserActivity.objects.create(
                user=request.user,
                path=request.path[:255],
                method=request.method[:10],
                status_code=response.status_code,
                ip_address=ip_address,
                user_agent=user_agent,
            )

        return response
