from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include
from django.urls import path
from django.views import defaults as default_views
from django.views.generic import TemplateView

from smart_campus.users.views import smart_campus_login_view


urlpatterns = [

    path("", TemplateView.as_view(template_name="pages/home.html"), name="home"),

    path(
        "about/",
        TemplateView.as_view(template_name="pages/about.html"),
        name="about",
    ),

    # Django Admin, use {% url 'admin:index' %}
    path(settings.ADMIN_URL, admin.site.urls),

    # User management
    path("users/", include("smart_campus.users.urls", namespace="users")),
    path("accounts/login/", smart_campus_login_view, name="account_login"),
    path("accounts/", include("allauth.urls")),

    # Custom apps
    path("assets/", include("smart_campus.assets.urls")),
    path(
        "complaints/",
        include("smart_campus.complaints.urls", namespace="complaints"),
    ),
    path("inventory/", include("smart_campus.inventory.urls")),
    path("dashboard/", include("smart_campus.dashboard.urls", namespace="dashboard")),
    # Media files
    *static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT),
]


if settings.DEBUG:
    # This allows the error pages to be debugged during development, just visit
    # these url in browser to see how these error pages look like.
    urlpatterns += [
        path(
            "400/",
            default_views.bad_request,
            kwargs={"exception": Exception("Bad Request!")},
        ),
        path(
            "403/",
            default_views.permission_denied,
            kwargs={"exception": Exception("Permission Denied")},
        ),
        path(
            "404/",
            default_views.page_not_found,
            kwargs={"exception": Exception("Page not Found")},
        ),
        path("500/", default_views.server_error),
    ]
    if "debug_toolbar" in settings.INSTALLED_APPS:
        import debug_toolbar

        urlpatterns = [
            path("__debug__/", include(debug_toolbar.urls)),
            *urlpatterns,
        ]
        
