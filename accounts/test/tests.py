from django.urls import reverse
from rest_framework.test import APITestCase
from django.contrib.auth.models import User

class AuthTests(APITestCase):

    def setUp(self):
        self.username = "testuser"
        self.password = "testpassword123"
        self.user = User.objects.create_user(username=self.username, password=self.password)
        self.login_url = reverse('api-login')

    def test_login_success(self):
        data = {
            "username": self.username,
            "password": self.password,
        }
        response = self.client.post(self.login_url, data)
        self.assertEqual(response.status_code, 200)
        self.assertIn('sessionid', response.data)
        self.assertEqual(response.data['message'], 'Logged in')
        self.assertIn('newUser', response.data)

    def test_login_failure(self):
        data = {
            "username": self.username,
            "password": "wrongpassword",
        }
        response = self.client.post(self.login_url, data)
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.data)
        
