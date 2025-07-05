# backend/app/core/security.py

from datetime import datetime, timedelta
from typing import Any, Union

from jose import jwt
from passlib.context import CryptContext

# 使用Bcrypt算法进行密码哈希
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = "HS256"

def create_access_token(
    subject: Union[str, Any], expires_delta: timedelta = None, secret_key: str = None
) -> str:
    """
    创建JWT access token
    :param subject: token中要编码的数据 (通常是用户ID或用户名)
    :param expires_delta: token的有效期
    :param secret_key: 用于签发token的密钥
    :return: JWT token字符串
    """
    from app.core.config import ACCESS_TOKEN_EXPIRE_MINUTES

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode = {"exp": expire, "sub": str(subject)}
    
    from app.core.config import SECRET_KEY
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证明文密码和哈希后的密码是否匹配"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """生成密码的哈希值"""
    return pwd_context.hash(password)