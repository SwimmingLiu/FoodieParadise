"""
日志配置模块

提供统一的日志配置管理，支持从环境变量加载日志级别和格式。
遵循 FastAPI 分层架构最佳实践，将日志配置集中管理。
"""

import logging
import sys
from typing import Optional

from pydantic_settings import BaseSettings


class LoggingConfig(BaseSettings):
    """日志配置类
    
    管理日志系统的配置参数，支持从环境变量加载。
    
    Attributes:
        log_level: 日志级别，默认为 DEBUG
        log_format: 日志格式字符串
    """
    
    log_level: str = "DEBUG"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    class Config:
        case_sensitive = False
        env_file = ".env"
        extra = "ignore"


# 全局日志配置实例
_logging_config: Optional[LoggingConfig] = None
_is_configured: bool = False


def setup_logging(config: Optional[LoggingConfig] = None) -> None:
    """初始化日志配置
    
    配置 Python 标准日志系统，设置日志级别、格式和输出处理器。
    此函数应在应用启动时调用一次。
    
    Args:
        config: 日志配置对象，如果为 None 则使用默认配置
    """
    global _logging_config, _is_configured
    
    if _is_configured:
        return
    
    if config is None:
        config = LoggingConfig()
    
    _logging_config = config
    
    # 配置根日志记录器
    logging.basicConfig(
        level=getattr(logging, config.log_level.upper(), logging.DEBUG),
        format=config.log_format,
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    
    _is_configured = True


def get_logger(name: str) -> logging.Logger:
    """获取指定名称的 logger 实例
    
    如果日志系统尚未初始化，会自动调用 setup_logging() 进行初始化。
    
    Args:
        name: logger 名称，通常使用 __name__
        
    Returns:
        logging.Logger: 配置好的 logger 实例
    """
    if not _is_configured:
        setup_logging()
    
    return logging.getLogger(name)
