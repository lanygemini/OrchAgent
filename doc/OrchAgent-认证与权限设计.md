# OrchAgent — 用户认证与权限设计

---

## 一、认证架构总览

```
┌──────────────────────────────────────────────────────────┐
│                      前端 (React)                         │
│   登录/注册 -> 获取 Token -> 存 HttpOnly Cookie / localStorage │
├──────────────────────────────────────────────────────────┤
│                     Nginx 反向代理                         │
├──────────────────────────────────────────────────────────┤
│                    FastAPI 中间件                          │
│  ┌────────────────────────────────────────────────────┐  │
│  │  AuthMiddleware                                    │  │
│  │  RBACMiddleware                                    │  │
│  │  ResourceOwnerMiddleware                            │  │
│  └────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
```

---

## 二、JWT 认证设计

```python
class TokenPayload(BaseModel):
    sub: str
    username: str
    roles: List[str]
    permissions: List[str]
    token_type: str
    iat: int
    exp: int
    jti: str
    session_id: str

class AuthConfig(BaseModel):
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    access_token_expire: int = 900
    refresh_token_expire: int = 604800
    issuer: str = "orchagent"
    audience: str = "orchagent-api"
```

### Token 签发与验证

```python
class JWTService:
    def __init__(self, config: AuthConfig):
        self.config = config

    def create_access_token(self, user: User) -> str:
        payload = {
            "sub": str(user.id),
            "username": user.username,
            "roles": [r.name for r in user.roles],
            "permissions": self._get_all_permissions(user),
            "token_type": "access",
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(seconds=self.config.access_token_expire),
            "jti": str(uuid4()),
            "session_id": user.current_session_id,
        }
        return jwt.encode(payload, self.config.jwt_secret, algorithm=self.config.jwt_algorithm)

    def decode_token(self, token: str) -> TokenPayload:
        try:
            payload = jwt.decode(token, self.config.jwt_secret,
                algorithms=[self.config.jwt_algorithm])
            return TokenPayload(**payload)
        except jwt.ExpiredSignatureError:
            raise UnauthorizedError("Token 已过期")
        except jwt.InvalidTokenError:
            raise UnauthorizedError("Token 无效")
```

---

## 三、RBAC 权限模型

### 角色定义

```python
class Role(str, Enum):
    ADMIN = "admin"
    EDITOR = "editor"
    VIEWER = "viewer"

ROLE_PERMISSIONS = {
    Role.ADMIN: [
        "agent:*", "tool:*", "mcp:*", "workflow:*",
        "execution:*", "memory:*", "user:*", "system:*", "stats:*",
    ],
    Role.EDITOR: [
        "agent:create", "agent:read", "agent:update",
        "tool:create", "tool:read", "tool:update",
        "mcp:create", "mcp:read", "mcp:update",
        "workflow:create", "workflow:read", "workflow:update",
        "execution:create", "execution:read",
        "memory:read", "memory:extract",
        "stats:read",
    ],
    Role.VIEWER: [
        "agent:read", "tool:read", "mcp:read",
        "workflow:read", "execution:read", "stats:read",
    ],
}
```

### 权限检查装饰器

```python
def require_permission(permission: str):
    async def dependency(current_user: User = Depends(get_current_user)):
        resource, action = permission.split(":")
        has_perm = permission in current_user.effective_permissions
        if not has_perm:
            has_perm = f"{resource}:*" in current_user.effective_permissions
        if not has_perm:
            raise ForbiddenError(f"需要权限: {permission}")
        return current_user
    return Depends(dependency)
```

---

## 四、资源级隔离

```python
class ResourceOwnerChecker:
    async def check_agent_ownership(self, agent_id: str, user: User) -> Agent:
        agent = await self.db.get(Agent, agent_id)
        if not agent:
            raise NotFoundError("Agent 不存在")
        if str(agent.owner_id) != str(user.id):
            if "agent:*" not in user.effective_permissions:
                raise NotFoundError("Agent 不存在")
        return agent
```

---

## 五、API Key 管理

```python
class APIKeyService:
    def __init__(self, db: AsyncSession, encryption_key: bytes):
        self.cipher = Fernet(encryption_key)

    async def store_api_key(self, user_id: str, provider: str, api_key: str):
        encrypted = self.cipher.encrypt(api_key.encode()).decode()
        key_record = UserAPIKey(
            user_id=user_id, provider=provider,
            encrypted_key=encrypted,
            key_prefix=api_key[:7] + "...",
            is_active=True,
        )
        self.db.add(key_record)
        await self.db.commit()

    async def get_decrypted_key(self, user_id: str, provider: str) -> str:
        key_record = await self.db.execute(
            select(UserAPIKey).where(
                UserAPIKey.user_id == user_id,
                UserAPIKey.provider == provider,
                UserAPIKey.is_active == True,
            )
        )
        key_record = key_record.scalar_one_or_none()
        return self.cipher.decrypt(key_record.encrypted_key.encode()).decode()
```

---

## 六、Token 黑名单与撤销

```python
class TokenBlacklist:
    def __init__(self, redis: Redis):
        self.redis = redis

    async def revoke_token(self, jti: str, ttl: int):
        await self.redis.setex(f"revoked:{jti}", ttl, "1")

    async def is_revoked(self, payload: TokenPayload) -> bool:
        result = await self.redis.exists(f"revoked:{payload.jti}")
        return bool(result)
```

---

## 七、速率限制

```python
RATE_LIMIT_CONFIGS = {
    "global:per_ip": (100, 60),
    "global:per_user": (200, 60),
    "auth:login": (5, 60),
    "auth:login:per_ip": (10, 300),
    "agent:create": (20, 3600),
    "workflow:execute": (30, 60),
    "llm:per_user": (60, 60),
    "tool:per_user": (100, 60),
}
```

---

## 八、安全加固

| 措施 | 说明 |
|------|------|
| JWT + Refresh Token Rotation | 短有效期 access_token + 每次刷新换新 refresh_token |
| bcrypt 密码哈希 | 工作量因子 12 |
| API Key AES 加密存储 | 使用 Fernet 对称加密 |
| HTTPS 强制 | Cookie secure 标志 |
| HttpOnly Cookie | 防 XSS 窃取 Token |
| CORS 白名单 | 仅允许已知前端域名 |
| 登录限流 | 用户名 + IP 双维度 |
| 账户锁定 | 5次失败锁定 15 分钟 |
