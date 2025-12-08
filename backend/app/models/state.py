from typing import TypedDict, Annotated, List, Optional
from langchain_core.messages import BaseMessage
import operator

# Define State
class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]
    image_path: str
    visual_report: str  # Stores result from visual analysis node
    process_report: str # Stores result from process analysis node
    
    # 吃多少功能的节点状态
    food_report: Optional[str]      # 食物识别结果
    calorie_report: Optional[str]   # 热量估算结果
    exercise_report: Optional[str]  # 运动消耗结果
    meal_time_report: Optional[str] # 用餐时间建议
    meal_time: Optional[str]        # 用户选择的用餐时间
