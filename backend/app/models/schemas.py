from pydantic import BaseModel
from typing import Dict, Any, Optional

class ChatRequest(BaseModel):
    file_path: str
    query: Optional[str] = None

class CaloriesRequest(BaseModel):
    """"吃多少"功能的请求模型
    
    Attributes:
        file_path: 上传的图片URL或路径
        meal_time: 用餐时间 (早餐/午餐/晚餐/下午茶/夜宵)
    """
    file_path: str
    meal_time: Optional[str] = "午餐"

class HistoryRecord(BaseModel):
    type: str # 'where-to-eat', 'check-premade', 'calories'
    image_path: str
    summary: str
    details: Dict[str, Any] = {}
