from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from smart_campus.complaints.models import Complaint

User = get_user_model()


class ComplaintModelTests(TestCase):
    def test_complaint_creation_and_auto_id(self):
        """Test that complaint creation automatically generates CMP-0001 ID and defaults status to Submitted."""
        complaint1 = Complaint.objects.create(
            title="Projector in Room 101 flickering",
            description="The projector flickers every few seconds during lectures.",
            category=Complaint.Category.IT_NETWORK,
            location="Room 101, Main Block",
            priority=Complaint.Priority.HIGH,
        )
        self.assertEqual(complaint1.complaint_id, "CMP-0001")
        self.assertEqual(complaint1.status, Complaint.Status.SUBMITTED)

        complaint2 = Complaint.objects.create(
            title="Broken chair in library",
            description="One leg is broken.",
            category=Complaint.Category.FURNITURE,
            location="Library 1st Floor",
            priority=Complaint.Priority.LOW,
        )
        self.assertEqual(complaint2.complaint_id, "CMP-0002")
        self.assertNotEqual(complaint1.complaint_id, complaint2.complaint_id)


class ComplaintViewsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="test_student",
            email="student@example.com",
            password="password123",
            role=User.Role.STUDENT,
        )
        self.staff = User.objects.create_user(
            username="test_staff",
            email="staff@example.com",
            password="password123",
            role=User.Role.MAINTENANCE,
        )
        self.complaint = Complaint.objects.create(
            title="Leaking pipe in restroom",
            description="Water leaking from sink pipe.",
            category=Complaint.Category.PLUMBING,
            location="Ground Floor Restroom",
            priority=Complaint.Priority.MEDIUM,
            user=self.user,
        )

    def test_complaint_list_view(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("complaints:list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "CMP-0001")
        self.assertContains(response, "Leaking pipe in restroom")

    def test_complaint_create_view_get(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("complaints:create"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Raise a Complaint")

    def test_complaint_create_view_post(self):
        self.client.force_login(self.user)
        post_data = {
            "title": "Air Conditioner not cooling",
            "category": Complaint.Category.ELECTRICAL,
            "location": "Faculty Room B",
            "priority": Complaint.Priority.HIGH,
            "description": "AC unit runs but does not cool.",
        }
        response = self.client.post(reverse("complaints:create"), post_data)
        self.assertEqual(response.status_code, 302)
        new_complaint = Complaint.objects.get(complaint_id="CMP-0002")
        self.assertEqual(new_complaint.title, "Air Conditioner not cooling")
        self.assertEqual(new_complaint.status, Complaint.Status.SUBMITTED)
        self.assertEqual(new_complaint.user, self.user)

    def test_complaint_detail_view(self):
        self.client.force_login(self.user)
        url = reverse("complaints:detail", kwargs={"complaint_id": self.complaint.complaint_id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Leaking pipe in restroom")
        self.assertContains(response, "Submitted")

    def test_complaint_status_update_view(self):
        self.client.force_login(self.staff)
        url = reverse("complaints:status_update", kwargs={"complaint_id": self.complaint.complaint_id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        post_data = {"status": Complaint.Status.IN_PROGRESS}
        response = self.client.post(url, post_data)
        self.assertEqual(response.status_code, 302)
        self.complaint.refresh_from_db()
        self.assertEqual(self.complaint.status, Complaint.Status.IN_PROGRESS)


class ComplaintSearchAndFilterTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            username="staff_filter",
            email="staff_filter@example.com",
            password="password123",
            role=User.Role.MAINTENANCE,
        )
        self.client.force_login(self.staff)

        self.c1 = Complaint.objects.create(
            title="Projector display distorted",
            description="Projector colours are inverted",
            category=Complaint.Category.IT_NETWORK,
            location="Room 101",
            priority=Complaint.Priority.HIGH,
            status=Complaint.Status.SUBMITTED,
        )
        self.c2 = Complaint.objects.create(
            title="Sink tap leaking",
            description="Water keeps dripping continuously",
            category=Complaint.Category.PLUMBING,
            location="Block A Restroom",
            priority=Complaint.Priority.MEDIUM,
            status=Complaint.Status.IN_PROGRESS,
        )
        self.c3 = Complaint.objects.create(
            title="Desk drawer broken",
            description="Drawer lock is jammed",
            category=Complaint.Category.FURNITURE,
            location="Staff Office 3",
            priority=Complaint.Priority.LOW,
            status=Complaint.Status.RESOLVED,
        )

    def test_search_by_complaint_id(self):
        url = reverse("complaints:list") + f"?search={self.c1.complaint_id}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.c1.complaint_id)
        self.assertNotContains(response, self.c2.complaint_id)

    def test_search_by_title(self):
        url = reverse("complaints:list") + "?search=Projector"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Projector display distorted")
        self.assertNotContains(response, "Sink tap leaking")

    def test_filter_by_category(self):
        url = reverse("complaints:list") + f"?category={Complaint.Category.PLUMBING}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Sink tap leaking")
        self.assertNotContains(response, "Projector display distorted")

    def test_filter_by_priority(self):
        url = reverse("complaints:list") + f"?priority={Complaint.Priority.HIGH}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Projector display distorted")
        self.assertNotContains(response, "Desk drawer broken")

    def test_filter_by_status(self):
        url = reverse("complaints:list") + f"?status={Complaint.Status.RESOLVED}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Desk drawer broken")
        self.assertNotContains(response, "Sink tap leaking")

    def test_multiple_filters_together(self):
        url = (
            reverse("complaints:list")
            + f"?category={Complaint.Category.IT_NETWORK}&priority={Complaint.Priority.HIGH}&status={Complaint.Status.SUBMITTED}"
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Projector display distorted")
        self.assertNotContains(response, "Sink tap leaking")

    def test_search_and_filters_combined(self):
        url = (
            reverse("complaints:list")
            + f"?search=distorted&category={Complaint.Category.IT_NETWORK}"
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Projector display distorted")

    def test_no_matching_results(self):
        url = reverse("complaints:list") + "?search=NonexistentKeyWord12345"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No Matching Complaints Found")

    def test_clear_reset_filters(self):
        url = reverse("complaints:list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.c1.complaint_id)
        self.assertContains(response, self.c2.complaint_id)
        self.assertContains(response, self.c3.complaint_id)


class IntegratedModuleTests(TestCase):
    def setUp(self):
        from smart_campus.assets.models import Asset
        from smart_campus.inventory.models import InventoryCategory, InventoryItem

        self.tech_user = User.objects.create_user(
            username="tech1",
            email="tech1@example.com",
            password="password123",
            role=User.Role.MAINTENANCE,
        )
        self.client.force_login(self.tech_user)

        self.asset = Asset.objects.create(
            asset_code="AST-9999",
            name="Lab Projector HD",
            category="Electronics",
            building="Science Block",
            room="Lab 3",
            status="ACTIVE",
        )
        self.category = InventoryCategory.objects.create(name="Electrical Parts")
        self.item = InventoryItem.objects.create(
            name="HDMI Cable 5m",
            category=self.category,
            quantity=10,
            minimum_quantity=2,
            unit="pcs",
        )
        self.complaint = Complaint.objects.create(
            title="Projector no signal",
            description="Cable is broken",
            category=Complaint.Category.IT_NETWORK,
            location="Science Block, Lab 3",
            priority=Complaint.Priority.HIGH,
            asset=self.asset,
        )

    def test_complaint_status_update_and_asset_status_sync(self):
        url = reverse("complaints:status_update", kwargs={"complaint_id": self.complaint.complaint_id})
        
        post_data = {
            "status": Complaint.Status.IN_PROGRESS,
            "assigned_to": self.tech_user.pk,
            "resolution_notes": "Replacing HDMI cable",
        }
        response = self.client.post(url, post_data)
        self.assertEqual(response.status_code, 302)

        self.complaint.refresh_from_db()
        self.asset.refresh_from_db()

        self.assertEqual(self.complaint.status, Complaint.Status.IN_PROGRESS)
        self.assertEqual(self.complaint.assigned_to, self.tech_user)
        self.assertIsNotNone(self.complaint.assigned_at)
        self.assertEqual(self.asset.status, "UNDER_MAINTENANCE")

        post_data_resolved = {
            "status": Complaint.Status.RESOLVED,
            "assigned_to": self.tech_user.pk,
            "resolution_notes": "Replaced HDMI cable successfully",
        }
        response = self.client.post(url, post_data_resolved)
        self.assertEqual(response.status_code, 302)

        self.complaint.refresh_from_db()
        self.asset.refresh_from_db()

        self.assertEqual(self.complaint.status, Complaint.Status.RESOLVED)
        self.assertIsNotNone(self.complaint.resolved_at)
        self.assertEqual(self.asset.status, "ACTIVE")

    def test_inventory_resource_consumption(self):
        url = reverse("complaints:add_resource", kwargs={"complaint_id": self.complaint.complaint_id})
        post_data = {
            "inventory_item": self.item.pk,
            "quantity_used": 2,
        }
        response = self.client.post(url, post_data)
        self.assertEqual(response.status_code, 302)

        self.item.refresh_from_db()
        self.assertEqual(self.item.quantity, 8)
        self.assertEqual(self.complaint.resources_used.count(), 1)
        res = self.complaint.resources_used.first()
        self.assertEqual(res.inventory_item, self.item)
        self.assertEqual(res.quantity_used, 2)


class ComplaintAuthenticationAndAuthorizationTests(TestCase):
    def setUp(self):
        self.student = User.objects.create_user(
            username="student_user",
            email="student@campus.edu",
            password="Password123!",
            role=User.Role.STUDENT,
        )
        self.other_student = User.objects.create_user(
            username="other_student",
            email="other_student@campus.edu",
            password="Password123!",
            role=User.Role.STUDENT,
        )
        self.tech_staff = User.objects.create_user(
            username="maint_tech",
            email="tech@campus.edu",
            password="Password123!",
            role=User.Role.MAINTENANCE,
        )
        self.complaint = Complaint.objects.create(
            title="Broken Light Switch",
            description="Switch sparked",
            category=Complaint.Category.ELECTRICAL,
            location="Room 201",
            priority=Complaint.Priority.MEDIUM,
            user=self.student,
        )

    def test_1_logged_out_user_accesses_complaint_creation_redirects_to_login(self):
        """TEST 1: Logged-out user accesses complaint creation URL -> redirected to login"""
        url = reverse("complaints:create")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        expected_login_url = f"{reverse('account_login')}?next={url}"
        self.assertRedirects(response, expected_login_url)

    def test_2_logged_in_user_accesses_complaint_creation_returns_form(self):
        """TEST 2: Logged-in user accesses complaint creation URL -> receives complaint form"""
        self.client.force_login(self.student)
        url = reverse("complaints:create")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Raise a Complaint")

    def test_3_logged_out_user_post_complaint_creation_redirects_to_login(self):
        """TEST 3: Logged-out user attempts POST to complaint creation -> cannot create complaint"""
        url = reverse("complaints:create")
        post_data = {
            "title": "Unauthorized Complaint",
            "category": Complaint.Category.OTHER,
            "location": "Main Gate",
            "priority": Complaint.Priority.LOW,
            "description": "Anonymous post attempt",
        }
        response = self.client.post(url, post_data)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Complaint.objects.filter(title="Unauthorized Complaint").exists())

    def test_4_logged_in_user_creates_complaint_successfully(self):
        """TEST 4: Logged-in user creates complaint -> complaint is created successfully"""
        self.client.force_login(self.student)
        url = reverse("complaints:create")
        post_data = {
            "title": "Water leak in hall",
            "category": Complaint.Category.PLUMBING,
            "location": "Main Hall",
            "priority": Complaint.Priority.MEDIUM,
            "description": "Water dripping from ceiling",
        }
        response = self.client.post(url, post_data)
        self.assertEqual(response.status_code, 302)
        created_complaint = Complaint.objects.get(title="Water leak in hall")
        self.assertIsNotNone(created_complaint)

    def test_5_created_complaint_automatically_belongs_to_request_user(self):
        """TEST 5: Created complaint automatically belongs to request.user"""
        self.client.force_login(self.student)
        url = reverse("complaints:create")
        post_data = {
            "title": "Desk broken",
            "category": Complaint.Category.FURNITURE,
            "location": "Room 302",
            "priority": Complaint.Priority.LOW,
            "description": "Leg missing",
        }
        self.client.post(url, post_data)
        created_complaint = Complaint.objects.get(title="Desk broken")
        self.assertEqual(created_complaint.user, self.student)

    def test_6_user_cannot_impersonate_another_user_through_form(self):
        """TEST 6: User cannot impersonate another user through complaint form"""
        self.client.force_login(self.student)
        url = reverse("complaints:create")
        post_data = {
            "title": "Impersonation Attempt",
            "category": Complaint.Category.OTHER,
            "location": "Room 101",
            "priority": Complaint.Priority.LOW,
            "description": "Form post trying to specify another user",
            "user": self.other_student.pk,
        }
        self.client.post(url, post_data)
        created_complaint = Complaint.objects.get(title="Impersonation Attempt")
        self.assertEqual(created_complaint.user, self.student)
        self.assertNotEqual(created_complaint.user, self.other_student)

    def test_7_unauthorized_user_cannot_update_complaint_status(self):
        """TEST 7: Unauthorized user (Student) cannot update complaint status -> 403 PermissionDenied"""
        self.client.force_login(self.student)
        url = reverse("complaints:status_update", kwargs={"complaint_id": self.complaint.complaint_id})
        response = self.client.post(url, {"status": Complaint.Status.RESOLVED})
        self.assertEqual(response.status_code, 403)
        self.complaint.refresh_from_db()
        self.assertNotEqual(self.complaint.status, Complaint.Status.RESOLVED)

    def test_8_authorized_role_can_update_complaint_status(self):
        """TEST 8: Authorized role (Maintenance Staff) can update complaint status"""
        self.client.force_login(self.tech_staff)
        url = reverse("complaints:status_update", kwargs={"complaint_id": self.complaint.complaint_id})
        response = self.client.post(url, {"status": Complaint.Status.IN_PROGRESS})
        self.assertEqual(response.status_code, 302)
        self.complaint.refresh_from_db()
        self.assertEqual(self.complaint.status, Complaint.Status.IN_PROGRESS)

    def test_9_raise_complaint_links_point_to_create_url(self):
        """TEST 9: All Raise Complaint links in templates point to the correct complaint URL"""
        response = self.client.get(reverse("home"))
        self.assertContains(response, reverse("complaints:create"))

    def test_student_cannot_view_other_students_complaint_detail(self):
        """Student A cannot view Student B's complaint detail (403 PermissionDenied)"""
        self.client.force_login(self.other_student)
        url = reverse("complaints:detail", kwargs={"complaint_id": self.complaint.complaint_id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_student_can_view_own_complaint_detail(self):
        """Student A can view Student A's complaint detail (200 OK)"""
        self.client.force_login(self.student)
        url = reverse("complaints:detail", kwargs={"complaint_id": self.complaint.complaint_id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_maintenance_staff_can_view_any_complaint_detail(self):
        """Maintenance Staff can view any complaint detail (200 OK)"""
        self.client.force_login(self.tech_staff)
        url = reverse("complaints:detail", kwargs={"complaint_id": self.complaint.complaint_id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)


