# backend/app/celery_app.py
from celery import Celery
from app.core.config import CELERY_BROKER_URL, CELERY_RESULT_BACKEND

# 创建 Celery 实例
celery_app = Celery(
    "quant_trade_worker",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=["app.tasks"]  # 指定包含任务的模块
)

# 可选的Celery配置
celery_app.conf.update(
    task_track_started=True,
)
