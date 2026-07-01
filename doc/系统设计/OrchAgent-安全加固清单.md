# OrchAgent — 安全加固清单

---

## 一、安全全景图

```
┌──────────────────────────────────────────────────────────────┐
│                        安全防护层次                             │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  传输层安全 (TLS/SSL, CORS)                             │  │
│  ├────────────────────────────────────────────────────────┤  │
│  │  认证与授权 (JWT, RBAC, API Key)                        │  │
│  ├────────────────────────────────────────────────────────┤  │
│  │  输入安全 (Prompt注入, SQL注入, XSS)                     │  │
│  ├────────────────────────────────────────────────────────┤  │
│  │  数据安全 (加密存储, 脱敏, 日志安全)                     │  │
│  ├────────────────────────────────────────────────────────┤  │
│  │  运行时安全 (沙箱, 限流, 熔断)                           │  │
│  ├────────────────────────────────────────────────────────┤  │
│  │  供应链安全 (依赖扫描, 镜像扫描)                         │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

---

## 二、传输层安全

### HTTPS 强制

```nginx
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/ssl/cert.pem;
    ssl_certificate_key /etc/ssl/key.pem;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers 'ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384';
    ssl_prefer_server_ciphers on;

    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    location /api/ {
        proxy_pass http://api:8000;
    }
}
```

### CORS 配置

```python
ALLOWED_ORIGINS = [
    "https://your-domain.com",
    "http://localhost:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
    max_age=3600,
)
```

### 安全响应头

```python
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response
```

---

## 三、输入安全

### Prompt 注入防护

```python
class PromptInjectionDetector:
    INJECTION_PATTERNS = [
        r"(?i)ignore\s+(all\s+)?(previous|above|earlier)\s+instructions?",
        r"(?i)forget\s+(all\s+)?(your|the)\s+(previous|above)\s+instructions?",
        r"(?i)you\s+are\s+now\s+(a|an)\s+",
        r"(?i)new\s+(system\s+)?instructions?",
        r"(?i)system:\s*",
        r"(?i)<\|system\|>",
        r"(?i)<\|im_start\|>",
        r"(?i)DAN\s+mode",
        r"(?i)jailbreak",
        r"(?i)developer\s+mode",
        r"(?i)print\s+(your\s+)?(system\s+)?prompt",
        r"(?i)show\s+(your\s+)?(system\s+)?instructions",
    ]

    @classmethod
    def detect(cls, user_input: str) -> DetectionResult:
        matches = []
        for pattern in cls.INJECTION_PATTERNS:
            found = re.findall(pattern, user_input)
            if found:
                matches.append({"pattern": pattern, "matched": found})

        if matches:
            return DetectionResult(
                is_injection=True,
                confidence=min(0.5 + 0.1 * len(matches), 1.0),
                details=matches,
            )
        return DetectionResult(is_injection=False, confidence=0.0)

    @classmethod
    def sanitize_input(cls, user_input: str) -> str:
        return f'<user_message>{user_input}</user_message>'


def build_safe_messages(system_prompt: str, user_input: str) -> list:
    detection = PromptInjectionDetector.detect(user_input)
    if detection.confidence > 0.7:
        raise SecurityError("检测到 Prompt 注入攻击")

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": PromptInjectionDetector.sanitize_input(user_input)},
    ]
```

### 输出内容过滤

```python
class OutputContentFilter:
    DANGEROUS_PATTERNS = [
        r'<script[^>]*>',
        r'javascript\s*:',
        r'on\w+\s*=',
        r'data:text/html',
        r'vbscript:',
        r'/etc/(passwd|shadow)',
        r'C:\\Windows\\System32\\',
        r"(?i)union\s+select",
        r"(?i)drop\s+table",
    ]

    @classmethod
    def filter(cls, content: str) -> str:
        for pattern in cls.DANGEROUS_PATTERNS:
            content = re.sub(pattern, "[FILTERED]", content)
        return content
```

---

## 四、数据安全

### 敏感数据加密

```python
from cryptography.fernet import Fernet

class SensitiveDataEncryptor:
    def __init__(self, key: bytes = None):
        self.key = key or Fernet.generate_key()
        self.cipher = Fernet(self.key)

    def encrypt(self, plaintext: str) -> str:
        return self.cipher.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        return self.cipher.decrypt(ciphertext.encode()).decode()
```

### 日志脱敏

```python
class SensitiveLogFilter(logging.Filter):
    REDACT_PATTERNS = [
        (r'sk-[a-zA-Z0-9]{20,}', '[OPENAI_KEY]'),
        (r'Authorization:\s*Bearer\s+\S+', 'Authorization: [REDACTED]'),
        (r'"password":\s*"\S+"', '"password": "[REDACTED]"'),
        (r'"api_key":\s*"\S+"', '"api_key": "[REDACTED]"'),
    ]

    def filter(self, record):
        if hasattr(record, "msg"):
            msg = str(record.msg)
            for pattern, replacement in self.REDACT_PATTERNS:
                msg = re.sub(pattern, replacement, msg)
            record.msg = msg
        return True

logging.getLogger().addFilter(SensitiveLogFilter())
```

### .gitignore 清单

```gitignore
.env
.env.*
!.env.example
*.key
*.pem
*.crt
*.db
*.sqlite
pgdata/
logs/
*.log
```

---

## 五、API 安全

### 请求大小限制

```python
MAX_REQUEST_SIZE = 1 * 1024 * 1024  # 1MB

@app.middleware("http")
async def limit_request_size(request: Request, call_next):
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_REQUEST_SIZE:
        raise HTTPException(413, "请求体超出大小限制 (1MB)")
    return await call_next(request)
```

---

## 六、运行时安全

### Docker 安全配置

```yaml
services:
  api:
    user: "1000:1000"
    read_only: true
    tmpfs:
      - /tmp:size=100M
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE
    deploy:
      resources:
        limits:
          cpus: "2"
          memory: 1G

  postgres:
    expose:
      - "5432"

  redis:
    expose:
      - "6379"
    command: redis-server --requirepass ${REDIS_PASSWORD}
```

### 启动时安全校验

```python
class ConfigValidator:
    REQUIRED_VARS = [
        "POSTGRES_HOST", "POSTGRES_DB", "POSTGRES_USER",
        "POSTGRES_PASSWORD", "REDIS_HOST", "JWT_SECRET", "ENCRYPTION_KEY",
    ]

    @classmethod
    def validate(cls):
        missing = [v for v in cls.REQUIRED_VARS if not os.getenv(v)]
        if missing:
            raise ConfigError(f"缺少必要的环境变量: {', '.join(missing)}")

        jwt_secret = os.getenv("JWT_SECRET", "")
        if len(jwt_secret) < 32:
            logger.warning("JWT_SECRET 长度不足 32 字符")

ConfigValidator.validate()
```

---

## 七、供应链安全

```bash
# Python 依赖扫描
pip install pip-audit && pip-audit

# Docker 镜像扫描
docker scan orchagent:latest

# CI 集成
name: Security Scan
on: [push, pull_request]
jobs:
  pip-audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install pip-audit && pip-audit
```

---

## 八、审计日志

```python
class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: str
    user_id: str
    action: str
    resource_type: str
    resource_id: str
    details: JSON
    ip_address: str
    user_agent: str
    created_at: datetime

class AuditLogger:
    @staticmethod
    async def log(user, action, resource_type, resource_id, details, request):
        audit = AuditLog(
            user_id=user.id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=json.dumps(details, default=str),
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent", ""),
        )
        db.add(audit)
        await db.commit()
```

---

## 九、安全检查清单

### 开发阶段

| 检查项 | 状态 |
|--------|------|
| `.gitignore` 含 `.env`, `*.key`, `*.pem` | [ ] |
| `.env.example` 不含真实敏感信息 | [ ] |
| JWT Secret 使用强随机字符串 (32+ 字符) | [ ] |
| 所有密码使用 bcrypt 哈希 | [ ] |
| API Key 加密存储 | [ ] |
| 日志自动脱敏 | [ ] |
| Prompt 注入检测开启 | [ ] |
| 工具沙箱隔离开启 | [ ] |
| CORS 配置白名单 | [ ] |
| 请求大小限制 | [ ] |
| 速率限制开启 | [ ] |
| pip-audit 无已知漏洞 | [ ] |

### 部署阶段

| 检查项 | 状态 |
|--------|------|
| HTTPS 强制 | [ ] |
| HSTS 头配置 | [ ] |
| CSP 头配置 | [ ] |
| Docker 容器非 root 运行 | [ ] |
| Docker 容器只读文件系统 | [ ] |
| PostgreSQL 不暴露公网端口 | [ ] |
| Redis 配置密码认证 | [ ] |
| 数据库用户权限最小化 | [ ] |
| 环境变量不注入到前端 | [ ] |
| 健康检查端点不暴露敏感信息 | [ ] |
| 审计日志开启 | [ ] |
| 监控告警已配置 | [ ] |

---

## 十、密码策略

```python
class PasswordPolicy:
    MIN_LENGTH = 8
    REQUIRE_UPPERCASE = True
    REQUIRE_LOWERCASE = True
    REQUIRE_DIGIT = True
    REQUIRE_SPECIAL = True
    MAX_LOGIN_ATTEMPTS = 5
    LOCK_DURATION_MINUTES = 15
```

## 十一、定期安全任务

```python
@celery_app.task
async def daily_security_check():
    # 检查超过90天未修改密码的用户
    # 检查超过30天未使用的 API Key
    # 检查过去24小时登录失败率
    pass
```
