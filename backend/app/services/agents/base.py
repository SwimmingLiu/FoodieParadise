"""
Agent 基础设施模块

提供所有Agent工作流共用的基础函数和工具。
"""

import random
from typing import Union

from app.constants.preset_responses import (
    WHERE_TO_EAT_PRESETS,
    CHECK_PREMADE_PRESETS,
    CALORIES_PRESETS
)
from app.models.state import AgentState
from langgraph.graph import END


def get_preset_response(preset_list: list) -> str:
    """从预设响应列表中随机选择一条
    
    用于在LLM实际响应前给用户提供即时反馈，提升用户体验。
    每次调用随机选择，确保用户看到的提示文本每次都不同。
    
    Args:
        preset_list: 预设响应文本列表
        
    Returns:
        str: 随机选择的预设响应文本
    """
    return random.choice(preset_list)


def should_continue(state: AgentState) -> Union[str, object]:
    """判断工作流是否应该继续执行
    
    检查最后一条消息是否包含工具调用，决定下一步是执行工具还是结束流程。
    
    Args:
        state: Agent状态对象，包含消息历史
        
    Returns:
        str: "tools" 表示需要执行工具，END 表示流程结束
    """
    messages = state["messages"]
    last_message = messages[-1]
    # 检查最后一条消息是否包含工具调用请求
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    return END


async def empty_start_node(state: AgentState) -> dict:
    """空启动节点
    
    用于工作流的初始化，不执行任何操作，仅传递状态。
    LangGraph要求有一个入口节点，此节点用于支持后续的并行分支。
    
    Args:
        state: Agent状态对象
        
    Returns:
        dict: 空字典，不修改状态
    """
    return {}
