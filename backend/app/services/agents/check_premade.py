"""
查预制功能模块

实现预制菜检测工作流。
使用并行分析架构：视觉分析 + 工艺分析 -> 聚合输出
"""

from langgraph.graph import StateGraph, END
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.callbacks.manager import adispatch_custom_event

from app.models.state import AgentState
from app.constants.prompts import (
    VISUAL_ANALYSIS_PROMPT,
    PROCESS_ANALYSIS_PROMPT,
    CHECK_PREMADE_MAIN_PROMPT
)
from app.constants.preset_responses import CHECK_PREMADE_PRESETS
from app.utils.image_utils import prepare_image_url
from app.utils.llm_utils import create_chat_model, build_vision_messages
from app.utils.stream_utils import ContentSplitter
from app.services.agents.base import get_preset_response, empty_start_node


async def visual_analysis_node(state: AgentState, config: RunnableConfig):
    """视觉分析节点：分析物理特征
    
    分析菜品的色泽、质地、光泽度等视觉特征，
    判断是否呈现预制菜的典型外观。
    
    Args:
        state: Agent状态对象
        config: LangChain运行配置
        
    Returns:
        dict: 包含视觉分析报告的状态更新
    """
    image_path = state.get("image_path")
    
    # 处理图片
    image_url, error = await prepare_image_url(image_path)
    if error:
        return {"visual_report": f"视觉分析失败: {error}"}
    
    model = create_chat_model()
    messages = build_vision_messages(VISUAL_ANALYSIS_PROMPT, "分析这张图片", image_url)
    
    response = await model.ainvoke(messages)
    await adispatch_custom_event("thought", {"content": "正在分析视觉特征（色泽、质地）...\n"}, config=config)
    
    return {"visual_report": response.content}


async def process_analysis_node(state: AgentState, config: RunnableConfig):
    """工艺分析节点：分析工业化痕迹
    
    分析菜品的制作工艺特征，如锅气、工业化切割痕迹、
    标准化摆盘等，判断是否可能为工厂批量生产。
    
    Args:
        state: Agent状态对象
        config: LangChain运行配置
        
    Returns:
        dict: 包含工艺分析报告的状态更新
    """
    image_path = state.get("image_path")
    
    # 处理图片
    image_url, error = await prepare_image_url(image_path)
    if error:
        return {"process_report": f"工艺分析失败: {error}"}
    
    model = create_chat_model()
    messages = build_vision_messages(PROCESS_ANALYSIS_PROMPT, "分析这张图片", image_url)
    
    response = await model.ainvoke(messages)
    await adispatch_custom_event("thought", {"content": "正在推测制作工艺（锅气、工业痕迹）...\n"}, config=config)
    
    return {"process_report": response.content}


async def check_premade_aggregator_node(state: AgentState, config: RunnableConfig):
    """聚合节点：汇总分析并输出最终报告
    
    综合视觉分析和工艺分析的结果，生成最终的预制菜判断报告，
    包括预制概率、新鲜度评估和推理依据。
    
    Args:
        state: Agent状态对象
        config: LangChain运行配置
        
    Returns:
        dict: 包含最终分析结果的状态更新
    """
    visual_report = state.get("visual_report", "未获取到视觉分析")
    process_report = state.get("process_report", "未获取到工艺分析")
    
    # 发送预设思考
    preset_text = get_preset_response(CHECK_PREMADE_PRESETS)
    await adispatch_custom_event("thought", {"content": f"{preset_text}\n正在综合多维度分析结果..."}, config=config)
    
    model = create_chat_model()
    
    from langchain_core.messages import SystemMessage, HumanMessage
    messages = [
        SystemMessage(content=CHECK_PREMADE_MAIN_PROMPT),
        HumanMessage(content=f"【视觉分析报告】\n{visual_report}\n\n【工艺分析报告】\n{process_report}")
    ]
    
    # 流式输出
    response_content = ""
    
    try:
        async for chunk in model.astream(messages, config=config):
            chunk_content = ""
            if chunk.content:
                chunk_content = chunk.content
                
            if chunk_content:
                response_content += chunk_content
                await adispatch_custom_event("message", {"content": chunk_content}, config=config)
                
    except Exception as e:
        error_msg = f"聚合分析失败: {str(e)}"
        return {"messages": [AIMessage(content=error_msg)]}

    return {"messages": [AIMessage(content=response_content)]}


# ========== 构建工作流图 ==========
premade_workflow = StateGraph(AgentState)

# 添加节点
premade_workflow.add_node("start", empty_start_node)
premade_workflow.add_node("visual_analysis", visual_analysis_node)
premade_workflow.add_node("process_analysis", process_analysis_node)
premade_workflow.add_node("aggregator", check_premade_aggregator_node)

# 设置入口点
premade_workflow.set_entry_point("start")

# 从启动节点并行执行分析节点
premade_workflow.add_edge("start", "visual_analysis")
premade_workflow.add_edge("start", "process_analysis")

# 汇聚到聚合节点
premade_workflow.add_edge("visual_analysis", "aggregator")
premade_workflow.add_edge("process_analysis", "aggregator")

premade_workflow.add_edge("aggregator", END)

premade_graph = premade_workflow.compile()
