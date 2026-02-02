from celery import Celery
import os

celery_app = Celery(
    "worker",
    broker=os.getenv("CELERY_BROKER_URL", "redis://redis_theater:6379/0"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://redis_theater:6379/0")
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Europe/Kiev",
    enable_utc=True,
    task_track_started=True,
    result_expires=86400,
    include=["celery_task.tasks"]
)
