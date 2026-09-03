from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import FormView

from allauth.account.views import LoginView
from allauth.core.exceptions import ImmediateHttpResponse

from smart_campus.users.forms import FacultySignupForm
from smart_campus.users.forms import StudentSignupForm
from smart_campus.users.models import User


from django.utils.http import url_has_allowed_host_and_scheme


from django.contrib.auth import login

class SmartCampusLoginView(LoginView):
    """
    Custom LoginView that authenticates the user normally,
    and redirects to 'next' URL if specified, or user's role-based dashboard with a success message.
    """

    def dispatch(self, request, *args, **kwargs):
        return FormView.dispatch(self, request, *args, **kwargs)

    def form_valid(self, form):
        user = form.user
        messages.success(self.request, _(f"Welcome back, {user.username}!"))
        next_url = self.request.POST.get("next") or self.request.GET.get("next")
        if next_url and url_has_allowed_host_and_scheme(
            url=next_url,
            allowed_hosts={self.request.get_host()},
            require_https=self.request.is_secure(),
        ):
            redirect_url = next_url
        else:
            if user.is_admin_user or user.is_maintenance_staff:
                redirect_url = reverse("dashboard:admin")
            else:
                redirect_url = reverse("dashboard:student")

        try:
            return form.login(self.request, redirect_url=redirect_url)
        except ImmediateHttpResponse as e:
            return e.response


smart_campus_login_view = SmartCampusLoginView.as_view()


class RoleRequiredMixin(LoginRequiredMixin):
    """
    Enforces server-side role-based access control.
    Prevents unauthorized users from accessing protected views.
    """

    allowed_roles: list[str] = []

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if request.user.is_superuser:
            return super().dispatch(request, *args, **kwargs)
        if request.user.role not in self.allowed_roles:
            raise PermissionDenied(_("You are not authorized to access this resource."))
        return super().dispatch(request, *args, **kwargs)


class StudentSignupView(FormView):
    template_name = "users/signup_student.html"
    form_class = StudentSignupForm

    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        user = form.save()
        login(self.request, user, backend="django.contrib.auth.backends.ModelBackend")
        messages.success(
            self.request,
            _("Account created successfully. Welcome to SmartCampus!"),
        )
        return redirect("dashboard:student")


student_signup_view = StudentSignupView.as_view()


class FacultySignupView(FormView):
    template_name = "users/signup_faculty.html"
    form_class = FacultySignupForm

    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        user = form.save()
        login(self.request, user, backend="django.contrib.auth.backends.ModelBackend")
        messages.success(
            self.request,
            _("Account created successfully. Welcome to SmartCampus!"),
        )
        return redirect("dashboard:student")


faculty_signup_view = FacultySignupView.as_view()






