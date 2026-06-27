"""认证 API：注册、登录、刷新令牌"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, Field
from uuid import uuid4

from app.dependencies import get_db
from app.models.user import User, Role
from app.core.security.jwt_service import jwt_service

router = APIRouter(prefix="/api/v1/auth", tags=["认证"])


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    email: str = Field(..., max_length=128)
    password: str = Field(..., min_length=6, max_length=128)
    display_name: str = ""


class LoginRequest(BaseModel):
    username: str
    password: str


class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user_id: str
    username: str


@router.post("/register", response_model=AuthResponse, status_code=201)
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """注册新用户（自动创建 access_token + refresh_token）"""
    existing = await db.execute(select(User).where((User.username == data.username) | (User.email == data.email)))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="用户名或邮箱已存在")

    user = User(
        username=data.username,
        email=data.email,
        hashed_password=jwt_service.hash_password(data.password),
        display_name=data.display_name or data.username,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)

    access_token = jwt_service.create_access_token(
        user_id=user.id,
        username=user.username,
        roles=[],
        permissions=["read:agent", "write:agent", "delete:agent"],
        session_id=str(uuid4()),
    )
    refresh_token = jwt_service.create_refresh_token(user.id, str(uuid4()))

    return AuthResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user_id=user.id,
        username=user.username,
    )


@router.post("/login", response_model=AuthResponse)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    """用户登录（用户名 + 密码）"""
    result = await db.execute(select(User).where(User.username == data.username))
    user = result.scalar_one_or_none()

    if not user or not jwt_service.verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    access_token = jwt_service.create_access_token(
        user_id=user.id,
        username=user.username,
        roles=[r.name for r in user.roles],
        permissions=[],
        session_id=str(uuid4()),
    )
    refresh_token = jwt_service.create_refresh_token(user.id, str(uuid4()))

    return AuthResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user_id=user.id,
        username=user.username,
    )


class RefreshRequest(BaseModel):
    refresh_token: str


@router.post("/refresh", response_model=AuthResponse)
async def refresh_token(data: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """使用 refresh_token 获取新的 access_token"""
    payload = jwt_service.decode_token(data.refresh_token)
    if payload is None or payload.token_type != "refresh":
        raise HTTPException(status_code=401, detail="刷新令牌无效")

    result = await db.execute(select(User).where(User.id == payload.sub))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")

    access_token = jwt_service.create_access_token(
        user_id=user.id,
        username=user.username,
        roles=[r.name for r in user.roles],
        permissions=[],
        session_id=payload.session_id,
    )
    new_refresh_token = jwt_service.create_refresh_token(user.id, payload.session_id)

    return AuthResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        user_id=user.id,
        username=user.username,
    )
