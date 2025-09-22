from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from .models import Profile

channel_layer = get_channel_layer()

@receiver(post_save, sender=Profile)
def model_changed(sender, instance, created, **kwargs):
    action = "created" if created else "updated"
    profile_image_url = instance.profile_picture.url if instance.profile_picture else None
    profile_caver_url = instance.profile_caver.url if instance.profile_caver else None
    print(f"signallll {action}: {instance.id}")  # لاگ کردن برای بررسی
    # ارسال اطلاعات به وب‌سوکت
    async_to_sync(channel_layer.group_send)(
        "Profile_group",
        {
            "type": "send_model_update",
            "data": {
                "action": action,
                "id": instance.id,
                "user_profile": instance.user.username,
                "groups_profile": list(instance.user.groups.values_list('name', flat=True)),  # تبدیل گروه‌ها به لیست نام‌ها
                "user_id": instance.user.id,
                "first_name": instance.first_name,
                "job_title": instance.job_title,
                "bio": instance.bio,
                "phone_number": instance.phone_number,
                "country": instance.country,
                "website": instance.website,
                "city_state": instance.city_state,
                "last_name": instance.last_name,
                "profile_picture": profile_image_url,
                "profile_caver": profile_caver_url,
            },
        },
    )

@receiver(post_delete, sender=Profile)
def model_deleted(sender, instance, **kwargs):
    profile_image_url = instance.profile_picture.url if instance.profile_picture else None
    profile_caver_url = instance.profile_caver.url if instance.profile_caver else None
    print(f"Profile deleted: {instance.id}")  # لاگ کردن برای بررسی
    # ارسال اطلاعات به وب‌سوکت
    async_to_sync(channel_layer.group_send)(
        "Profile_group",
        {
            "type": "send_model_update",
            "data": {
                "action": "deleted",
                "id": instance.id,
                "user_profile": instance.user.username,
                "groups_profile": list(instance.user.groups.values_list('name', flat=True)),  # تبدیل گروه‌ها به لیست نام‌ها
                "user_id": instance.user.id,
                "first_name": instance.first_name,
                "job_title": instance.job_title,
                "bio": instance.bio,
                "phone_number": instance.phone_number,
                "country": instance.country,
                "website": instance.website,
                "city_state": instance.city_state,
                "last_name": instance.last_name,
                "profile_picture": profile_image_url,
                "profile_caver": profile_caver_url,
            },
        },
    )
