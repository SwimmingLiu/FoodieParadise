"""
配置模块

统一管理应用的所有配置项，包括数据库、OSS、LLM等第三方服务配置。
"""

from .config import settings

__all__ = ["settings"]
