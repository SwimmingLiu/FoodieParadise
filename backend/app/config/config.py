"""
配置管理模块

使用 Pydantic BaseSettings 实现类型安全的配置管理。
所有配置项从环境变量或 .env 文件中加载。
"""

from pydantic_settings import BaseSettings
from typing import Optional


class DatabaseConfig(BaseSettings):
    """数据库配置类
    
    管理MySQL数据库连接相关的配置参数。
    """
    
    # MySQL 连接参数
    mysql_host: str
    mysql_port: int = 3306
    mysql_user: str
    mysql_password: str
    mysql_db: str
    
    class Config:
        # 环境变量名称大小写不敏感
        case_sensitive = False
        # 从 .env 文件加载配置
        env_file = ".env"
        # 忽略额外的环境变量
        extra = "ignore"
    
    @property
    def database_url(self) -> str:
        """构建数据库连接URL
        
        Returns:
            str: MySQL数据库连接字符串
        """
        return (
            f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_db}"
        )



class QiniuConfig(BaseSettings):
    """七牛云OSS配置类
    
    管理七牛云对象存储服务的相关配置。
    """
    
    # 七牛云认证密钥
    qiniu_access_key: str
    qiniu_secret_key: str
    # 存储空间名称
    qiniu_bucket_name: str
    # CDN加速域名
    qiniu_domain: str
    # 上传目录前缀（可选）
    qiniu_upload_dir: str = ""
    
    class Config:
        case_sensitive = False
        env_file = ".env"
        # 忽略额外的环境变量
        extra = "ignore"


class LLMConfig(BaseSettings):
    """大语言模型配置类
    
    管理OpenAI兼容API的配置参数。
    """
    
    # OpenAI API密钥
    openai_api_key: str
    # API基础URL（支持自定义端点）
    openai_api_base: str
    # 默认使用的模型名称
    default_model: str = "o4-mini"
    # 模型温度参数（控制随机性）
    default_temperature: float = 0.0
    # 请求超时时间（秒），用于处理网络不稳定情况
    request_timeout: float = 120.0
    # 最大重试次数，用于处理临时性连接错误
    max_retries: int = 3
    
    class Config:
        case_sensitive = False
        env_file = ".env"
        # 忽略额外的环境变量
        extra = "ignore"


class AppConfig(BaseSettings):
    """应用配置类
    
    管理FastAPI应用运行时的配置参数。
    """
    
    # 应用标题
    app_title: str = "FoodieParadise Backend"
    # 监听主机地址
    host: str = "0.0.0.0"
    # 监听端口
    port: int = 8000
    # 是否开启热重载
    reload: bool = True
    # CORS允许的源（多个用逗号分隔）
    cors_origins: str = "*"
    
    class Config:
        case_sensitive = False
        env_file = ".env"
        # 忽略额外的环境变量
        extra = "ignore"
    
    @property
    def cors_origins_list(self) -> list:
        """获取CORS允许源列表
        
        Returns:
            list: CORS允许的源地址列表
        """
        if self.cors_origins == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_origins.split(",")]


from app.config.logging import LoggingConfig


class Settings:
    """统一配置管理类
    
    聚合所有子配置类，提供统一的配置访问入口。
    """
    
    def __init__(self):
        # 初始化各个配置模块
        self.database = DatabaseConfig()
        self.qiniu = QiniuConfig()
        self.llm = LLMConfig()
        self.app = AppConfig()
        self.logging = LoggingConfig()


# 创建全局配置实例
settings = Settings()
