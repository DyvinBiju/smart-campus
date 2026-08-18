from __future__ import annotations

from typing import TYPE_CHECKING

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView
from django.views.generic import FormView
from django.views.generic import RedirectView
from django.views.generic import TemplateView
from django.views.generic import UpdateView

from smart_campus.users.forms import FacultySignupForm
from smart_campus.users.forms import MaintenanceStaffCreationForm
from smart_campus.users.forms import StudentSignupForm
from smart_campus.users.forms import UserProfileUpdateForm
from smart_campus.users.models import User

if TYPE_CHECKING:
    from django.db.models import QuerySet


class RoleRequiredMixin(LoginRequiredMixin):
    """
    Enforces server-side role-based access control.
    Prevents unauthorized users from accessing other roles' dashboards by URL.
    """

    allowed_roles: list[str] = []

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if request.user.is_superuser:
            return super().dispatch(request, *args, **kwargs)
        if request.user.role not in self.allowed_roles:
            raise PermissionDenied(_("You are not authorized to access this dashboard."))
        return super().dispatch(request, *args, **kwargs)


class StudentSignupView(FormView):
    template_name = "users/signup_student.html"
    form_class = StudentSignupForm

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("users:redirect")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        user = form.save()
        login(self.request, user, backend="django.contrib.auth.backends.ModelBackend")
        messages.success(self.request, _("Welcome to SmartCampus! Your Student account has been created."))
        return redirect("users:student_dashboard")


student_signup_view = StudentSignupView.as_view()


class FacultySignupView(FormView):
    template_name = "users/signup_faculty.html"
    form_class = FacultySignupForm

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("users:redirect")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        user = form.save()
        login(self.request, user, backend="django.contrib.auth.backends.ModelBackend")
        messages.success(self.request, _("Welcome to SmartCampus! Your Faculty account has been created."))
        return redirect("users:faculty_dashboard")


faculty_signup_view = FacultySignupView.as_view()


class StudentDashboardView(RoleRequiredMixin, TemplateView):
    template_name = "users/dashboard_student.html"
    allowed_roles = [User.Role.STUDENT.value]


student_dashboard_view = StudentDashboardView.as_view()


class FacultyDashboardView(RoleRequiredMixin, TemplateView):
    template_name = "users/dashboard_faculty.html"
    allowed_roles = [User.Role.FACULTY.value]


faculty_dashboard_view = FacultyDashboardView.as_view()


class MaintenanceDashboardView(RoleRequiredMixin, TemplateView):
    template_name = "users/dashboard_maintenance.html"
    allowed_roles = [User.Role.MAINTENANCE.value]


maintenance_dashboard_view = MaintenanceDashboardView.as_view()


class AdminDashboardView(RoleRequiredMixin, TemplateView):
    template_name = "users/dashboard_admin.html"
    allowed_roles = [User.Role.ADMIN.value]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if "maintenance_form" not in context:
            context["maintenance_form"] = MaintenanceStaffCreationForm()
        context["students_count"] = User.objects.filter(role=User.Role.STUDENT).count()
        context["faculty_count"] = User.objects.filter(role=User.Role.FACULTY).count()
        context["maintenance_count"] = User.objects.filter(role=User.Role.MAINTENANCE).count()
        context["recent_users"] = User.objects.order_by("-date_joined")[:8]
        context["maintenance_staff_list"] = User.objects.filter(role=User.Role.MAINTENANCE).order_by("-date_joined")
        return context

    def post(self, request, *args, **kwargs):
        form = MaintenanceStaffCreationForm(request.POST)
        if form.is_valid():
            staff_user = form.save()
            messages.success(
                request,
                _("Maintenance Staff account for '%(name)s' (ID: %(id)s) has been successfully created.")
                % {"name": staff_user.name, "id": staff_user.campus_id},
            )
            return redirect("users:admin_dashboard")
        context = self.get_context_data(maintenance_form=form)
        return self.render_to_response(context)


admin_dashboard_view = AdminDashboardView.as_view()


class UserDetailView(LoginRequiredMixin, DetailView):
    model = User
    slug_field = "username"
    slug_url_kwarg = "username"
    template_name = "users/user_detail.html"


user_detail_view = UserDetailView.as_view()


class UserUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = User
    form_class = UserProfileUpdateForm
    template_name = "users/user_form.html"
    success_message = _("Information successfully updated")

    def get_success_url(self) -> str:
        assert self.request.user.is_authenticated  # type guard
        return self.request.user.get_absolute_url()

    def get_object(self, queryset: QuerySet | None = None) -> User:
        assert self.request.user.is_authenticated  # type guard
        return self.request.user


user_update_view = UserUpdateView.as_view()


class UserRedirectView(LoginRequiredMixin, RedirectView):
    permanent = False

    def get_redirect_url(self) -> str:
        user = self.request.user
        if user.role == User.Role.STUDENT:
            return reverse("users:student_dashboard")
        elif user.role == User.Role.FACULTY:
            return reverse("users:faculty_dashboard")
        elif user.role == User.Role.MAINTENANCE:
            return reverse("users:maintenance_dashboard")
        elif user.role == User.Role.ADMIN or user.is_superuser:
            return reverse("users:admin_dashboard")
        return reverse("users:detail", kwargs={"username": user.username})


user_redirect_view = UserRedirectView.as_view()


