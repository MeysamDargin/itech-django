from django.test import TestCase, Client
from django.contrib.auth.models import User
from following.models import Follow
from django.urls import reverse

class ToggleFollowTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user1 = User.objects.create_user(username='user1', password='testpass123')
        self.user2 = User.objects.create_user(username='user2', password='testpass123')
        self.toggle_url = reverse('toggle-follow')  # باید تو urls.py اسمش رو گذاشته باشی

    def test_follow_user(self):
        self.client.login(username='user1', password='testpass123')
        response = self.client.post(self.toggle_url, {'user_id': self.user2.id})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Follow.objects.filter(follower=self.user1, followed=self.user2).exists())
        self.assertEqual(response.json()['action'], 'follow')

    def test_unfollow_user(self):
        Follow.objects.create(follower=self.user1, followed=self.user2)
        self.client.login(username='user1', password='testpass123')
        response = self.client.post(self.toggle_url, {'user_id': self.user2.id})
