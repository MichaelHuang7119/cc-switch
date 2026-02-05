"""Configuration management for CC Switch"""

import json
import os
import shutil
from pathlib import Path
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class CacheConfig(BaseModel):
    """Cache configuration."""

    enabled: bool = True
    cache_type: str = "memory"  # "memory" or "redis"
    default_ttl: int = 3600  # seconds
    max_size: int = 1000  # for memory cache
    redis_url: str = "redis://localhost:6379/0"
    redis_max_connections: int = 20
    # Exclude certain parameters from cache key
    exclude_from_cache: list = Field(default_factory=lambda: ["stream"])


class CircuitBreakerConfig(BaseModel):
    """Circuit breaker configuration."""

    failure_threshold: int = 5
    recovery_timeout: int = 60
    enabled: bool = True


class ProviderConfig(BaseModel):
    """Provider configuration."""

    name: str
    enabled: bool = True
    priority: int = 1
    api_key: str
    base_url: str
    api_version: Optional[str] = None
    timeout: int = 180
    max_retries: int = 2
    custom_headers: Dict[str, str] = Field(default_factory=dict)
    models: Dict[str, List[str]] = Field(default_factory=dict)
    max_tokens_limit: Optional[int] = None  # Per-provider max_tokens limit override
    api_format: str = Field(
        default="openai",
        description="API format: 'openai' or 'anthropic'. Defaults to 'openai' for backward compatibility.",
    )


class ObservabilityConfig(BaseModel):
    """Observability configuration."""

    # Logging configuration
    log_level: str = Field(
        default="info", description="Log level: debug, info, warning, error"
    )
    log_sampling_rate: float = Field(
        default=1.0, description="Log sampling rate (0.0-1.0), 1.0 means log everything"
    )

    # Slow request detection
    slow_request_threshold_ms: int = Field(
        default=5000, description="Slow request threshold in milliseconds"
    )
    enable_slow_request_alert: bool = Field(
        default=True, description="Enable slow request alerting"
    )

    # OpenTelemetry configuration
    otlp_enabled: bool = Field(
        default=False, description="Enable OpenTelemetry tracing"
    )
    otlp_endpoint: Optional[str] = Field(default=None, description="OTLP endpoint URL")
    otlp_service_name: str = Field(
        default="cc-switch", description="Service name for OTLP"
    )
    otlp_headers: Dict[str, str] = Field(
        default_factory=dict, description="OTLP authentication headers"
    )


class AppConfig(BaseModel):
    """Application configuration."""

    providers: List[ProviderConfig] = Field(default_factory=list)
    fallback_strategy: str = "priority"
    circuit_breaker: CircuitBreakerConfig = Field(default_factory=CircuitBreakerConfig)
    cache: CacheConfig = Field(default_factory=CacheConfig)
    observability: ObservabilityConfig = Field(default_factory=ObservabilityConfig)
    retry_on_zero_output_tokens: bool = Field(default=True, description="Whether to retry requests when output tokens is 0")
    retry_on_zero_output_tokens_retries: int = Field(default=3, description="Maximum number of retries when output tokens is 0")


class Config:
    """Configuration manager."""

    # Model name mappings
    MODEL_MAPPINGS = {"haiku": "small", "sonnet": "middle", "opus": "big"}

    def __init__(self, config_path: Optional[str] = None):
        """Initialize configuration from file."""
        # 获取配置路径
        config_path = os.getenv("PROVIDER_CONFIG_PATH")
        if config_path is None:
            config_path = str(Path(__file__).parent.parent.parent / "provider.json")

        # 转为 Path 对象便于操作
        config_file = Path(config_path)

        # 如果配置文件不存在，尝试从 provider.example.json 复制
        if not config_file.exists():
            example_file = config_file.parent / "provider.example.json"
            if example_file.exists():
                print(
                    f"Config file {config_file} not exist, copying from {example_file} ..."
                )
                shutil.copy(example_file, config_file)
            else:
                raise FileNotFoundError(
                    f"Config file {config_file} not exist, and the example file {example_file} not found."
                )

        self.config_path = config_path
        self.app_config = self._load_config()

        # Global token limits (per claude-code-proxy pattern)
        # These apply to all requests regardless of provider
        self.max_tokens_limit = int(
            os.getenv("MAX_TOKENS_LIMIT", "1000000")
        )  # Increased from 4096 to 1000000
        self.min_tokens_limit = int(os.getenv("MIN_TOKENS_LIMIT", "100"))

    def _load_config(self) -> AppConfig:
        """Load configuration from JSON file."""
        with open(self.config_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Validate and create app_config from data
        self.app_config = AppConfig(**data)

        # Override from environment variables
        retry_zero_output_str = os.getenv("RETRY_ZERO_OUTPUT_TOKENS", "")
        if retry_zero_output_str.lower() in ("true", "1", "yes"):
            self.app_config.retry_on_zero_output_tokens = True
        elif retry_zero_output_str.lower() in ("false", "0", "no"):
            self.app_config.retry_on_zero_output_tokens = False

        retry_zero_output_retries_str = os.getenv("RETRY_ZERO_OUTPUT_TOKENS_RETRIES", "")
        if retry_zero_output_retries_str:
            try:
                self.app_config.retry_on_zero_output_tokens_retries = int(retry_zero_output_retries_str)
            except ValueError:
                pass

        return self.app_config

    def get_enabled_providers(self) -> List[ProviderConfig]:
        """Get list of enabled providers sorted by priority."""
        enabled = [p for p in self.app_config.providers if p.enabled]
        return sorted(enabled, key=lambda x: x.priority)

    def resolve_api_key(self, api_key: str) -> str:
        """Resolve environment variable in API key."""
        if api_key.startswith("${") and api_key.endswith("}"):
            var_name = api_key[2:-1]
            return os.getenv(var_name, api_key)
        return api_key

    def map_model_name(self, model: str) -> str:
        """
        Map Anthropic model name to provider model category.

        Checks if the model name contains 'haiku', 'sonnet', or 'opus' keywords
        and maps them to 'small', 'middle', or 'big' respectively.

        Supports various formats:
        - Short names: haiku, sonnet, opus
        - Full names: claude-haiku-4-5-20251001, claude-sonnet-4-5-20250929
        - Any format containing the keywords
        """
        model_lower = model.lower()

        # Check if model name contains any of the mapped keywords
        for keyword, category in self.MODEL_MAPPINGS.items():
            if keyword in model_lower:
                return category

        # If no mapping found, return the original (lowercased)
        # This allows custom model names to pass through
        return model_lower


# Global config instance
config = Config()
