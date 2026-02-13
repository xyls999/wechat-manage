from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime

# 用户注册
class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=20, description="用户名，3-20字符")
    password: str = Field(..., min_length=6, max_length=20, description="密码，6-20字符")
    nickname: str = Field(..., min_length=1, max_length=10, description="昵称，1-10字符")
    
    @field_validator('username')
    @classmethod
    def validate_username(cls, v):
        if not v.isalnum():
            raise ValueError('用户名只能包含字母和数字')
        return v

# 用户登录
class UserLogin(BaseModel):
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")

# 用户响应
class UserResponse(BaseModel):
    id: str
    username: str
    nickname: str
    avatar: str
    createdAt: datetime
    token: Optional[str] = None
    
    class Config:
        from_attributes = True
        populate_by_name = True
        
    @staticmethod
    def from_user(user, token: Optional[str] = None):
        return UserResponse(
            id=user.id,
            username=user.username,
            nickname=user.nickname,
            avatar=user.avatar,
            createdAt=user.created_at,
            token=token
        )

# 用户信息（不含token）
class UserInfo(BaseModel):
    id: str
    username: str
    nickname: str
    avatar: str
    createdAt: datetime
    
    class Config:
        from_attributes = True
        populate_by_name = True
        
    @staticmethod
    def from_user(user):
        return UserInfo(
            id=user.id,
            username=user.username,
            nickname=user.nickname,
            avatar=user.avatar,
            createdAt=user.created_at
        )
