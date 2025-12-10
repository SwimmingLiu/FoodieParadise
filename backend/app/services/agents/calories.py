"""
吃多少功能模块

实现食物热量分析工作流。
使用并行分析架构：食物识别 + 热量估算 + 运动消耗 -> 聚合输出
"""

import json
import re

from langgraph.graph import StateGraph, END
from langchain_core.messages import AIMessage, SystemMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.callbacks.manager import adispatch_custom_event

from app.models.state import AgentState
from app.constants.prompts import (
    FOOD_IDENTIFICATION_PROMPT,
    CALORIE_ESTIMATION_PROMPT,
    EXERCISE_ESTIMATION_PROMPT,
    CALORIES_MAIN_PROMPT
)
from app.constants.preset_responses import CALORIES_PRESETS
from app.utils.image_utils import prepare_image_url
from app.utils.llm_utils import create_chat_model, build_vision_messages
from app.utils.stream_utils import ContentSplitter
from app.services.agents.base import get_preset_response, empty_start_node


async def food_identification_node(state: AgentState, config: RunnableConfig):
    """食物识别节点：识别图片中的所有食物
    
    分析图片中的食物种类、份量、烹饪方式等信息。
    
    Args:
        state: Agent状态对象
        config: LangChain运行配置
        
    Returns:
        dict: 包含食物识别结果的状态更新
    """
    image_path = state.get("image_path")
    
    # 处理图片
    image_url, error = await prepare_image_url(image_path)
    if error:
        return {"food_report": f"食物识别失败: {error}"}
    
    model = create_chat_model()
    messages = build_vision_messages(
        FOOD_IDENTIFICATION_PROMPT,
        "请识别这张图片中的所有食物",
        image_url
    )
    
    response = await model.ainvoke(messages)
    await adispatch_custom_event("thought", {"content": "🍽️ 正在识别图片中的食物...\n"}, config=config)
    
    return {"food_report": response.content}


async def calorie_estimation_node(state: AgentState, config: RunnableConfig):
    """热量估算节点：估算每种食物的热量
    
    根据食物种类和份量计算热量值。
    
    Args:
        state: Agent状态对象
        config: LangChain运行配置
        
    Returns:
        dict: 包含热量估算结果的状态更新
    """
    image_path = state.get("image_path")
    
    # 处理图片
    image_url, error = await prepare_image_url(image_path)
    if error:
        return {"calorie_report": f"热量估算失败: {error}"}
    
    model = create_chat_model()
    messages = build_vision_messages(
        CALORIE_ESTIMATION_PROMPT,
        "请估算图片中每种食物的热量",
        image_url
    )
    
    response = await model.ainvoke(messages)
    await adispatch_custom_event("thought", {"content": "🔢 正在估算食物热量...\n"}, config=config)
    
    return {"calorie_report": response.content}


async def exercise_estimation_node(state: AgentState, config: RunnableConfig):
    """运动消耗估算节点：计算消耗热量所需的运动量
    
    将热量转换为具体的运动时间建议。
    
    Args:
        state: Agent状态对象
        config: LangChain运行配置
        
    Returns:
        dict: 包含运动消耗结果的状态更新
    """
    image_path = state.get("image_path")
    
    # 处理图片
    image_url, error = await prepare_image_url(image_path)
    if error:
        return {"exercise_report": f"运动消耗估算失败: {error}"}
    
    model = create_chat_model()
    messages = build_vision_messages(
        EXERCISE_ESTIMATION_PROMPT,
        "请计算消耗这些食物热量所需的运动量",
        image_url
    )
    
    response = await model.ainvoke(messages)
    await adispatch_custom_event("thought", {"content": "🏃 正在计算运动消耗...\n"}, config=config)
    
    return {"exercise_report": response.content}


async def calories_aggregator_node(state: AgentState, config: RunnableConfig):
    """聚合节点：汇总所有分析结果并生成最终报告
    
    根据食物识别、热量估算、运动消耗报告生成综合分析报告。
    
    Args:
        state: Agent状态对象，包含各节点分析结果
        config: LangChain运行配置
        
    Returns:
        dict: 包含最终报告的状态更新
    """
    food_report = state.get("food_report", "未获取到食物识别报告")
    calorie_report = state.get("calorie_report", "未获取到热量估算报告")
    exercise_report = state.get("exercise_report", "未获取到运动消耗报告")
    meal_time = state.get("meal_time", "午餐")
    
    # 发送预设思考
    preset_text = get_preset_response(CALORIES_PRESETS)
    await adispatch_custom_event("thought", {"content": f"{preset_text}\n⏰ 正在综合分析结果..."}, config=config)
    
    model = create_chat_model()
    
    # 填充提示词中的meal_time
    prompt = CALORIES_MAIN_PROMPT.replace("{meal_time}", meal_time)
    
    messages = [
        SystemMessage(content=prompt),
        HumanMessage(content=f"""【食物识别报告】
{food_report}

【热量估算报告】
{calorie_report}

【运动消耗报告】
{exercise_report}

用餐时间：{meal_time}

请根据以上报告生成综合分析结果。""")
    ]
    
    # 初始化内容分割器
    splitter = ContentSplitter()
    response_content = ""
    
    try:
        async for chunk in model.astream(messages, config=config):
            chunk_content = ""
            if chunk.content:
                chunk_content = chunk.content
            
            if chunk_content:
                response_content += chunk_content
                # 使用ContentSplitter进行内容分流
                events = splitter.process_chunk(chunk_content)
                
                for event in events:
                    event_type = event["type"]
                    event_content = event["content"]
                    
                    if event_type == "thought":
                        await adispatch_custom_event("thought", {"content": event_content}, config=config)
                    elif event_type == "message":
                        await adispatch_custom_event("message", {"content": event_content}, config=config)
        
        # 刷新缓冲区
        flush_events = splitter.flush()
        for event in flush_events:
            event_type = event["type"]
            event_content = event["content"]
            
            if event_type == "thought":
                await adispatch_custom_event("thought", {"content": event_content}, config=config)
            elif event_type == "message":
                await adispatch_custom_event("message", {"content": event_content}, config=config)
                
    except Exception as e:
        error_msg = f"聚合分析失败: {str(e)}"
        return {"messages": [AIMessage(content=error_msg)]}
    
    # 解析JSON结果并生成function_call
    try:
        json_match = re.search(r'\{[\s\S]*?"food_items"[\s\S]*?\}', response_content)
        if json_match:
            json_str = json_match.group()
            # 清理JSON字符串
            json_str = re.sub(r'"reason-content"\s*:\s*"[^"]*"\s*,?', '', json_str)
            json_str = re.sub(r'"answer"\s*:\s*"[^"]*"\s*,?', '', json_str)
            
            food_data = json.loads(json_str)
            
            # 发送function_call事件
            await adispatch_custom_event("function_call", {
                "content": json.dumps({
                    "action": "calories_result",
                    "food_items": food_data.get("food_items", []),
                    "total_calories": food_data.get("total_calories", 0),
                    "overall_advice": food_data.get("overall_advice", "")
                })
            }, config=config)
    except Exception as e:
        print(f"[DEBUG] JSON解析失败: {e}")
    
    return {"messages": [AIMessage(content=response_content)]}


# ========== 构建工作流图 ==========
calories_workflow = StateGraph(AgentState)

# 添加节点
calories_workflow.add_node("start", empty_start_node)
calories_workflow.add_node("food_identification", food_identification_node)
calories_workflow.add_node("calorie_estimation", calorie_estimation_node)
calories_workflow.add_node("exercise_estimation", exercise_estimation_node)
calories_workflow.add_node("aggregator", calories_aggregator_node)

# 设置入口点
calories_workflow.set_entry_point("start")

# 从启动节点并行执行三个分析节点
calories_workflow.add_edge("start", "food_identification")
calories_workflow.add_edge("start", "calorie_estimation")
calories_workflow.add_edge("start", "exercise_estimation")

# 汇聚到聚合节点
calories_workflow.add_edge("food_identification", "aggregator")
calories_workflow.add_edge("calorie_estimation", "aggregator")
calories_workflow.add_edge("exercise_estimation", "aggregator")

calories_workflow.add_edge("aggregator", END)

calories_graph = calories_workflow.compile()
