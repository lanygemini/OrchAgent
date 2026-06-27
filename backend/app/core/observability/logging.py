import structlog
import logging
from pathlib import Path
from app.config import settings


def setup_logging(env: str = "prod"):
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    if env == "dev":
        structlog.configure(
            processors=[
                structlog.stdlib.add_log_level,
                structlog.dev.ConsoleRenderer(colors=True),
            ],
            wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
            logger_factory=structlog.PrintLoggerFactory(),
        )
    else:
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
