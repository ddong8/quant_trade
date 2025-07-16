# backend/app/core/config.py
import os
from dotenv import load_dotenv
from pathlib import Path

# 加载 .env 文件中的环境变量
load_dotenv()

# JWT 设置
# 警告: 在生产环境中，绝不要硬编码密钥！
# 应该从环境变量或安全的配置服务中读取。
SECRET_KEY = os.getenv("SECRET_KEY", "a-very-secret-key-for-jwt-that-should-be-long-and-random")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 # Token有效期：24小时

# 数据库设置
# 优先从环境变量读取DATABASE_URL，否则使用本地的SQLite数据库
DATABASE_URL = os.getenv("DATABASE_URL")


# Tushare API Token
# 警告: 请替换成你自己的Tushare Token
TUSHARE_TOKEN = os.getenv("TUSHARE_TOKEN", "YOUR_TUSHARE_TOKEN")

# TqSdk Credentials <-- 新增
TQ_USER = os.getenv("TQ_USER")
TQ_PASSWORD = os.getenv("TQ_PASSWORD")

# Celery and Redis Settings
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
