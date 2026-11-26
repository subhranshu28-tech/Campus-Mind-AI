"""Small production hardening middleware not provided by Django core."""
from django.conf import settings


class ContentSecurityPolicyMiddleware:
    """Attach a conservative CSP to API responses."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if not settings.DEBUG:
            response["Content-Security-Policy"] = (
                "default-src 'self'; frame-ancestors 'none'; base-uri 'self'; "
                "form-action 'self'"
            )
            response["X-Content-Type-Options"] = "nosniff"
            response["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response
