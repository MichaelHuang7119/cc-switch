"""Main FastAPI application for CC Switch"""
import os
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from fastapi import FastAPI

from .config.settings import config
from .core import ModelManager
from .routes.providers import router as providers_router, set_provider_service
from .routes.health import router as api_health_router, set_health_service
from .routes.config import router as config_router
from .routes.stats import router as stats_router
from .routes.auth import router as auth_router
from .routes.api_keys import router as api_keys_router
from .routes.conversations import router as conversations_router
from .routes.preferences import router as preferences_router
from .routes.messages import create_messages_router
from .routes.oauth import router as oauth_router
from .routes.health import router as health_router
from .routes.event_logging import router as event_logging_router
from .routes.admin_permissions import router as admin_permissions_router
from .core.lifecycle import startup_event, shutdown_event
from .services.message_service import MessageService
from .services.health_service import HealthService
from .services.provider_service import ProviderService
from .database.core import DatabaseCore
from .database.health_history import HealthHistoryManager

# Configure logging
# Allow log level to be set via environment variable or default to INFO
# Production mode: INFO (clean output)
# Development mode (--dev): DEBUG (detailed logs)
log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
# Map string level to logging constant
log_level_map = {
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARNING': logging.WARNING,
    'ERROR': logging.ERROR,
    'CRITICAL': logging.CRITICAL,
}
log_level_int = log_level_map.get(log_level, logging.INFO)

# Create logs directory
logs_dir = Path(__file__).parent.parent.parent / 'logs'
logs_dir.mkdir(exist_ok=True)

# Configure root logger with rotating file handler and console output
root_logger = logging.getLogger()
root_logger.setLevel(log_level_int)

# File handler - rotating log files (max 10MB, keep 5 backup files)
log_file = logs_dir / 'backend.log'
file_handler = RotatingFileHandler(
    log_file,
    maxBytes=20 * 1024 * 1024,  # 50MB per file
    backupCount=10,
    encoding='utf-8'
)
file_handler.setLevel(log_level_int)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
))

# Console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(log_level_int)
console_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s'
))

root_logger.addHandler(file_handler)
root_logger.addHandler(console_handler)

logger = logging.getLogger(__name__)
logger.info(f"Logging level set to: {log_level}")
logger.info(f"Log files will be saved to: {logs_dir}")


watchdog_log_level = log_level_map.get(os.getenv('WATCHDOG_LOG_LEVEL', 'WARNING').upper(), logging.WARNING)
logging.getLogger("watchdog").setLevel(watchdog_log_level)
logging.getLogger("watchdog.observers").setLevel(watchdog_log_level)
logging.getLogger("watchdog.observers.inotify_buffer").setLevel(watchdog_log_level)
logging.getLogger("watchfiles").setLevel(watchdog_log_level)

# Initialize OpenTelemetry if enabled
_telemetry_enabled = os.getenv("ENABLE_TELEMETRY", "true").lower() in ("true", "1", "yes")
if _telemetry_enabled:
    try:
        from .infrastructure.telemetry import initialize_telemetry, instrument_fastapi, instrument_httpx
        initialize_telemetry(
            service_name="cc-switch",
            otlp_endpoint=os.getenv("OTLP_ENDPOINT"),
            enable_tracing=True,
            enable_metrics=True
        )
        instrument_httpx()
        logger.info("OpenTelemetry enabled")
    except Exception as e:
        logger.warning(f"Failed to initialize OpenTelemetry: {e}")

# Suppress verbose httpx/httpcore logging from OpenAI SDK
# This prevents logging every HTTP request, reducing noise in logs
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

# Suppress aiosqlite DEBUG logs - prevent printing every database operation
logging.getLogger("aiosqlite").setLevel(logging.WARNING)

app = FastAPI(
    title="CC Switch",
    description="""
    CC Switch - High-performance AI Model API Proxy

    ## Claude Code 配置

    在 Claude Code 中使用本服务，需要配置以下环境变量：

    ```bash
    export ANTHROPIC_BASE_URL=http://localhost:5175
    export ANTHROPIC_API_KEY="any-value"
    ```

    然后启动 Claude Code 进行 Vibe Coding。

    **注意**：`ANTHROPIC_BASE_URL` 需要替换为实际的前端服务地址。
    """,
    version="1.0.0"
)

# Instrument FastAPI with OpenTelemetry if enabled
if _telemetry_enabled:
    try:
        from .infrastructure.telemetry import instrument_fastapi
        instrument_fastapi(app)
    except Exception as e:
        logger.warning(f"Failed to instrument FastAPI: {e}")

model_manager = ModelManager(config)

# Initialize database
db_core = DatabaseCore()

# Initialize services
message_service = MessageService(model_manager)
health_history_manager = HealthHistoryManager(db_core)
health_service = HealthService(message_service, health_history_manager)
provider_service = ProviderService()

# Set service instances for API routes
set_health_service(health_service)
set_provider_service(provider_service)

# Register routes
app.include_router(create_messages_router(model_manager))
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(api_keys_router)
app.include_router(providers_router)
app.include_router(api_health_router)
app.include_router(config_router)
app.include_router(stats_router)
app.include_router(conversations_router)
app.include_router(preferences_router)
app.include_router(oauth_router)
app.include_router(event_logging_router)
app.include_router(admin_permissions_router)


@app.on_event("startup")
async def on_startup():
    """Application startup event."""
    await startup_event()


@app.on_event("shutdown")
async def on_shutdown():
    """Application shutdown event."""
    await shutdown_event()


@app.get("/health")
async def docker_health_check():
    """Docker health check endpoint - no authentication required."""
    return {"status": "healthy"}
