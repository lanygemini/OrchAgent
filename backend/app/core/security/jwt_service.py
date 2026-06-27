from datetime import datetime, timedelta, timezone
from typing import List, Optional
from uuid import uuid4

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class TokenPayload:
    def __init__(
        self,
        sub: str,
        username: str,
        roles: List[str],
        permissions: List[str],
        token_type: str,
        iat: int,
        exp: int,
        jti: str,
        session_id: str,
    ):
        self.sub = sub
        self.username = username
        self.roles = roles
        self.permissions = permissions
        self.token_type = token_type
        self.iat = iat
        self.exp = exp
        self.jti = jti
        self.session_id = session_id


class JWTService:
    def __init__(self):
        self.secret = settings.jwt_secret
        self.algorithm = settings.jwt_algorithm
        self.access_expire = settings.access_token_expire_minutes * 60
        self.refresh_expire = settings.refresh_token_expire_days * 86400

    def create_access_token(self, user_id: str, username: str, roles: List[str], permissions: List[str], session_id: str) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "sub": user_id,
            "username": username,
            "roles": roles,
            "permissions": permissions,
            "token_type": "access",
            "iat": int(now.timestamp()),
            "exp": int(now.timestamp()) + self.access_expire,
            "jti": str(uuid4()),
            "session_id": session_id,
        }
        return jwt.encode(payload, self.secret, algorithm=self.algorithm)

    def create_refresh_token(self, user_id: str, session_id: str) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "sub": user_id,
            "token_type": "refresh",
            "iat": int(now.timestamp()),
            "exp": int(now.timestamp()) + self.refresh_expire,
            "jti": str(uuid4()),
            "session_id": session_id,
        }
        return jwt.encode(payload, self.secret, algorithm=self.algorithm)

    def decode_token(self, token: str) -> Optional[TokenPayload]:
        try:
            payload = jwt.decode(token, self.secret, algorithms=[self.algorithm])
            return TokenPayload(**payload)
        except JWTError:
            return None

    @staticmethod
    def hash_password(password: str) -> str:
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)


jwt_service = JWTService()
