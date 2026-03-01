"""Celery application for Delivery Assistant."""
from celery import Celery

from src.config import get_settings

settings = get_settings()

app = Celery(
    "delivery_assistant",
    broker=settings.celery_broker_url,
    backend=settings.redis_url,
    include=["src.infra.queue.tasks"],
)
app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
)
