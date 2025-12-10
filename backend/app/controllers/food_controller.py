"""
Food控制器模块

处理所有与食物相关的API请求路由。
遵循 FastAPI 分层架构，Controller 层仅负责：
- 接收和验证HTTP请求
- 调用Service层处理业务逻辑
- 返回HTTP响应

业务逻辑统一封装在 app.services.food_service 中。
"""

from fastapi import APIRouter, UploadFile, File
from fastapi.responses import StreamingResponse
import shutil
import os

# ========== 导入配置和日志 ==========
from app.config import get_logger

logger = get_logger(__name__)

# ========== 导入业务模块 ==========
from app.models.schemas import ChatRequest, CaloriesRequest, HistoryRecord
from app.services.food_service import food_service
from app.services.oss_service import QiniuService
from app.utils.stream_utils import stream_generator
from app.repositories.history_repo import save_history, get_user_history

# 创建API路由器
router = APIRouter()

# 初始化OSS服务
oss_service = QiniuService()


@router.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """文件上传接口
    
    接收用户上传的文件，保存到临时目录后上传至七牛云OSS。
    上传成功后返回文件的公开访问URL。
    
    Args:
        file: 上传的文件对象
        
    Returns:
        dict: 包含文件URL的字典 {"file_path": "https://..."}
    """
    temp_file_path = f"/tmp/{file.filename}"
    with open(temp_file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    try:
        file_url = oss_service.upload_file(temp_file_path, file.filename)
        return {"file_path": file_url}
    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)


@router.post("/api/where-to-eat")
async def where_to_eat(request: ChatRequest):
    """去哪吃功能接口
    
    接收用户上传的图片和问题，使用AI识别图片中的餐厅位置。
    返回流式响应，包括思考过程（thought）和最终的位置信息（message）。
    
    Args:
        request: 包含图片路径和用户问题的请求对象
        
    Returns:
        StreamingResponse: SSE流式响应
    """
    logger.info(f"[CONTROLLER] 收到去哪吃请求: file_path={request.file_path}")
    
    return StreamingResponse(
        stream_generator(food_service.process_where_to_eat_stream(
            file_path=request.file_path,
            query=request.query
        )),
        media_type="text/event-stream"
    )


@router.post("/api/check-premade")
async def check_premade(request: ChatRequest):
    """查预制功能接口
    
    接收用户上传的菜品图片，使用AI分析是否为预制菜。
    返回流式响应，包括分析过程（thought）和分析结论（message）。
    
    Args:
        request: 包含图片路径的请求对象
        
    Returns:
        StreamingResponse: SSE流式响应
    """
    logger.info(f"[CONTROLLER] 收到查预制请求: file_path={request.file_path}")
    
    return StreamingResponse(
        stream_generator(food_service.process_check_premade_stream(
            file_path=request.file_path
        )),
        media_type="text/event-stream"
    )


@router.post("/api/calories")
async def calories(request: CaloriesRequest):
    """吃多少功能接口
    
    接收用户上传的食物图片和用餐时间，使用AI并发分析食物热量。
    返回流式响应，包括思考过程、热量报告和食物卡片信息。
    
    Args:
        request: 包含图片路径和用餐时间的请求对象
        
    Returns:
        StreamingResponse: SSE流式响应
    """
    logger.info(f"[CONTROLLER] 收到吃多少请求: file_path={request.file_path}, meal_time={request.meal_time}")
    
    return StreamingResponse(
        stream_generator(food_service.process_calories_stream(
            file_path=request.file_path,
            meal_time=request.meal_time or "午餐"
        )),
        media_type="text/event-stream"
    )


@router.get("/api/history")
async def get_history():
    """获取历史记录接口
    
    返回用户的所有历史记录。
    
    Returns:
        list: 历史记录列表
    """
    return get_user_history()


@router.post("/api/history")
async def add_history(record: HistoryRecord):
    """添加历史记录接口
    
    保存一条新的历史记录到数据库。
    
    Args:
        record: 历史记录对象
        
    Returns:
        dict: 操作状态 {"status": "ok"}
    """
    save_history(record.dict())
    return {"status": "ok"}
