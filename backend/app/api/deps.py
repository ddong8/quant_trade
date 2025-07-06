# backend/app/api/deps.py
import asyncio
from typing import Generator
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from pydantic import ValidationError

from app.db.session import SessionLocal
from app.core import security, config
from app.schemas.token import TokenPayload

# 这个URL是FastAPI在Swagger UI中显示"Authorize"按钮时使用的，
# 它指向获取token的端点。
reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"/api/v1/login/access-token"
)

def get_db() -> Generator:
    """获取数据库会话的依赖"""
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()

def get_current_user(
    db: Session = Depends(get_db), token: str = Depends(reusable_oauth2)
):
    try:
        # 确保这里解码时，使用的也是从 config 导入的 KEY 和 ALGORITHM
        payload = jwt.decode(
            token, config.SECRET_KEY, algorithms=[config.ALGORITHM]
        )
        # 检查 subject 是否存在
        if payload.get("sub") is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Could not validate credentials (subject missing)",
            )
        token_data = TokenPayload(**payload)
    except JWTError as e: # 捕获具体的JWTError可以提供更多信息
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Could not validate credentials ({str(e)})",
        )
    except ValidationError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials (payload validation failed)",
        )
    
    # 简化版：直接返回解码后的用户信息
    return {"username": token_data.sub}


