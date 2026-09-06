from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from smart_campus.assets.models import Asset
from .models import InventoryCategory, InventoryItem, StockTransaction

User = get_user_model()


class InventoryModelTest(TestCase):
    def setUp(self):
        self.category = InventoryCategory.objects.create(
            name="IT Supplies", description="Computer consumables and networking materials"
        )
        self.item = InventoryItem.objects.create(
            name="HDMI Cable 2m",
            category=self.category,
            quantity=15,
            minimum_quantity=5,
            unit="pieces",
            storage_location="Room 101",
        )
        self.asset = Asset.objects.create(
            name="Dell OptiPlex Desktop",
            category="IT & Computers",
            building="Academic Block A",
            room="Lab 101",
        )

    def test_item_creation_and_stock_status(self):
        """Test item fields and stock status derivation."""
        self.assertEqual(self.item.name, "HDMI Cable 2m")
        self.assertEqual(self.item.stock_status, "In Stock")

        # Test Low Stock
        self.item.quantity = 4
        self.item.save()
        self.assertEqual(self.item.stock_status, "Low Stock")

        # Test Out of Stock
        self.item.quantity = 0
        self.item.save()
        self.assertEqual(self.item.stock_status, "Out of Stock")

    def test_stock_receive_transaction(self):
        """Test receiving stock increases quantity."""
        tx = StockTransaction.objects.create(
            item=self.item,
            transaction_type="RECEIVE",
            quantity=10,
            notes="Received new batch from vendor",
        )
        self.item.refresh_from_db()
        self.assertEqual(self.item.quantity, 25)
        self.assertEqual(tx.quantity, 10)

    def test_stock_issue_transaction(self):
        """Test issuing stock decreases quantity."""
        tx = StockTransaction.objects.create(
            item=self.item,
            transaction_type="ISSUE",
            quantity=5,
            asset=self.asset,
            notes="Issued cable for Dell OptiPlex setup",
        )
        self.item.refresh_from_db()
        self.assertEqual(self.item.quantity, 10)
        self.assertEqual(tx.asset, self.asset)

    def test_prevent_over_issuing_stock(self):
        """Test that issuing more than available stock raises ValidationError."""
        tx = StockTransaction(
            item=self.item,
            transaction_type="ISSUE",
            quantity=20,  # Available is 15
        )
        with self.assertRaises(ValidationError):
            tx.save()

    def test_asset_code_auto_generation(self):
        """Test that Asset automatically generates unique AST-XXXX code when blank."""
        self.assertTrue(self.asset.asset_code.startswith("AST-"))
        asset2 = Asset.objects.create(
            name="Epson Projector",
            category="Audio / Visual",
            building="Main Block",
        )
        self.assertTrue(asset2.asset_code.startswith("AST-"))
        self.assertNotEqual(self.asset.asset_code, asset2.asset_code)


from smart_campus.complaints.models import Complaint, MaintenanceRequest, ComplaintResource


class InventoryViewsPermissionsTest(TestCase):
    def setUp(self):
        self.category = InventoryCategory.objects.create(name="Paper Products")
        self.item = InventoryItem.objects.create(
            name="A4 Paper Reams",
            category=self.category,
            quantity=50,
            minimum_quantity=10,
            unit="reams",
        )
        self.out_item = InventoryItem.objects.create(
            name="HDMI Cable 5m",
            category=self.category,
            quantity=0,
            minimum_quantity=5,
            unit="pieces",
        )
        self.admin_user = User.objects.create_superuser(
            username="admin_test",
            email="admin@test.com",
            password="password123",
            role=User.Role.ADMIN,
        )
        self.staff_user = User.objects.create_user(
            username="staff_test",
            email="staff@test.com",
            password="password123",
            role=User.Role.MAINTENANCE,
        )
        self.student_user = User.objects.create_user(
            username="student_test",
            email="student@test.com",
            password="password123",
            role=User.Role.STUDENT,
        )
        self.complaint = Complaint.objects.create(
            title="Printer paper depleted",
            description="Library printer out of paper",
            location="Library Floor 1",
            user=self.student_user,
            assigned_to=self.staff_user,
            status="In Progress",
        )

    def test_student_access_denied(self):
        """Test that Students are blocked from accessing inventory views."""
        self.client.force_login(self.student_user)
        response = self.client.get(reverse("inventory:list"))
        self.assertEqual(response.status_code, 403)

    def test_maintenance_staff_read_access(self):
        """Test that Maintenance Staff can view inventory list & details."""
        self.client.force_login(self.staff_user)

        response = self.client.get(reverse("inventory:list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "A4 Paper Reams")

        detail_resp = self.client.get(reverse("inventory:detail", kwargs={"pk": self.item.pk}))
        self.assertEqual(detail_resp.status_code, 200)

    def test_student_cannot_create_inventory(self):
        """Test that non-admin (student) cannot create inventory items."""
        self.client.force_login(self.student_user)
        response = self.client.get(reverse("inventory:create"))
        self.assertEqual(response.status_code, 302)

    def test_admin_can_create_inventory(self):
        """Test that admin user can access create view and add item."""
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse("inventory:create"))
        self.assertEqual(response.status_code, 200)

        data = {
            "name": "Whiteboard Markers",
            "category": self.category.pk,
            "quantity": 100,
            "minimum_quantity": 20,
            "unit": "boxes",
            "storage_location": "Store 1",
            "description": "Black and blue markers",
        }
        post_res = self.client.post(reverse("inventory:create"), data)
        self.assertEqual(post_res.status_code, 302)
        self.assertTrue(InventoryItem.objects.filter(name="Whiteboard Markers").exists())

    def test_maintenance_staff_use_inventory_for_assigned_complaint(self):
        """Test Maintenance Staff using inventory for their assigned complaint."""
        self.client.force_login(self.staff_user)

        res = self.client.post(
            reverse("inventory:use_for_complaint", kwargs={"pk": self.item.pk}),
            data={
                "complaint_id": self.complaint.pk,
                "quantity": 3,
            },
            follow=True,
        )
        self.assertEqual(res.status_code, 200)

        # 1. Quantity is reduced from 50 to 47
        self.item.refresh_from_db()
        self.assertEqual(self.item.quantity, 47)

        # 2. StockTransaction created
        self.assertTrue(StockTransaction.objects.filter(item=self.item, transaction_type="ISSUE", quantity=3).exists())

        # 3. ComplaintResource created
        self.assertTrue(ComplaintResource.objects.filter(complaint=self.complaint, inventory_item=self.item, quantity_used=3).exists())

    def test_maintenance_staff_cannot_over_issue_inventory(self):
        """Test that attempting to use more than available stock is rejected."""
        self.client.force_login(self.staff_user)

        res = self.client.post(
            reverse("inventory:use_for_complaint", kwargs={"pk": self.out_item.pk}),
            data={
                "complaint_id": self.complaint.pk,
                "quantity": 1,
            },
            follow=True,
        )
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Insufficient stock")
        self.assertEqual(self.out_item.quantity, 0)

    def test_maintenance_staff_report_resource_unavailable(self):
        """Test Maintenance Staff reporting an out-of-stock item to Administrator."""
        self.client.force_login(self.staff_user)

        res = self.client.post(
            reverse("inventory:report_unavailable", kwargs={"pk": self.out_item.pk}),
            data={
                "complaint_id": self.complaint.pk,
                "quantity": 2,
                "reason": "Need 5m HDMI cable for projector replacement",
            },
            follow=True,
        )
        self.assertEqual(res.status_code, 200)
        self.assertTrue(
            MaintenanceRequest.objects.filter(
                complaint=self.complaint,
                inventory_item=self.out_item,
                request_type=MaintenanceRequest.RequestType.UNAVAILABLE_RESOURCE,
            ).exists()
        )

    def test_admin_stock_transaction_flow(self):
        """Test admin processing stock transaction via POST view."""
        self.client.force_login(self.admin_user)
        data = {
            "transaction_type": "RECEIVE",
            "quantity": 20,
            "notes": "Weekly stock delivery",
        }
        res = self.client.post(reverse("inventory:stock_transaction", kwargs={"pk": self.item.pk}), data)
        self.assertEqual(res.status_code, 302)
        self.item.refresh_from_db()
        self.assertEqual(self.item.quantity, 70)


