from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import User

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    first_name = models.CharField(
        _('first name'),
        max_length=30,
        blank=True,
    )
    last_name = models.CharField(
        _('last name'),
        max_length=30,
        blank=True,
    )
    job_title = models.CharField(
        _('job title'),
        max_length=30,
        blank=True,
    )
    # فیلدهای اضافی که بخوای
    bio = models.TextField(
        _('bio'),
        blank=True,
        null=True,
    )
    phone_number = models.CharField(
        _('phone number'),
        max_length=15,
        blank=True,
        null=True,
    )
    country = models.CharField(
        _('country'),
        max_length=20,
        blank=True,
        null=True,
    )
    city_state = models.CharField(
        _('city/state'),
        max_length=20,
        blank=True,
        null=True,
    )
    website = models.CharField(
        _('website'),
        max_length=20,
        blank=True,
        null=True,
    )
    profile_picture = models.ImageField(
        _('profile picture'),
        upload_to='profile_pics/',  # مسیر ذخیره‌سازی
        blank=True,
        null=True,
    )
    profile_caver = models.ImageField(
        _('profile cover'),
        upload_to='profile_cover/',  # مسیر ذخیره‌سازی
        blank=True,
        null=True,
    )

    def __str__(self):
        return f"{self.user.email} - Profile"