from rest_framework.test import APITestCase
from django.urls import reverse
from django.contrib.auth.models import User
from otp.models import OTP
from unittest.mock import patch

class OTPViewsTest(APITestCase):

    def setUp(self):
        # ایجاد یک یوزر نمونه
        self.user_email = "testuser@example.com"
        self.user = User.objects.create_user(username="testuser", email=self.user_email, password="password123")
        self.send_otp_url = reverse('send-otp')  # مطمئن شو url name در urls.py همین است
        self.verify_otp_url = reverse('verify-otp')

    @patch('otp.utils.utils.send_otp_to_user')
    def test_send_otp_success(self, mock_send_otp):
        mock_send_otp.return_value = True

        # تست وقتی ایمیل جدید است
        response = self.client.post(self.send_otp_url, {'email': 'newuser@example.com'}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertIn('message', response.data)

    def test_send_otp_existing_user(self):
        # وقتی ایمیل قبلا ثبت شده
        response = self.client.post(self.send_otp_url, {'email': self.user_email}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.data)

    def test_verify_otp_success(self):
        # ایجاد OTP معتبر
        otp_instance = OTP.objects.create(email='verify@example.com', otp_code='123456')
        
        response = self.client.post(self.verify_otp_url, {'email': 'verify@example.com', 'otp': '123456'}, format='json')
        self.assertEqual(response.status_code, 200)
        otp_instance.refresh_from_db()
        self.assertTrue(otp_instance.is_used)

    def test_verify_otp_invalid(self):
        response = self.client.post(self.verify_otp_url, {'email': 'wrong@example.com', 'otp': '000000'}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.data)

    def test_verify_otp_missing_fields(self):
        response = self.client.post(self.verify_otp_url, {'email': 'missing@example.com'}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.data)
