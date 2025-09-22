from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

# Create your models here.
class Follow(models.Model):
    follower = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name="following", 
        help_text="کاربر فالوکننده"
    )
    followed = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name="followers", 
        help_text="کاربر فالوشده"
    )
    created_at = models.DateTimeField(default=timezone.now, help_text="زمان فالو")

    class Meta:
        unique_together = ('follower', 'followed')  # جلوگیری از فالوهای تکراری
        verbose_name = "رابطه فالو"
        verbose_name_plural = "روابط فالو"

    def save(self, *args, **kwargs):
        # جلوگیری از فالو کردن خود
        if self.follower == self.followed:
            raise ValueError("کاربر نمی‌تواند خودش را فالو کند")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.follower.username} follows {self.followed.username}"