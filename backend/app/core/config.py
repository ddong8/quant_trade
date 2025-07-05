# backend/app/core/config.py

# 警告: 在生产环境中，绝不要硬编码密钥！
# 应该从环境变量或安全的配置服务中读取。
SECRET_KEY = "a-very-secret-key-for-jwt-that-should-be-long-and-random"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 # Token有效期：24小时