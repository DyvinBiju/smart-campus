from django.test import TestCase
from django.urls import reverse
from smart_campus.users.models import User
from .models import Activity
from .helpers import seed_mock_activities

class DashboardViewTests(TestCase):
    def setUp(self):
        # Seed the mock activities which creates student1 and admin1
        seed_mock_activities()
        self.student = User.objects.get(username="student1")
        self.admin = User.objects.get(username="admin1")

    def test_switch_role_and_redirect(self):
        """
        Verify switching roles works and sets the correct session variable.
        """
        # Switch to student role
        response = self.client.get(reverse("dashboard:switch-role") + "?role=student")
        self.assertRedirects(response, reverse("dashboard:index"), target_status_code=302)
        self.assertEqual(self.client.session["preview_role"], "student")
        
        # Switch to admin role
        response = self.client.get(reverse("dashboard:switch-role") + "?role=admin")
        self.assertRedirects(response, reverse("dashboard:index"), target_status_code=302)
        self.assertEqual(self.client.session["preview_role"], "admin")

    def test_dashboard_index_redirects_based_on_role(self):
        """
        Index page should redirect to the admin or student dashboard depending on simulated role.
        """
        # Default is admin
        response = self.client.get(reverse("dashboard:index"))
        self.assertRedirects(response, reverse("dashboard:admin"))
        
        # Switch session to student
        session = self.client.session
        session["preview_role"] = "student"
        session.save()
        
        response = self.client.get(reverse("dashboard:index"))
        self.assertRedirects(response, reverse("dashboard:student"))

    def test_student_dashboard_renders_student_complaints(self):
        """
        Student dashboard should render complaints related to the student user.
        """
        # Force student role preview
        session = self.client.session
        session["preview_role"] = "student"
        session.save()
        
        response = self.client.get(reverse("dashboard:student"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "dashboard/student_dashboard.html")
        self.assertContains(response, "John Student")
        
        # Verify it lists student's seeded complaints
        self.assertContains(response, "Water leakage in Hostel Block C restroom")
        self.assertContains(response, "Library Wi-Fi connection issues")
        
        # Metrics count verification (John has 3 complaints seeded)
        self.assertEqual(response.context["complaints_stats"]["total"], 3)

    def test_admin_dashboard_renders_all_metrics(self):
        """
        Admin dashboard should display campus-wide metrics from the Activity model.
        """
        # Force admin role preview
        session = self.client.session
        session["preview_role"] = "admin"
        session.save()
        
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
        Reports view should render print layout with executive summary and list of activities.
        """
        response = self.client.get(reverse("dashboard:reports") + "?format=print")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "dashboard/reports_export.html")
        self.assertContains(response, "Operations Executive Summary")
        self.assertContains(response, "Detailed Project Activities Audit Log")
        self.assertContains(response, "Xerox Paper")

    def test_report_export_csv_format(self):
        """
        Reports view should generate and export CSV files with all activities.
        """
        response = self.client.get(reverse("dashboard:reports") + "?format=csv")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertTrue(response["Content-Disposition"].startswith('attachment; filename="smart_campus_activities_report_'))
        
        content = response.content.decode("utf-8")
        self.assertIn("Smart Campus - All Project Activities Audit Report", content)
        self.assertIn("--- Activity Type Summaries ---", content)
        self.assertIn("--- Detailed Activity Audit Logs ---", content)
        self.assertIn("Water leakage", content)
