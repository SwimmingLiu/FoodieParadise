"""
Agent 服务模块

实现基于 LangGraph 的智能 Agent 工作流。
包含"去哪吃"、"查预制"、"吃多少"三个功能的完整流程。
"""

from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
import json
import base64
import re
import os
import random

from app.models.state import AgentState
from app.services.tools import search_location, analyze_premade, analyze_calories
from app.constants.prompts import WHERE_TO_EAT_PROMPT
from app.constants.preset_responses import (
    WHERE_TO_EAT_PRESETS,
    CHECK_PREMADE_PRESETS,
    CALORIES_PRESETS
)
from app.config import settings
from app.utils.stream_utils import ContentSplitter

from langchain_core.runnables import RunnableConfig
from langchain_core.callbacks.manager import adispatch_custom_event


# ========== 辅助函数 ==========

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


def encode_image(image_path):
    """将图片文件编码为Base64字符串
    
    读取本地图片文件并转换为Base64编码，用于在API请求中传输图片数据。
    
    Args:
        image_path: 图片文件的本地路径
        
    Returns:
        str: Base64编码后的图片字符串
    """
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')


def should_continue(state: AgentState):
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



# ========== 去哪吃功能逻辑 ==========

async def where_to_eat_node(state: AgentState, config: RunnableConfig):
    """处理"去哪吃"功能的主节点，负责图片位置识别和流式输出
    
    该节点接收用户上传的图片，先返回预设响应文本给用户即时反馈，
    然后调用LLM进行位置推理。使用ContentSplitter解析LLM输出，
    将思考过程（reason-content块）和最终答案（answer块）分开返回。
    
    Args:
        state: Agent状态对象，包含图片路径和消息历史
        config: LangChain运行配置，用于事件派发
        
    Yields:
        dict: 包含消息更新的状态字典
    """
    import httpx
    
    # 从状态中获取图片路径和用户查询
    image_path = state.get("image_path")
    user_query = state.get("messages", [{}])[0].content if state.get("messages") else "这是哪里?"
    
    # ========== 步骤1: 发送预设响应 ==========
    # 立即返回预设响应文本，给用户即时反馈，提升体验
    preset_text = get_preset_response(WHERE_TO_EAT_PRESETS)
    await adispatch_custom_event("thought", {"content": preset_text}, config=config)
    
    # ========== 步骤2: 处理图片 ==========
    # 将图片转换为Base64编码或从URL下载
    if image_path.startswith("http"):
        # 图片是远程URL，需要下载并编码
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(image_path, timeout=30.0)
                response.raise_for_status()
                image_data = base64.b64encode(response.content).decode("utf-8")
                content_type = response.headers.get("content-type", "image/jpeg")
                image_url = f"data:{content_type};base64,{image_data}"
        except Exception as e:
            # 图片下载失败，返回错误信息
            yield {"messages": [AIMessage(
                content=f"图片下载失败: {str(e)}",
                additional_kwargs={"message": f"图片下载失败: {str(e)}"}
            )]}
            return
    else:
        # 图片是本地文件路径
        if not os.path.exists(image_path):
            yield {"messages": [AIMessage(content="图片文件不存在")]}
            return
        base64_image = encode_image(image_path)
        image_url = f"data:image/jpeg;base64,{base64_image}"
    
    # ========== 步骤3: 调用LLM进行分析 ==========
    llm_config = settings.llm
    
    # 注意：o4-mini 等推理模型只支持默认的 temperature=1，不传入该参数
    model = ChatOpenAI(
        model=llm_config.default_model,
        base_url=llm_config.openai_api_base
    )
    
    # 构建消息列表：系统提示词 + 用户消息（文本+图片）
    messages = [
        SystemMessage(content=WHERE_TO_EAT_PROMPT),
        HumanMessage(content=[
            {"type": "text", "text": user_query},
            {"type": "image_url", "image_url": {"url": image_url}}
        ])
    ]
    
    # ========== 步骤3.5: 初始化内容分割器 ==========
    # 使用ContentSplitter解析LLM输出，根据``` reason-content和``` answer标记分割
    splitter = ContentSplitter()
    response_content = ""     # 完整响应内容累加
    thought_content = ""      # 推理模型专用字段的思考内容
    
    print(f"[DEBUG] 开始处理去哪吃请求，图片: {image_path}")
    
    try:
        # 流式调用LLM，实时获取响应内容
        async for chunk in model.astream(messages, config=config):
            chunk_content = ""  # 当前 chunk 的内容
            
            # ===== 优先级1: 处理推理内容（专用字段） =====
            # DeepSeek 等推理模型会在 additional_kwargs.reasoning_content 中返回推理过程
            if hasattr(chunk, 'additional_kwargs') and chunk.additional_kwargs:
                reasoning = chunk.additional_kwargs.get("reasoning_content", "")
                if reasoning:
                    # 推理内容独立处理，直接作为思考过程派发
                    await adispatch_custom_event("thought", {"content": reasoning}, config=config)
                    thought_content += reasoning
                    continue  # 推理内容处理完毕，跳过后续逻辑
            
            # ===== 优先级2: 处理 content_blocks（结构化输出） =====
            has_content_blocks = False
            if hasattr(chunk, 'content_blocks') and chunk.content_blocks:
                has_content_blocks = True
                for block in chunk.content_blocks:
                    block_type = block.get("type", "")
                    
                    if block_type == "reasoning":
                        reasoning_text = block.get("reasoning", "")
                        if reasoning_text:
                            await adispatch_custom_event("thought", {"content": reasoning_text}, config=config)
                            thought_content += reasoning_text
                    
                    elif block_type == "text":
                        text_content = block.get("text", "")
                        if text_content:
                            chunk_content += text_content
            
            # ===== 优先级3: 处理普通 content 字段 =====
            if not has_content_blocks and chunk.content:
                chunk_content = chunk.content
            
            # ===== 使用ContentSplitter进行内容分流 =====
            if chunk_content:
                response_content += chunk_content
                
                # 处理chunk并获取需要发射的事件
                events = splitter.process_chunk(chunk_content)
                
                for event in events:
                    event_type = event["type"]
                    event_content = event["content"]
                    
                    if event_type == "thought":
                        # 思考过程：发送thought事件
                        await adispatch_custom_event("thought", {"content": event_content}, config=config)
                    elif event_type == "message":
                        # 最终答案：发送message事件
                        # 清理可能的 JSON 残留标记
                        clean_content = re.sub(r'```json\s*\{[^`]*?\}\s*```', '', event_content)
                        clean_content = re.sub(r'\s*"\s*\}\s*$', '', clean_content)
                        clean_content = re.sub(r'^\s*"\s*\}\s*', '', clean_content)
                        if clean_content.strip():
                            await adispatch_custom_event("message", {"content": clean_content}, config=config)
        
        # 流式传输结束，刷新缓冲区中的剩余内容
        flush_events = splitter.flush()
        for event in flush_events:
            event_type = event["type"]
            event_content = event["content"]
            
            if event_type == "thought":
                await adispatch_custom_event("thought", {"content": event_content}, config=config)
            elif event_type == "message":
                # 清理可能的 JSON 残留标记
                clean_content = re.sub(r'```json\s*\{[^`]*?\}\s*```', '', event_content)
                clean_content = re.sub(r'\s*"\s*\}\s*$', '', clean_content)
                clean_content = re.sub(r'^\s*"\s*\}\s*', '', clean_content)
                if clean_content.strip():
                    await adispatch_custom_event("message", {"content": clean_content}, config=config)

    except Exception as e:
        # LLM调用失败，返回错误信息
        error_msg = f"AI服务调用失败: {str(e)}"
        yield {"messages": [AIMessage(
            content=error_msg,
            additional_kwargs={"message": error_msg}
        )]}
        return
    
    # ========== 步骤4: 获取解析结果并打印调试信息 ==========
    parsed = splitter.get_parsed_content()
    
    print(f"\n{'='*60}")
    print("[DEBUG] LLM 完整输出内容:")
    print(f"{'='*60}")
    print(f"思考过程长度 (reason-content): {len(parsed.thought)}")
    print(f"最终答案长度 (answer): {len(parsed.answer)}")
    print(f"推理模型思考长度: {len(thought_content)}")
    print(f"总响应长度: {len(response_content)}")
    print(f"{'='*60}\n")
    
    # ========== 步骤5: 提取位置JSON信息 ==========
    json_pattern = r'```json\s*(\{[^`]*?\})\s*```'
    json_matches = re.findall(json_pattern, response_content, re.DOTALL)
    
    locations = []
    for json_str in json_matches:
        try:
            json_data = json.loads(json_str)
            if json_data.get("latitude") and json_data.get("longitude"):
                locations.append(json_data)
        except json.JSONDecodeError:
            continue
    
    # ========== 步骤6: 构建最终响应消息 ==========
    final_messages = []
    
    # 合并思考过程（推理模型的reasoning_content + reason-content块）
    combined_thought = thought_content + parsed.thought
    if combined_thought:
        final_messages.append(AIMessage(
            content=combined_thought,
            additional_kwargs={"thought": combined_thought}
        ))

    # 使用解析的answer作为最终结果（如果有的话）
    result_content = parsed.answer if parsed.answer else response_content
    # 从结果内容中移除 JSON 代码块
    result_content = re.sub(r'```json\s*\{[^`]*?\}\s*```', '', result_content)
    # 移除 JSON 样式块的残留结束标记 "}（可能在末尾或单独一行）
    result_content = re.sub(r'\s*"\s*\}\s*$', '', result_content)
    result_content = re.sub(r'^\s*"\s*\}\s*', '', result_content)
    result_content = result_content.strip()
    
    if result_content:
        final_messages.append(AIMessage(
            content=result_content,
            additional_kwargs={"message": result_content}
        ))

    # 添加位置信息（支持多个店铺）
    if locations:
        for loc in locations:
            final_messages.append(AIMessage(
                content=f"位置已识别: {loc.get('name', '未知地点')}",
                additional_kwargs={
                    "function_call": {
                        "action": "open_map",
                        "lat": loc.get("latitude"),
                        "lng": loc.get("longitude"),
                        "name": loc.get("name", "未知地点"),
                        "address": loc.get("address", "地址未知")
                    }
                }
            ))
    else:
        # 未能提取位置信息
        final_messages.append(AIMessage(
            content="未能从响应中提取位置信息。",
            additional_kwargs={"message": "未能从响应中提取位置信息。"}
        ))
        
    yield {"messages": final_messages}


# 构建"去哪吃"工作流图
where_to_eat_workflow = StateGraph(AgentState)
where_to_eat_workflow.add_node("agent", where_to_eat_node)
where_to_eat_workflow.set_entry_point("agent")
where_to_eat_workflow.add_edge("agent", END)
where_to_eat_graph = where_to_eat_workflow.compile()




# ========== 查预制功能逻辑 ==========

async def check_premade_node(state: AgentState):
    """处理"查预制"功能的主节点
    
    分析图片中的菜品是否为预制菜，先返回预设响应，
    然后调用工具进行实际分析。
    
    Args:
        state: Agent状态对象，包含图片路径和消息历史
        
    Returns:
        dict: 包含消息更新的状态字典
    """
    # 发送预设响应
    preset_text = get_preset_response(CHECK_PREMADE_PRESETS)
    
    messages = state["messages"]
    return {
        "messages": [
            AIMessage(
                content=preset_text,
                additional_kwargs={"thought": preset_text}
            ),
            AIMessage(
                content="",
                tool_calls=[{
                    "name": "analyze_premade",
                    "args": {"image_path": state["image_path"]},
                    "id": "call_2"
                }]
            )
        ]
    }


async def premade_tools_node(state: AgentState):
    """执行预制菜分析工具
    
    调用analyze_premade工具，解析结果并格式化为用户友好的报告。
    
    Args:
        state: Agent状态对象
        
    Returns:
        dict: 包含分析报告的消息更新
    """
    messages = state["messages"]
    last_message = messages[-1]
    
    # 检查是否有工具调用
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        tool_call = last_message.tool_calls[0]
        if tool_call["name"] == "analyze_premade":
            # 调用分析工具
            result = analyze_premade.invoke(tool_call["args"])
            data = json.loads(result)
            
            # 构建分析报告
            report = f"**菜品名称**: {data['dish_name']}\n"
            report += f"**预制概率**: {data['score']}%\n"
            report += f"**新鲜度**: {data['freshness']}\n"
            report += "**分析依据**:\n" + "\n".join([f"- {r}" for r in data['reasons']])
            
            return {
                "messages": [
                    AIMessage(
                        content=report,
                        additional_kwargs={"message": report}
                    )
                ]
            }
    return {"messages": []}


# 构建"查预制"工作流图
premade_workflow = StateGraph(AgentState)
premade_workflow.add_node("agent", check_premade_node)
premade_workflow.add_node("tools", premade_tools_node)
premade_workflow.set_entry_point("agent")
premade_workflow.add_conditional_edges("agent", should_continue)
premade_workflow.add_edge("tools", END)
premade_graph = premade_workflow.compile()


# ========== 吃多少功能逻辑 ==========

async def calories_node(state: AgentState):
    """处理"吃多少"功能的主节点
    
    识别图片中的食物并计算热量，先返回预设响应，
    然后调用工具进行实际分析。
    
    Args:
        state: Agent状态对象，包含图片路径和消息历史
        
    Returns:
        dict: 包含消息更新的状态字典
    """
    # 发送预设响应
    preset_text = get_preset_response(CALORIES_PRESETS)
    
    messages = state["messages"]
    return {
        "messages": [
            AIMessage(
                content=preset_text,
                additional_kwargs={"thought": preset_text}
            ),
            AIMessage(
                content="",
                tool_calls=[{
                    "name": "analyze_calories",
                    "args": {"image_path": state["image_path"]},
                    "id": "call_3"
                }]
            )
        ]
    }


async def calories_tools_node(state: AgentState):
    """执行热量分析工具
    
    调用analyze_calories工具，解析结果并格式化为热量报告。
    
    Args:
        state: Agent状态对象
        
    Returns:
        dict: 包含热量报告的消息更新
    """
    messages = state["messages"]
    last_message = messages[-1]
    
    # 检查是否有工具调用
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        tool_call = last_message.tool_calls[0]
        if tool_call["name"] == "analyze_calories":
            # 调用分析工具
            result = analyze_calories.invoke(tool_call["args"])
            data = json.loads(result)
            
            # 构建热量报告
            report = f"**总热量**: {data['total_calories']} 千卡\n\n"
            for item in data['items']:
                report += f"- **{item['name']}**: {item['calories']} 千卡\n"
            report += f"\n**建议**: {data['advice']}"
            
            return {
                "messages": [
                    AIMessage(
                        content=report,
                        additional_kwargs={
                            "message": report,
                            "function_call": {
                                "action": "annotate_image",
                                "items": data['items']
                            }
                        }
                    )
                ]
            }
    return {"messages": []}


# 构建"吃多少"工作流图
calories_workflow = StateGraph(AgentState)
calories_workflow.add_node("agent", calories_node)
calories_workflow.add_node("tools", calories_tools_node)
calories_workflow.set_entry_point("agent")
calories_workflow.add_conditional_edges("agent", should_continue)
calories_workflow.add_edge("tools", END)
calories_graph = calories_workflow.compile()
