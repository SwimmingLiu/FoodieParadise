from pydantic import BaseModel
from typing import Dict, Any, Optional

class ChatRequest(BaseModel):
    file_path: str
    query: Optional[str] = None

class HistoryRecord(BaseModel):
    type: str # 'where-to-eat', 'check-premade', 'calories'
    image_path: str
    summary: str
    details: Dict[str, Any] = {}
