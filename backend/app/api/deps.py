# backend/app/api/deps.py

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
    """
    解码token以获取当前用户。
    这是一个简化的版本，没有从数据库查询用户。
    """
    try:
        payload = jwt.decode(
            token, config.SECRET_KEY, algorithms=[config.ALGORITHM]
        )
        token_data = TokenPayload(**payload)
    except (JWTError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )
    
    # 简化：我们不从数据库查用户，只要token有效就认为用户存在。
    # 在真实应用中，你会用 token_data.sub (用户ID) 从数据库查询用户。
    # user = crud.user.get(db, id=token_data.sub)
    # if not user:
    #     raise HTTPException(status_code=404, detail="User not found")
    # return user

    # 返回一个模拟的用户对象
    return {"username": token_data.sub}