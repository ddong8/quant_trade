# backend/app/api/v1/endpoints/login.py

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.api import deps
from app.core import security
from app.schemas.token import Token

router = APIRouter()

@router.post("/login/access-token", response_model=Token)
def login_for_access_token(
    db: Session = Depends(deps.get_db), form_data: OAuth2PasswordRequestForm = Depends()
):
    """
    OAuth2兼容的token登录，获取access token。
    为了演示，我们使用一个硬编码的用户。
    """
    # ---- 硬编码的演示用户 ----
    DEMO_USER_USERNAME = "admin"
    DEMO_USER_PASSWORD = "password" # 明文密码
    
    # 在真实应用中，你会从数据库查询用户
    # user = crud.user.authenticate(db, email=form_data.username, password=form_data.password)
    
    # 简化验证逻辑
    if form_data.username != DEMO_USER_USERNAME or not security.verify_password(form_data.password, security.get_password_hash(DEMO_USER_PASSWORD)):
        raise HTTPException(
            status_code=400, detail="Incorrect username or password"
        )
    
    access_token = security.create_access_token(
        subject=form_data.username
    )
    return {"access_token": access_token, "token_type": "bearer"}