import logging
from celery import shared_task
from ai.views.ai import generate_user_embedding
from django.contrib.auth import get_user_model

# تعریف logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

@shared_task
def run_user_embedding():
    logger.info("Starting run_user_embedding task")
    User = get_user_model()
    for user in User.objects.all():
        try:
            result = generate_user_embedding(user.id)
            if 'error' in result:
                logger.warning(f"Failed for user {user.id}: {result['error']}")
            else:
                logger.info(f"Success for user {user.id}: {result['message']}")
        except Exception as e:
            logger.error(f"Unexpected error for user {user.id}: {str(e)}")
    logger.info("Finished run_user_embedding task")
