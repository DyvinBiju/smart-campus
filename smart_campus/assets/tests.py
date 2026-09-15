from django.test import TestCase
from django.urls import reverse

from .models import Asset


class AssetModelTest(TestCase):
    """
    Unit tests for the Asset model logic and methods.
    """

    def setUp(self):
        self.asset = Asset.objects.create(
            asset_code="AST-001",
            name="Dell OptiPlex 7090",
            category="IT & Computers",
            building="Academic Block A",
            room="Lab 101",
            status="ACTIVE",
            description="Core i7, 16GB RAM Desktop PC",
        )

    def test_asset_creation(self):
        """Test that an asset is created with correct fields."""
        self.assertEqual(self.asset.asset_code, "AST-001")
        self.assertEqual(self.asset.name, "Dell OptiPlex 7090")
        self.assertEqual(self.asset.status, "ACTIVE")

    def test_asset_str_representation(self):
        """Test the string representation of an asset."""
        self.assertEqual(str(self.asset), "AST-001 - Dell OptiPlex 7090")

    def test_asset_absolute_url(self):
        """Test get_absolute_url returns the correct detail URL."""
        expected_url = reverse("assets:asset_detail", kwargs={"pk": self.asset.pk})
        self.assertEqual(self.asset.get_absolute_url(), expected_url)

    def test_status_badge_class(self):
        """Test helper property returns correct Bootstrap badge class."""
        self.assertEqual(self.asset.status_badge_class, "bg-success")
        self.asset.status = "UNDER_MAINTENANCE"
        self.assertEqual(self.asset.status_badge_class, "bg-warning text-dark")
        self.asset.status = "DAMAGED"
        self.assertEqual(self.asset.status_badge_class, "bg-danger")


from smart_campus.users.models import User


class AssetViewsTest(TestCase):
    """
    Unit tests for Asset CRUD views, role permissions, and search/filter functionality.
    """

    def setUp(self):
        self.admin = User.objects.create_user(
            username="adminuser",
            email="admin@campus.edu",
            password="password123",
            role=User.Role.ADMIN,
            is_staff=True,
            is_superuser=True,
        )
        self.staff = User.objects.create_user(
            username="staffuser",
            email="staff@campus.edu",
            password="password123",
            role=User.Role.MAINTENANCE,
        )
        self.student = User.objects.create_user(
            username="studentuser",
            email="student@campus.edu",
            password="password123",
            role=User.Role.STUDENT,
        )

        self.asset1 = Asset.objects.create(
            asset_code="AST-101",
            name="Projector Epson EB-X06",
            category="Audio / Visual",
            building="Seminar Hall",
            room="Hall B",
            status="ACTIVE",
        )
        self.asset2 = Asset.objects.create(
            asset_code="AST-102",
            name="Chemistry Lab Microscope",
            category="Lab Equipment",
            building="Science Block",
            room="Lab 3",
            status="UNDER_MAINTENANCE",
        )

    def test_student_access_denied(self):
        """Test that Students are blocked from asset management."""
        self.client.force_login(self.student)
        response = self.client.get(reverse("assets:asset_list"))
        self.assertEqual(response.status_code, 403)

    def test_maintenance_staff_read_only_access(self):
        """Test that Maintenance Staff can view asset list/detail but not create/edit/delete."""
        self.client.force_login(self.staff)

        # 1. Staff can view list
        response = self.client.get(reverse("assets:asset_list"))
        self.assertEqual(response.status_code, 200)

        # 2. Staff can view detail
        detail_resp = self.client.get(reverse("assets:asset_detail", kwargs={"pk": self.asset1.pk}))
        self.assertEqual(detail_resp.status_code, 200)

        # 3. Staff cannot access create form
        create_resp = self.client.get(reverse("assets:asset_create"))
        self.assertEqual(create_resp.status_code, 403)

    def test_admin_asset_list_view(self):
        """Test asset list page loads correctly for admin with statistics."""
        self.client.force_login(self.admin)
        response = self.client.get(reverse("assets:asset_list"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "assets/asset_list.html")
        self.assertContains(response, "AST-101")
        self.assertContains(response, "AST-102")
        self.assertEqual(response.context["total_count"], 2)
        self.assertEqual(response.context["active_count"], 1)
        self.assertEqual(response.context["maintenance_count"], 1)

    def test_asset_list_search(self):
        """Test searching assets by keyword."""
        self.client.force_login(self.admin)
        response = self.client.get(reverse("assets:asset_list"), {"q": "Microscope"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Microscope")
        self.assertNotContains(response, "Projector")

    def test_asset_list_filter_by_status(self):
        """Test filtering assets by status."""
        self.client.force_login(self.admin)
        response = self.client.get(
            reverse("assets:asset_list"), {"status": "UNDER_MAINTENANCE"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "AST-102")
        self.assertNotContains(response, "AST-101")

    def test_asset_detail_view(self):
        """Test asset detail page displays asset specifications."""
        self.client.force_login(self.admin)
        response = self.client.get(
            reverse("assets:asset_detail", kwargs={"pk": self.asset1.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "assets/asset_detail.html")
        self.assertContains(response, "Projector Epson EB-X06")
        self.assertContains(response, "Seminar Hall")

    def test_asset_create_view(self):
        """Test adding a new asset via the create form."""
        self.client.force_login(self.admin)
        data = {
            "asset_code": "AST-201",
            "name": "Sony Wireless Microphone",
            "category": "Audio / Visual",
            "building": "Main Auditorium",
            "room": "Stage Control",
            "status": "ACTIVE",
            "description": "Dual channel wireless mic set",
        }
        response = self.client.post(reverse("assets:asset_create"), data)
        self.assertRedirects(response, reverse("assets:asset_list"))
        self.assertTrue(Asset.objects.filter(asset_code="AST-201").exists())

    def test_asset_update_view(self):
        """Test updating an existing asset."""
        self.client.force_login(self.admin)
        data = {
            "asset_code": "AST-101",
            "name": "Projector Epson EB-X06 (Updated)",
            "category": "Audio / Visual",
            "building": "Seminar Hall",
            "room": "Hall C",
            "status": "IN_STOCK",
            "description": "Moved to Hall C storage",
        }
        response = self.client.post(
            reverse("assets:asset_update", kwargs={"pk": self.asset1.pk}), data
        )
        self.assertRedirects(response, reverse("assets:asset_list"))
        self.asset1.refresh_from_db()
        self.assertEqual(self.asset1.name, "Projector Epson EB-X06 (Updated)")
        self.assertEqual(self.asset1.status, "IN_STOCK")

    def test_asset_retire_view(self):
        """Test marking an asset as retired."""
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("assets:asset_retire", kwargs={"pk": self.asset1.pk})
        )
        self.assertRedirects(response, reverse("assets:asset_detail", kwargs={"pk": self.asset1.pk}))
        self.asset1.refresh_from_db()
        self.assertEqual(self.asset1.status, "RETIRED")

    def test_asset_delete_view(self):
        """Test deleting an asset."""
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("assets:asset_delete", kwargs={"pk": self.asset2.pk})
        )
        self.assertRedirects(response, reverse("assets:asset_list"))
        self.assertFalse(Asset.objects.filter(pk=self.asset2.pk).exists())


from django.core.management import call_command
from smart_campus.inventory.models import InventoryCategory, InventoryItem, StockTransaction


class SeedCampusDataCommandTest(TestCase):
    """
    Unit tests for seed_campus_data management command idempotency, data accuracy, and relationships.
    """

    def test_seed_campus_data_execution_and_idempotency(self):
        """Test running seed_campus_data creates records and running it twice creates zero duplicates."""
        # 1. First execution
        call_command("seed_campus_data")

        asset_count_first = Asset.objects.count()
        cat_count_first = InventoryCategory.objects.count()
        item_count_first = InventoryItem.objects.count()
        tx_count_first = StockTransaction.objects.count()

        self.assertGreaterEqual(asset_count_first, 21)
        self.assertGreaterEqual(cat_count_first, 10)
        self.assertGreaterEqual(item_count_first, 21)
        self.assertGreater(tx_count_first, 0)

        # Verify asset statuses present
        statuses = set(Asset.objects.values_list("status", flat=True))
        self.assertIn("ACTIVE", statuses)
        self.assertIn("IN_STOCK", statuses)
        self.assertIn("UNDER_MAINTENANCE", statuses)
        self.assertIn("DAMAGED", statuses)
        self.assertIn("RETIRED", statuses)

        # Verify stock statuses
        low_stock_items = [i for i in InventoryItem.objects.all() if i.stock_status == "Low Stock"]
        out_of_stock_items = [i for i in InventoryItem.objects.all() if i.stock_status == "Out of Stock"]
        in_stock_items = [i for i in InventoryItem.objects.all() if i.stock_status == "In Stock"]

        self.assertGreater(len(low_stock_items), 0)
        self.assertGreater(len(out_of_stock_items), 0)
        self.assertGreater(len(in_stock_items), 0)

        # 2. Second execution (Idempotency check)
        call_command("seed_campus_data")

        self.assertEqual(Asset.objects.count(), asset_count_first)
        self.assertEqual(InventoryCategory.objects.count(), cat_count_first)
        self.assertEqual(InventoryItem.objects.count(), item_count_first)
        self.assertEqual(StockTransaction.objects.count(), tx_count_first)


from smart_campus.assets.models import Location


class LocationManagementTest(TestCase):
    """
    Unit tests for Location model hierarchy, CRUD views, permissions, and deletion safeguards.
    """

    def setUp(self):
        self.admin = User.objects.create_user(
            username="loc_admin",
            email="locadmin@campus.edu",
            password="password123",
            role=User.Role.ADMIN,
            is_staff=True,
            is_superuser=True,
        )
        self.staff = User.objects.create_user(
            username="loc_staff",
            email="locstaff@campus.edu",
            password="password123",
            role=User.Role.MAINTENANCE,
        )
        self.student = User.objects.create_user(
            username="loc_student",
            email="locstudent@campus.edu",
            password="password123",
            role=User.Role.STUDENT,
        )

        self.block = Location.objects.create(
            name="Science Block",
            location_type="BLOCK",
            is_active=True,
        )
        self.lab = Location.objects.create(
            name="Physics Lab 1",
            location_type="LABORATORY",
            parent=self.block,
            is_active=True,
        )

    def test_location_full_path_hierarchy(self):
        """Test that get_full_path produces formatted string 'Science Block → Physics Lab 1'."""
        self.assertEqual(self.block.get_full_path(), "Science Block")
        self.assertEqual(self.lab.get_full_path(), "Science Block → Physics Lab 1")
        self.assertEqual(str(self.lab), "Science Block → Physics Lab 1")

    def test_admin_can_create_and_edit_location(self):
        """Test Admin adding a new location and editing it."""
        self.client.force_login(self.admin)
        
        # Create
        res = self.client.post(
            reverse("assets:location_create"),
            data={
                "name": "Robotics Lab",
                "location_type": "LABORATORY",
                "parent": self.block.pk,
                "description": "Advanced automation lab",
                "is_active": True,
            },
        )
        self.assertRedirects(res, reverse("assets:campus_locations"))
        self.assertTrue(Location.objects.filter(name="Robotics Lab").exists())

        # Update
        new_lab = Location.objects.get(name="Robotics Lab")
        update_res = self.client.post(
            reverse("assets:location_update", kwargs={"pk": new_lab.pk}),
            data={
                "name": "Robotics & AI Lab",
                "location_type": "LABORATORY",
                "parent": self.block.pk,
                "description": "Updated description",
                "is_active": True,
            },
        )
        self.assertRedirects(update_res, reverse("assets:campus_locations"))
        new_lab.refresh_from_db()
        self.assertEqual(new_lab.name, "Robotics & AI Lab")

    def test_admin_can_toggle_active_status(self):
        """Test Admin toggling location active state."""
        self.client.force_login(self.admin)
        res = self.client.post(reverse("assets:location_toggle_active", kwargs={"pk": self.lab.pk}))
        self.assertRedirects(res, reverse("assets:campus_locations"))
        self.lab.refresh_from_db()
        self.assertFalse(self.lab.is_active)

    def test_deletion_safeguard_for_linked_assets(self):
        """Test preventing deletion of location with linked assets."""
        self.client.force_login(self.admin)
        Asset.objects.create(
            name="Laser Interferometer",
            location=self.lab,
            status="ACTIVE",
        )
        res = self.client.post(reverse("assets:location_delete", kwargs={"pk": self.lab.pk}), follow=True)
        self.assertRedirects(res, reverse("assets:campus_locations"))
        self.assertTrue(Location.objects.filter(pk=self.lab.pk).exists())
        self.assertContains(res, "Cannot delete location")

    def test_role_permissions_for_locations(self):
        """Test permissions: Staff can view; Student cannot access; Student cannot create."""
        # Maintenance staff can view directory & detail
        self.client.force_login(self.staff)
        res = self.client.get(reverse("assets:campus_locations"))
        self.assertEqual(res.status_code, 200)

        detail_res = self.client.get(reverse("assets:location_detail", kwargs={"pk": self.lab.pk}))
        self.assertEqual(detail_res.status_code, 200)

        # Maintenance staff cannot create
        create_res = self.client.get(reverse("assets:location_create"))
        self.assertEqual(create_res.status_code, 403)

        # Student cannot access directory
        self.client.force_login(self.student)
        stud_res = self.client.get(reverse("assets:campus_locations"))
        self.assertEqual(stud_res.status_code, 403)



