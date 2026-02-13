from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime

from app.core.database import get_db
from app.core.security import (
    verify_password, 
    get_password_hash, 
    create_access_token,
    get_current_user
)
from app.models.user import User
from app.schemas.user import UserRegister, UserLogin, UserResponse, UserInfo
from app.schemas.response import ApiResponse

router = APIRouter()

@router.post("/register", response_model=ApiResponse)
async def register(user_data: UserRegister, db: AsyncSession = Depends(get_db)):
    """用户注册"""
    # 检查用户名是否已存在
    result = await db.execute(select(User).where(User.username == user_data.username))
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="用户名已存在"
        )
    
    # 创建新用户
    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        username=user_data.username,
        password=hashed_password,
        nickname=user_data.nickname,
        avatar=""
    )
    
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    # 生成JWT token
    token = create_access_token(data={"sub": new_user.id})
    
    # 构建响应
    return ApiResponse(
        code=200,
        message="注册成功",
        data={
            "id": new_user.id,
            "username": new_user.username,
            "nickname": new_user.nickname,
            "avatar": new_user.avatar,
            "createdAt": new_user.created_at.isoformat(),
            "token": token
        }
    )

@router.post("/login", response_model=ApiResponse)
async def login(user_data: UserLogin, db: AsyncSession = Depends(get_db)):
    """用户登录"""
    # 查找用户
    result = await db.execute(select(User).where(User.username == user_data.username))
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(user_data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用"
        )

    user.last_login_at = datetime.utcnow()
    await db.commit()
    await db.refresh(user)
    
    # 生成JWT token
    token = create_access_token(data={"sub": user.id})
    
    # 构建响应
    return ApiResponse(
        code=200,
        message="登录成功",
        data={
            "id": user.id,
            "username": user.username,
            "nickname": user.nickname,
            "avatar": user.avatar,
            "createdAt": user.created_at.isoformat(),
            "token": token
        }
    )

@router.get("/profile", response_model=ApiResponse)
async def get_profile(current_user: User = Depends(get_current_user)):
    """获取用户信息"""
    return ApiResponse(
        code=200,
        data={
            "id": current_user.id,
            "username": current_user.username,
            "nickname": current_user.nickname,
            "avatar": current_user.avatar,
            "createdAt": current_user.created_at.isoformat()
        }
    )

@router.post("/logout", response_model=ApiResponse)
async def logout(current_user: User = Depends(get_current_user)):
    """退出登录"""
    return ApiResponse(
        code=200,
        message="退出成功"
    )
