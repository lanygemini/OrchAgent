from fastapi import Request, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db as _get_db
from app.models.user import User


async def get_db():
    async for session in _get_db():
        yield session


def get_current_user(request: Request):
    if not hasattr(request.state, "user"):
        raise HTTPException(status_code=401, detail="未认证，请先登录")
    return request.state.user


def require_permission(permission: str):
    def checker(request: Request):
        user = get_current_user(request)
        if permission not in user.permissions and "admin" not in user.roles:
            raise HTTPException(status_code=403, detail="权限不足")
        return True
    return checker
