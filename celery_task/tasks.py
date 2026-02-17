import os

from sqlalchemy import create_engine, delete
from sqlalchemy.orm import sessionmaker, Session

from config.dependencies import get_settings
from database import ActivationTokenModel
from celery_task.celery_app import celery_app
import logging

logger = logging.getLogger(__name__)

if os.getenv("ENVIRONMENT") != "testing":
    settings = get_settings()
    sync_engine = create_engine(settings.SYNC_DATABASE_URL)
    SyncSessionLocal = sessionmaker(bind=sync_engine, class_=Session)


@celery_app.task(name="delay_delete_activation_token")
def delay_delete_activation_token(token_id: int):
    with SyncSessionLocal() as db:
        result = db.execute(
            delete(ActivationTokenModel).where(ActivationTokenModel.id == token_id)
        )
        db.commit()
        if result.rowcount == 0:
            logger.info(f"Token {token_id} not found - user already activated account")
        else:
            logger.info(f"Token {token_id} successfully deleted")
