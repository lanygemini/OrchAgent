"""日志配置：使用 structlog 实现结构化日志（开发模式彩色控制台 / 生产模式 JSON）"""
import structlog
import logging
from pathlib import Path
from app.config import settings


def setup_logging(env: str = "prod"):
    """配置 structlog 日志处理器"""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    if env == "dev":
        # 开发模式：彩色控制台输出
        structlog.configure(
            processors=[
                structlog.stdlib.add_log_level,
                structlog.dev.ConsoleRenderer(colors=True),
            ],
            wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
            logger_factory=structlog.PrintLoggerFactory(),
        )
    else:
        # 生产模式：JSON 格式写入文件
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_log_level,
                structlog.processors.TimeStamper(fmt="iso", utc=True),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.JSONRenderer(),
            ],
            wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
            logger_factory=structlog.WriteLoggerFactory(
                file=open(log_dir / "app.log", "a", encoding="utf-8")
            ),
        )

    logging.basicConfig(level=settings.log_level)


logger = structlog.get_logger()
