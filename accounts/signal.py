from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db import transaction
from django.contrib.auth.models import User
from services import send_user_update

@receiver(post_save, sender=User)
def user_post_save(sender, instance: User, created: bool, **kwargs) -> None:
    action = "created" if created else "updated"

    def on_commit_action():
        send_user_update(action, instance)

    transaction.on_commit(on_commit_action)


@receiver(post_delete, sender=User)
def user_post_delete(sender, instance: User, **kwargs) -> None:

    def on_commit_action():
        send_user_update("deleted", instance)

    transaction.on_commit(on_commit_action)
