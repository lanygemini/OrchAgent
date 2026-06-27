"""FastAPI 依赖注入：数据库会话、用户认证、权限校验"""
from fastapi import Request, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db as _get_db
from app.models.user import User


async def get_db():
    """提供异步数据库会话（自动提交 / 回滚）"""
    async for session in _get_db():
        yield session


def get_current_user(request: Request):
    """从请求状态中获取当前已认证用户"""
    if not hasattr(request.state, "user"):
        raise HTTPException(status_code=401, detail="未认证，请先登录")
    return request.state.user


def require_permission(permission: str):
    """权限校验的依赖工厂，检查用户是否拥有指定权限"""
    def checker(request: Request):
        user = get_current_user(request)
        if permission not in user.permissions and "admin" not in user.roles:
            raise HTTPException(status_code=403, detail="权限不足")
        return True
    return checker
