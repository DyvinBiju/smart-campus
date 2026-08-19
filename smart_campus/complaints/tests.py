from django.test import TestCase
from django.urls import reverse
from smart_campus.complaints.models import Complaint


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
        self.complaint = Complaint.objects.create(
            title="Leaking pipe in restroom",
            description="Water leaking from sink pipe.",
            category=Complaint.Category.PLUMBING,
            location="Ground Floor Restroom",
            priority=Complaint.Priority.MEDIUM,
        )

    def test_complaint_list_view(self):
        response = self.client.get(reverse("complaints:list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "CMP-0001")
        self.assertContains(response, "Leaking pipe in restroom")

    def test_complaint_create_view_get(self):
        response = self.client.get(reverse("complaints:create"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Raise a Complaint")

    def test_complaint_create_view_post(self):
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

    def test_complaint_detail_view(self):
        url = reverse("complaints:detail", kwargs={"complaint_id": self.complaint.complaint_id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Leaking pipe in restroom")
        self.assertContains(response, "Submitted")

    def test_complaint_status_update_view(self):
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
