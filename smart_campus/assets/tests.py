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


class AssetViewsTest(TestCase):
    """
    Unit tests for Asset CRUD views and search/filter functionality.
    """

    def setUp(self):
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

    def test_asset_list_view(self):
        """Test asset list page loads correctly with statistics."""
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
        response = self.client.get(reverse("assets:asset_list"), {"q": "Microscope"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Microscope")
        self.assertNotContains(response, "Projector")

    def test_asset_list_filter_by_status(self):
        """Test filtering assets by status."""
        response = self.client.get(
            reverse("assets:asset_list"), {"status": "UNDER_MAINTENANCE"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "AST-102")
        self.assertNotContains(response, "AST-101")

    def test_asset_detail_view(self):
        """Test asset detail page displays asset specifications."""
        response = self.client.get(
            reverse("assets:asset_detail", kwargs={"pk": self.asset1.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "assets/asset_detail.html")
        self.assertContains(response, "Projector Epson EB-X06")
        self.assertContains(response, "Seminar Hall")

    def test_asset_create_view(self):
        """Test adding a new asset via the create form."""
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

    def test_asset_delete_view(self):
        """Test deleting an asset."""
        response = self.client.post(
            reverse("assets:asset_delete", kwargs={"pk": self.asset2.pk})
        )
        self.assertRedirects(response, reverse("assets:asset_list"))
        self.assertFalse(Asset.objects.filter(pk=self.asset2.pk).exists())
