"""
FoodieParadise Backend 主应用

FastAPI应用的入口文件，负责应用初始化、中间件配置和路由注册。
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import uvicorn

# 加载环境变量
load_dotenv()

from app.controllers.food_controller import router as food_router
from app.database import engine, Base
from app.config import settings

# ========== 数据库初始化 ==========
# 根据ORM模型自动创建数据库表
Base.metadata.create_all(bind=engine)

# ========== 创建FastAPI应用 ==========
app = FastAPI(title=settings.app.app_title)

# ========== CORS中间件配置 ==========
# 配置跨域资源共享，允许前端跨域访问API
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.app.cors_origins_list,  # 允许的源列表
    allow_credentials=True,  # 允许携带凭证
    allow_methods=["*"],  # 允许所有HTTP方法
    allow_headers=["*"],  # 允许所有请求头
)

# ========== 路由注册 ==========
# 注册食物相关的API路由
app.include_router(food_router)


@app.get("/")
async def root():
    """根路径接口
    
    返回API欢迎信息。
    
    Returns:
        dict: 欢迎消息
    """
    return {"message": "欢迎使用好吃嘴儿API"}


if __name__ == "__main__":
    # 运行开发服务器
    uvicorn.run(
        "main:app",
        host=settings.app.host,
        port=settings.app.port,
        reload=settings.app.reload
    )

