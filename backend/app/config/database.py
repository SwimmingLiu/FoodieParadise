"""
数据库连接模块

使用 SQLAlchemy 管理 MySQL 数据库连接和会话。
提供数据库引擎、会话工厂和依赖注入函数。
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.config import settings

# 从配置中获取数据库连接URL
DATABASE_URL = settings.database.database_url

# 创建数据库引擎
# echo=False: 不打印SQL语句（生产环境推荐）
# pool_pre_ping=True: 连接池预检测，自动处理断开的连接
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# 创建会话工厂
# autocommit=False: 需要显式提交事务
# autoflush=False: 不自动刷新到数据库
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建ORM模型基类
Base = declarative_base()


def get_db():
    """获取数据库会话的依赖注入函数
    
    用于FastAPI的Depends依赖注入，自动管理数据库会话的生命周期。
    使用上下文管理器确保会话在请求结束后正确关闭。
    
    Yields:
        Session: SQLAlchemy数据库会话对象
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

