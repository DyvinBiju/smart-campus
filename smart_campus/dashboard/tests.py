from django.test import TestCase
from django.urls import reverse
from smart_campus.assets.models import Asset, Location
from smart_campus.complaints.models import Complaint
from smart_campus.inventory.models import InventoryCategory, InventoryItem
from smart_campus.users.models import User
from .models import Activity
from .helpers import seed_mock_activities

class DashboardViewTests(TestCase):
    def setUp(self):
        # Seed the mock activities which creates student1 and admin1
        seed_mock_activities()
        self.student = User.objects.get(username="student1")
        self.admin = User.objects.get(username="admin1")

    def test_anonymous_user_cannot_access_student_dashboard(self):
        """
        Unauthenticated users must be redirected to the login page.
        """
        response = self.client.get(reverse("dashboard:student"))
        self.assertRedirects(response, f"{reverse('account_login')}?next={reverse('dashboard:student')}")

    def test_anonymous_user_cannot_access_admin_dashboard(self):
        """
        Unauthenticated users must be redirected to the login page.
        """
        response = self.client.get(reverse("dashboard:admin"))
        self.assertRedirects(response, f"{reverse('account_login')}?next={reverse('dashboard:admin')}")

    def test_switch_role_and_redirect(self):
        """
        Verify switching views for authenticated admin.
        """
        self.client.force_login(self.admin)
        response = self.client.get(reverse("dashboard:switch-role") + "?role=student")
        self.assertRedirects(response, reverse("dashboard:student"))
        
        response = self.client.get(reverse("dashboard:switch-role") + "?role=admin")
        self.assertRedirects(response, reverse("dashboard:admin"))

    def test_dashboard_index_redirects_based_on_role(self):
        """
        Index page should redirect to admin dashboard for admin and student dashboard for student.
        """
        # Admin logged in
        self.client.force_login(self.admin)
        response = self.client.get(reverse("dashboard:index"))
        self.assertRedirects(response, reverse("dashboard:admin"))
        
        # Student logged in
        self.client.force_login(self.student)
        response = self.client.get(reverse("dashboard:index"))
        self.assertRedirects(response, reverse("dashboard:student"))

    def test_student_dashboard_renders_student_complaints(self):
        """
        Student dashboard should render complaints related to the student user.
        """
        Complaint.objects.create(
            title="Water leakage in Hostel Block C restroom",
            description="Water is dripping constantly.",
            category=Complaint.Category.PLUMBING,
            location="Hostel Block C",
            priority=Complaint.Priority.HIGH,
            user=self.student,
        )
        Complaint.objects.create(
            title="Library Wi-Fi connection issues",
            description="Connection frequently drops.",
            category=Complaint.Category.IT_NETWORK,
            location="Library",
            priority=Complaint.Priority.MEDIUM,
            user=self.student,
            status=Complaint.Status.RESOLVED,
        )
        Complaint.objects.create(
            title="Smart board in Lecture Hall 204 not turning on",
            description="Power indicator is flashing red.",
            category=Complaint.Category.IT_NETWORK,
            location="Lecture Hall 204",
            priority=Complaint.Priority.MEDIUM,
            user=self.student,
            status=Complaint.Status.IN_PROGRESS,
        )
        self.client.force_login(self.student)
        response = self.client.get(reverse("dashboard:student"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "dashboard/student_dashboard.html")
        self.assertContains(response, "John Student")
        
        # Verify it lists student's seeded complaints
        self.assertContains(response, "Water leakage in Hostel Block C restroom")
        self.assertContains(response, "Library Wi-Fi connection issues")
        
        # Metrics count verification (John has 3 complaints seeded)
        self.assertEqual(response.context["complaints_stats"]["total"], 3)

    def test_student_dashboard_only_shows_own_complaints(self):
        other_student = User.objects.create_user(
            username="other_student",
            email="other_student@campus.edu",
            password="Password123!",
            role=User.Role.STUDENT,
            name="Other Student",
        )
        Complaint.objects.create(
            title="My projector issue",
            description="Projector needs attention.",
            category=Complaint.Category.IT_NETWORK,
            location="Lab 205",
            user=self.student,
        )
        Complaint.objects.create(
            title="Another user's private complaint",
            description="This must not appear.",
            category=Complaint.Category.OTHER,
            location="Other Room",
            user=other_student,
        )

        self.client.force_login(self.student)
        response = self.client.get(reverse("dashboard:student"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "John Student")
        self.assertContains(response, "My projector issue")
        self.assertNotContains(response, "Another user's private complaint")
        self.assertEqual(response.context["complaints_stats"]["total"], 1)

    def test_empty_student_dashboard_has_zero_counts_and_empty_state(self):
        new_student = User.objects.create_user(
            username="empty_dashboard_student",
            email="empty_dashboard@campus.edu",
            password="Password123!",
            role=User.Role.STUDENT,
        )
        self.client.force_login(new_student)

        response = self.client.get(reverse("dashboard:student"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "You have not submitted any complaints yet.")
        self.assertEqual(response.context["complaints_stats"]["total"], 0)
        self.assertEqual(response.context["complaints_stats"]["resolved"], 0)

    def test_student_can_update_own_profile_without_changing_role(self):
        self.client.force_login(self.student)
        profile_url = reverse("users:profile_edit")
        response = self.client.post(profile_url, {
            "name": "Updated Student",
            "email": self.student.email,
            "department": "Computer Science",
            "campus_id": "STU-001",
            "year_or_semester": "Semester 4",
            "phone_number": "5550100100",
        })

        self.assertRedirects(response, reverse("dashboard:student"))
        self.student.refresh_from_db()
        self.assertEqual(self.student.name, "Updated Student")
        self.assertEqual(self.student.role, User.Role.STUDENT)

    def test_administrator_cannot_use_student_profile_editor(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("users:profile_edit"))
        self.assertEqual(response.status_code, 403)

    def test_admin_dashboard_renders_all_metrics(self):
        """
        Admin dashboard should display campus-wide metrics from the Activity model.
        """
        self.client.force_login(self.admin)
        response = self.client.get(reverse("dashboard:admin"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "dashboard/admin_dashboard.html")
        
        # Assert metrics are fetched
        self.assertGreater(response.context["complaints_stats"]["total"], 0)
        self.assertGreater(response.context["assets_stats"]["total"], 0)
        self.assertGreater(response.context["inventory_stats"]["total"], 0)
        
        # Verify audit activity feed is shown
        self.assertContains(response, "Water leakage in Hostel Block C restroom")
        self.assertContains(response, "Dry erase markers")

    def test_report_export_print_format(self):
        """
        Reports view should render real database records in the printable layout.
        """
        location = Location.objects.create(name="Science Block")
        complaint = Complaint.objects.create(
            title="Broken laboratory fan",
            description="The fan is not working.",
            category=Complaint.Category.ELECTRICAL,
            location_record=location,
            priority=Complaint.Priority.HIGH,
            user=self.student,
        )
        Asset.objects.create(
            name="Laboratory Fan",
            category="Electrical & Utilities",
            location=location,
            building="Science Block",
            status="ACTIVE",
        )
        category = InventoryCategory.objects.create(name="Maintenance Supplies")
        InventoryItem.objects.create(
            name="Replacement Fuse",
            category=category,
            quantity=4,
            minimum_quantity=2,
        )

        self.client.force_login(self.admin)
        response = self.client.get(reverse("dashboard:reports") + "?format=print")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "dashboard/reports_export.html")
        self.assertContains(response, "Operations Executive Summary")
        self.assertContains(response, "Detailed Project Activities Audit Log")
        self.assertContains(response, complaint.complaint_id)
        self.assertContains(response, "Laboratory Fan")
        self.assertContains(response, "Replacement Fuse")
        self.assertEqual(response.context["summary"]["complaints"], 1)
        self.assertEqual(response.context["summary"]["assets"], 1)
        self.assertEqual(response.context["summary"]["inventory"], 1)
        self.assertNotContains(response, "Water leakage in Hostel Block C restroom")

    def test_report_export_csv_format(self):
        """
        Reports view should generate CSV from real database records.
        """
        complaint = Complaint.objects.create(
            title="Damaged classroom chair",
            description="One chair is damaged.",
            category=Complaint.Category.FURNITURE,
            user=self.student,
        )

        self.client.force_login(self.admin)
        response = self.client.get(reverse("dashboard:reports") + "?format=csv")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertTrue(response["Content-Disposition"].startswith('attachment; filename="smart_campus_activities_report_'))
        
        content = response.content.decode("utf-8")
        self.assertIn("Smart Campus - All Project Activities Audit Report", content)
        self.assertIn("--- Activity Type Summaries ---", content)
        self.assertIn("--- Detailed Activity Audit Logs ---", content)
        self.assertIn(complaint.complaint_id, content)
        self.assertIn("Damaged classroom chair", content)
        self.assertNotIn("Water leakage in Hostel Block C restroom", content)

    def test_maintenance_staff_dashboard_access_and_authorization(self):
        """
        Verify role-based security & rendering for the dedicated Maintenance Staff dashboard.
        """
        staff_user = User.objects.create_user(
            username="maint_tech_dash",
            email="tech_dash@campus.edu",
            password="Password123!",
            role=User.Role.MAINTENANCE,
            is_available=True,
        )

        # 1. Anonymous user -> redirect to login
        anon_response = self.client.get(reverse("dashboard:maintenance"))
        self.assertRedirects(anon_response, f"{reverse('account_login')}?next={reverse('dashboard:maintenance')}")

        # 2. Student user -> redirected away from maintenance dashboard
        self.client.force_login(self.student)
        student_response = self.client.get(reverse("dashboard:maintenance"))
        self.assertRedirects(student_response, reverse("dashboard:student"))

        # 3. Landing index redirect for Maintenance Staff
        self.client.force_login(staff_user)
        index_response = self.client.get(reverse("dashboard:index"))
        self.assertRedirects(index_response, reverse("dashboard:maintenance"))

        # 4. Maintenance Staff direct access -> 200 OK & template used
        dashboard_response = self.client.get(reverse("dashboard:maintenance"))
        self.assertEqual(dashboard_response.status_code, 200)
        self.assertTemplateUsed(dashboard_response, "dashboard/maintenance_dashboard.html")
        self.assertContains(dashboard_response, "Maintenance Operations Hub")
        self.assertContains(dashboard_response, "Status: Available for Work")

    def test_maintenance_staff_cannot_access_administrator_views(self):
        staff_user = User.objects.create_user(
            username="maint_admin_boundary",
            email="maint_admin_boundary@campus.edu",
            password="Password123!",
            role=User.Role.MAINTENANCE,
        )
        self.client.force_login(staff_user)

        dashboard_response = self.client.get(reverse("dashboard:admin"))
        self.assertRedirects(dashboard_response, reverse("dashboard:student"))

        report_response = self.client.get(reverse("dashboard:reports"))
        self.assertRedirects(report_response, reverse("dashboard:student"))

    def test_admin_sidebar_uses_route_aware_active_navigation(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("dashboard:admin"))
        self.assertContains(response, 'aria-current="page"')
        self.assertContains(response, 'id="dashboard-sidebar"')
        self.assertNotContains(response, "Maintenance Workspace")
        self.assertNotContains(response, "Maintenance Hub")
        self.assertNotContains(response, "My Assigned Work")
        self.assertNotContains(response, "Resource Inventory")

    def test_maintenance_sidebar_is_visible_only_to_maintenance_role(self):
        maintenance_user = User.objects.create_user(
            username="maint_sidebar",
            email="maint_sidebar@campus.edu",
            password="Password123!",
            role=User.Role.MAINTENANCE,
            is_staff=True,
        )
        self.client.force_login(maintenance_user)
        maintenance_response = self.client.get(reverse("dashboard:maintenance"))
        self.assertContains(maintenance_response, "Maintenance Workspace")
        self.assertContains(maintenance_response, "Maintenance Hub")
        self.assertContains(maintenance_response, "My Assigned Work")

        self.client.force_login(self.student)
        student_response = self.client.get(reverse("dashboard:student"))
        self.assertNotContains(student_response, "Maintenance Workspace")
        self.assertNotContains(student_response, "Maintenance Hub")

    def test_submit_complaint_rejects_overlong_title(self):
        """Overlong titles must be rejected instead of hitting the DB limit."""
        self.client.force_login(self.student)
        response = self.client.post(
            reverse("dashboard:submit-complaint"),
            data={"title": "x" * 300, "description": "Too long title"},
            follow=True,
        )
        self.assertContains(response, "must not exceed 255 characters")
        self.assertFalse(Activity.objects.filter(description="Too long title").exists())

    def test_submit_complaint_rejects_blank_title(self):
        self.client.force_login(self.student)
        response = self.client.post(
            reverse("dashboard:submit-complaint"),
            data={"title": "   ", "description": "Blank title"},
            follow=True,
        )
        self.assertContains(response, "Complaint title is required.")

