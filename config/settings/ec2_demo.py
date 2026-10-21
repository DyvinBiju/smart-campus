from .production import *  # noqa: F403
from .production import DATABASES
from .production import env

# Hosts allowed to reach the demo. Set via env on EC2, for example:
# DJANGO_ALLOWED_HOSTS=<elastic-ip>,<public-dns>,localhost,127.0.0.1
ALLOWED_HOSTS = env.list(
    "DJANGO_ALLOWED_HOSTS",
    default=["localhost", "127.0.0.1"],
)

# CSRF origins must include the scheme when the demo is served over HTTP.
# DJANGO_CSRF_TRUSTED_ORIGINS=http://<elastic-ip>,http://<public-dns>
CSRF_TRUSTED_ORIGINS = env.list("DJANGO_CSRF_TRUSTED_ORIGINS", default=[])

# HTTP-only demo overrides. Secure cookies cannot be set over plain HTTP.
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SESSION_COOKIE_NAME = "sessionid"
CSRF_COOKIE_NAME = "csrftoken"
SECURE_HSTS_SECONDS = 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False

# The demo does not run Redis. FileBasedCache keeps the password-reset
# rate-limit counter shared across Gunicorn workers on a single host.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.filebased.FileBasedCache",
        "LOCATION": env("DJANGO_CACHE_DIR", default="/tmp/smart_campus_cache"),
    },
}

# RDS enforces TLS by default on recent PostgreSQL versions.
DATABASES["default"].setdefault("OPTIONS", {})
DATABASES["default"]["OPTIONS"]["sslmode"] = env(
    "POSTGRES_SSLMODE",
    default="require",
)
DATABASES["default"]["CONN_MAX_AGE"] = env.int("CONN_MAX_AGE", default=60)

# The demo has no real mail delivery. Emails are written to container logs.
EMAIL_BACKEND = env(
    "DJANGO_EMAIL_BACKEND",
    default="django.core.mail.backends.console.EmailBackend",
)
