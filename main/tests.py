from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from main.models import Add_vehicle, Profile, Society, Qr_scan_history


class SocietyAndPrivacyTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="resident@example.com",
            email="resident@example.com",
            password="strongpass123",
            first_name="Rahul",
        )
        self.profile = Profile.objects.create(user=self.user, mobile="9876543210")
        self.admin = get_user_model().objects.create_user(
            username="admin@example.com",
            email="admin@example.com",
            password="strongpass123",
            first_name="Admin",
        )
        self.admin_profile = Profile.objects.create(user=self.admin, mobile="9123456780")
        self.society = Society.objects.create(
            name="Green Park",
            city="Pune",
            state="Maharashtra",
            admin=self.admin,
        )
        self.vehicle = Add_vehicle.objects.create(
            user=self.user,
            vehicle_number="MH12AB1234",
            vehicle_type="Car",
            brand="Toyota",
            model="Corolla",
            year_of_manufacture=2022,
            vehicle_color_name="Silver",
            vehicle_color_code="#c0c0c0",
        )

    def test_authenticated_user_can_join_society_via_invite_link(self):
        self.client.login(username="resident@example.com", password="strongpass123")
        response = self.client.get(reverse("join_society", args=[self.society.invite_code]))

        self.profile.refresh_from_db()
        self.assertEqual(self.profile.society, self.society)
        self.assertEqual(response.status_code, 302)

    def test_vehicle_detail_hides_private_owner_fields_when_disabled(self):
        self.profile.show_name = False
        self.profile.show_mobile = False
        self.profile.show_city = False
        self.profile.show_email = False
        self.profile.save()

        response = self.client.get(reverse("vehicle_details", args=[self.vehicle.qr_id]))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Rahul")
        self.assertNotContains(response, "9876543210")


class SocietyFlowTests(TestCase):
    def setUp(self):
        self.admin_user = get_user_model().objects.create_user(
            username="societyowner@example.com",
            email="societyowner@example.com",
            password="strongpass123",
            first_name="Owner Admin",
        )
        self.admin_profile = Profile.objects.create(
            user=self.admin_user,
            mobile="9999999999",
            account_type="society"
        )
        self.resident_user = get_user_model().objects.create_user(
            username="resident_test@example.com",
            email="resident_test@example.com",
            password="strongpass123",
            first_name="Resident Test",
        )
        self.resident_profile = Profile.objects.create(
            user=self.resident_user,
            mobile="8888888888",
            account_type="individual"
        )

    def test_society_creation_flow(self):
        self.client.login(username="societyowner@example.com", password="strongpass123")
        
        # Access create society page
        response = self.client.get(reverse("create_society"))
        self.assertEqual(response.status_code, 200)

        # Create society
        post_data = {
            "name": "Hollycity Phase 1",
            "city": "Austin",
            "state": "Texas",
        }
        response = self.client.post(reverse("create_society"), data=post_data)
        
        self.assertEqual(response.status_code, 302)
        
        # Verify society exists and values are set correctly
        society = Society.objects.filter(admin=self.admin_user).first()
        self.assertIsNotNone(society)
        self.assertEqual(society.name, "Hollycity Phase 1")
        self.assertEqual(society.city, "Austin")
        self.assertEqual(society.state, "Texas")
        self.assertIsNotNone(society.invite_code)
        
        # Verify profile is associated
        self.admin_profile.refresh_from_db()
        self.assertEqual(self.admin_profile.society, society)

    def test_prevent_duplicate_societies(self):
        self.client.login(username="societyowner@example.com", password="strongpass123")
        # Create first society
        society = Society.objects.create(
            name="Hollycity Phase 1",
            city="Austin",
            state="Texas",
            admin=self.admin_user
        )
        self.admin_profile.society = society
        self.admin_profile.save()

        # Try to create second society
        post_data = {
            "name": "Hollycity Phase 2",
            "city": "Austin",
            "state": "Texas",
        }
        response = self.client.post(reverse("create_society"), data=post_data)
        self.assertEqual(response.status_code, 302)
        # Should redirect to society admin dashboard
        self.assertRedirects(response, reverse("society_admin_dashboard"))
        # Verify no second society was created
        self.assertEqual(Society.objects.filter(admin=self.admin_user).count(), 1)

    def test_resident_cannot_access_create_society(self):
        self.client.login(username="resident_test@example.com", password="strongpass123")
        response = self.client.get(reverse("create_society"))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("dashboard"))

    def test_invite_redirection_and_joining_flow(self):
        # Create a society managed by admin
        society = Society.objects.create(
            name="Hollycity Phase 1",
            city="Austin",
            state="Texas",
            admin=self.admin_user
        )
        
        # 1. Access invite link unauthenticated (incognito simulator)
        response = self.client.get(reverse("join_society", args=[society.invite_code]))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("register"))
        
        # Verify invite code is saved in session
        self.assertEqual(self.client.session.get("pending_invite_code"), society.invite_code)

        # 2. Register new resident
        register_data = {
            "full_name": "New Resident",
            "mobile": "7777777777",
            "email": "newresident@example.com",
            "account_type": "individual",
            "password": "newstrongpassword123",
            "confirm_password": "newstrongpassword123",
        }
        response = self.client.post(reverse("register"), data=register_data)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("login"))

        # Verify new user profile is linked to the society
        new_user = get_user_model().objects.get(email="newresident@example.com")
        new_profile = Profile.objects.get(user=new_user)
        self.assertEqual(new_profile.society, society)
        
        # 3. Log in and verify society admin dashboard shows correct counts
        self.client.login(username="societyowner@example.com", password="strongpass123")
        response = self.client.get(reverse("society_admin_dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Hollycity Phase 1")
        # Total residents should be 2 (admin + new resident)
        self.assertEqual(response.context["total_residents"], 2)

