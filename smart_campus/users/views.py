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
from django.db.models import Q, Count
from django.views.generic import ListView, DetailView, CreateView, UpdateView, View
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404

from smart_campus.users.forms import (
    FacultySignupForm,
    StudentSignupForm,
    UserManagementCreateForm,
    UserManagementEditForm,
)
from smart_campus.complaints.models import Complaint


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


class UserManagementListView(RoleRequiredMixin, ListView):
    """
    Admin control console user management directory.
    Displays search, role filters, status filters, and pagination.
    """

    allowed_roles = [User.Role.ADMIN]
    model = User
    template_name = "users/user_list.html"
    context_object_name = "users_list"
    paginate_by = 15

    def get_queryset(self):
        queryset = User.objects.all().order_by("-date_joined")

        # Search filter (name, username, email, campus_id)
        search_query = self.request.GET.get("q", "").strip()
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query)
                | Q(username__icontains=search_query)
                | Q(email__icontains=search_query)
                | Q(campus_id__icontains=search_query)
                | Q(department__icontains=search_query)
            )

        # Role filter
        role_filter = self.request.GET.get("role", "").strip()
        if role_filter:
            queryset = queryset.filter(role=role_filter)

        # Status filter (Active / Inactive)
        status_filter = self.request.GET.get("status", "").strip()
        if status_filter == "active":
            queryset = queryset.filter(is_active=True)
        elif status_filter == "inactive":
            queryset = queryset.filter(is_active=False)

        # Staff availability filter
        avail_filter = self.request.GET.get("availability", "").strip()
        if avail_filter == "available":
            queryset = queryset.filter(is_available=True)
        elif avail_filter == "unavailable":
            queryset = queryset.filter(is_available=False)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        all_users = User.objects.all()

        context["total_users"] = all_users.count()
        context["active_users"] = all_users.filter(is_active=True).count()
        context["inactive_users"] = all_users.filter(is_active=False).count()
        context["student_count"] = all_users.filter(role=User.Role.STUDENT).count()
        context["faculty_count"] = all_users.filter(role=User.Role.FACULTY).count()
        context["maintenance_count"] = all_users.filter(role=User.Role.MAINTENANCE).count()
        context["admin_count"] = all_users.filter(role=User.Role.ADMIN).count()

        context["role_choices"] = User.Role.choices
        context["search_query"] = self.request.GET.get("q", "")
        context["selected_role"] = self.request.GET.get("role", "")
        context["selected_status"] = self.request.GET.get("status", "")
        context["selected_availability"] = self.request.GET.get("availability", "")
        return context


class UserManagementDetailView(RoleRequiredMixin, DetailView):
    """
    Detailed profile, complaint history, and maintenance assignments view for a user.
    """

    allowed_roles = [User.Role.ADMIN]
    model = User
    template_name = "users/user_detail.html"
    context_object_name = "managed_user"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        target_user = self.object

        # User's submitted complaints
        submitted_complaints = Complaint.objects.filter(user=target_user)
        context["submitted_complaints"] = submitted_complaints[:10]
        context["total_submitted_count"] = submitted_complaints.count()
        context["open_submitted_count"] = submitted_complaints.exclude(status__in=["Resolved", "Closed"]).count()
        context["resolved_submitted_count"] = submitted_complaints.filter(status__in=["Resolved", "Closed"]).count()

        # Maintenance assignments if user is maintenance staff or admin
        if target_user.is_maintenance_staff or target_user.is_admin_user:
            assigned_complaints = Complaint.objects.filter(assigned_to=target_user)
            context["assigned_complaints"] = assigned_complaints[:10]
            context["total_assigned_count"] = assigned_complaints.count()
            context["active_assigned_count"] = assigned_complaints.exclude(status__in=["Resolved", "Closed"]).count()
            context["completed_assigned_count"] = assigned_complaints.filter(status__in=["Resolved", "Closed"]).count()

        return context


class UserManagementCreateView(RoleRequiredMixin, FormView):
    """
    Form view allowing Administrators to create new user accounts.
    """

    allowed_roles = [User.Role.ADMIN]
    template_name = "users/user_form.html"
    form_class = UserManagementCreateForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = _("Create New User Account")
        context["button_text"] = _("Create User")
        return context

    def form_valid(self, form):
        new_user = form.save()
        messages.success(
            self.request,
            _(f"User account '{new_user.name or new_user.username}' ({new_user.get_role_display()}) created successfully!"),
        )
        return redirect("users:manage")


class UserManagementEditView(RoleRequiredMixin, UpdateView):
    """
    Form view allowing Administrators to edit user details with server-side safeguards.
    """

    allowed_roles = [User.Role.ADMIN]
    model = User
    form_class = UserManagementEditForm
    template_name = "users/user_form.html"
    success_url = reverse_lazy("users:manage")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = _(f"Edit User: {self.object.name or self.object.username}")
        context["button_text"] = _("Save Changes")
        context["managed_user"] = self.object
        return context

    def form_valid(self, form):
        target_user = self.object
        current_admin = self.request.user
        new_role = form.cleaned_data.get("role")
        new_is_active = form.cleaned_data.get("is_active")

        # Safeguard 1: Admin self-demotion / self-deactivation protection
        if target_user.pk == current_admin.pk:
            if new_role != User.Role.ADMIN:
                messages.error(self.request, _("Action denied: You cannot remove administrative access from your own account."))
                return self.form_invalid(form)
            if not new_is_active:
                messages.error(self.request, _("Action denied: You cannot deactivate your own administrative account."))
                return self.form_invalid(form)

        # Safeguard 2: Sole active administrator protection
        if target_user.role == User.Role.ADMIN and (new_role != User.Role.ADMIN or not new_is_active):
            active_admin_count = User.objects.filter(role=User.Role.ADMIN, is_active=True).count()
            if active_admin_count <= 1:
                messages.error(
                    self.request,
                    _("Action denied: Cannot demote or deactivate the last remaining active Administrator in the system."),
                )
                return self.form_invalid(form)

        messages.success(self.request, _(f"User '{target_user.username}' updated successfully."))
        return super().form_valid(form)


class UserManagementToggleActiveView(RoleRequiredMixin, View):
    """
    POST action endpoint to toggle active / inactive status safely.
    """

    allowed_roles = [User.Role.ADMIN]

    def post(self, request, pk, *args, **kwargs):
        target_user = get_object_or_404(User, pk=pk)
        current_admin = request.user

        # Safeguard 1: Cannot deactivate yourself
        if target_user.pk == current_admin.pk:
            messages.error(request, _("Action denied: You cannot deactivate your own account."))
            return redirect("users:manage")

        # Safeguard 2: Cannot deactivate sole active administrator
        if target_user.role == User.Role.ADMIN and target_user.is_active:
            active_admin_count = User.objects.filter(role=User.Role.ADMIN, is_active=True).count()
            if active_admin_count <= 1:
                messages.error(
                    request,
                    _("Action denied: Cannot deactivate the sole active Administrator account."),
                )
                return redirect("users:manage")

        # Toggle status
        target_user.is_active = not target_user.is_active
        target_user.save()

        status_text = "activated" if target_user.is_active else "deactivated"
        messages.success(
            request,
            _(f"User account '{target_user.name or target_user.username}' was {status_text} successfully."),
        )
        return redirect("users:manage")


class MaintenanceStaffListView(RoleRequiredMixin, ListView):
    """
    Dedicated view for Administrators to manage Maintenance Staff workload and availability.
    """

    allowed_roles = [User.Role.ADMIN]
    model = User
    template_name = "users/staff_list.html"
    context_object_name = "staff_list"

    def get_queryset(self):
        return User.objects.filter(Q(role=User.Role.MAINTENANCE) | Q(is_staff=True)).distinct().order_by("name", "username")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        staff_qs = self.get_queryset()

        staff_data = []
        for staff in staff_qs:
            assigned = Complaint.objects.filter(assigned_to=staff)
            active_jobs = assigned.exclude(status__in=["Resolved", "Closed"]).count()
            completed_jobs = assigned.filter(status__in=["Resolved", "Closed"]).count()
            staff_data.append({
                "user": staff,
                "active_jobs": active_jobs,
                "completed_jobs": completed_jobs,
            })

        context["staff_members"] = staff_data
        context["total_staff"] = staff_qs.count()
        context["available_staff"] = staff_qs.filter(is_available=True).count()
        context["unavailable_staff"] = staff_qs.filter(is_available=False).count()
        return context


class MaintenanceStaffToggleAvailabilityView(RoleRequiredMixin, View):
    """
    POST action endpoint for Admin to toggle maintenance staff availability status.
    """

    allowed_roles = [User.Role.ADMIN]

    def post(self, request, pk, *args, **kwargs):
        staff_member = get_object_or_404(User, pk=pk)
        staff_member.is_available = not staff_member.is_available
        staff_member.save()

        status_text = "Available" if staff_member.is_available else "Unavailable"
        messages.success(
            request,
            _(f"Maintenance staff '{staff_member.name or staff_member.username}' availability updated to {status_text}."),
        )
        return redirect("users:staff")







