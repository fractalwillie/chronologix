# __init__.py

from .config import LogConfig, LogConfigError
from .manager import LogManager

__all__ = ["LogConfig", "LogManager", "LogConfigError"]
