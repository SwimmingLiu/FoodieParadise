"""
去哪吃功能模块

实现基于图片的餐厅位置识别工作流。
接收用户上传的图片，分析并返回可能的餐厅位置信息。
"""

import json
import re

from langgraph.graph import StateGraph, END
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.callbacks.manager import adispatch_custom_event

from app.models.state import AgentState
from app.constants.prompts import WHERE_TO_EAT_PROMPT
from app.constants.preset_responses import WHERE_TO_EAT_PRESETS
from app.utils.image_utils import prepare_image_url
from app.utils.llm_utils import create_chat_model, build_vision_messages
from app.utils.stream_utils import ContentSplitter
from app.services.agents.base import get_preset_response


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
    # 从状态中获取图片路径和用户查询
    image_path = state.get("image_path")
    user_query = state.get("messages", [{}])[0].content if state.get("messages") else "这是哪里?"
    
    # ========== 步骤1: 发送预设响应 ==========
    preset_text = get_preset_response(WHERE_TO_EAT_PRESETS)
    await adispatch_custom_event("thought", {"content": preset_text}, config=config)
    
    # ========== 步骤2: 处理图片 ==========
    image_url, error = await prepare_image_url(image_path)
    if error:
        yield {"messages": [AIMessage(
            content=error,
            additional_kwargs={"message": error}
        )]}
        return
    
    # ========== 步骤3: 调用LLM进行分析 ==========
    model = create_chat_model()
    messages = build_vision_messages(WHERE_TO_EAT_PROMPT, user_query, image_url)
    
    # ========== 步骤4: 流式处理LLM响应 ==========
    splitter = ContentSplitter()
    response_content = ""
    thought_content = ""
    
    print(f"[DEBUG] 开始处理去哪吃请求，图片: {image_path}")
    
    try:
        async for chunk in model.astream(messages, config=config):
            chunk_content = ""
            
            # 优先获取 content 内容
            if hasattr(chunk, "content") and chunk.content:
                chunk_content = chunk.content
            
            # ===== 使用ContentSplitter进行内容分流 =====
            if chunk_content:
                response_content += chunk_content
                events = splitter.process_chunk(chunk_content)
                
                for event in events:
                    event_type = event["type"]
                    event_content = event["content"]
                    
                    if event_type == "thought":
                        await adispatch_custom_event("thought", {"content": event_content}, config=config)
                    elif event_type == "message":
                        # 尝试清理可能出现的JSON块（注意：流式过程中可能清理不完全，在最终结果中会再次清理）
                        # 实际上流式输出时难以完美去除尚未结束的JSON块，暂时直接输出，前端不展示或由最终结果覆盖
                        # 这里还是做简单的JSON块标记清理
                        clean_content = _clean_message_content(event_content)
                        if clean_content.strip():
                            await adispatch_custom_event("message", {"content": clean_content}, config=config)
        
        # 刷新缓冲区
        flush_events = splitter.flush()
        for event in flush_events:
            event_type = event["type"]
            event_content = event["content"]
            
            if event_type == "thought":
                await adispatch_custom_event("thought", {"content": event_content}, config=config)
            elif event_type == "message":
                clean_content = _clean_message_content(event_content)
                if clean_content.strip():
                    await adispatch_custom_event("message", {"content": clean_content}, config=config)

    except Exception as e:
        error_msg = f"AI服务调用失败: {str(e)}"
        yield {"messages": [AIMessage(
            content=error_msg,
            additional_kwargs={"message": error_msg}
        )]}
        return
    
    # ========== 步骤5: 获取解析结果 ==========
    parsed = splitter.get_parsed_content()
    
    print(f"\n{'='*60}")
    print("[DEBUG] LLM 完整输出内容:")
    print(f"{'='*60}")
    print(f"思考过程长度 (reason-content): {len(parsed.thought)}")
    print(f"最终答案长度 (answer): {len(parsed.answer)}")
    print(f"推理模型思考长度: {len(thought_content)}")
    print(f"总响应长度: {len(response_content)}")
    print(f"{'='*60}\n")
    
    # ========== 步骤6: 提取位置JSON信息 ==========
    # 从完整响应中提取 JSON
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
    
    # ========== 步骤7: 构建最终响应消息 ==========
    final_messages = []
    
    # 合并思考过程
    # 注意：refactor 后 thought_content 主要由 splitter 收集，前面的 thought_content 变量可能不再使用
    # 但为了兼容，如果 splitter.thought 有内容就用 splitter 的
    combined_thought = parsed.thought
    if combined_thought:
        final_messages.append(AIMessage(
            content=combined_thought,
            additional_kwargs={"thought": combined_thought}
        ))

    # 使用解析的answer作为最终结果
    result_content = parsed.answer if parsed.answer else response_content
    # 清理掉 JSON 块，只保留对用户友好的文本
    result_content = _clean_message_content(result_content)
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
        # 如果解析到了 locations 但 parsed.answer 为空？或者没有locations？
        pass # 保持原逻辑，这里原逻辑是 else append 未能提取信息，但通常会有文本回复
        
        # 只有在真的没有任何有效回复时才报错，但通常 parsed.answer 会有内容
        if not result_content and not locations:
             final_messages.append(AIMessage(
                content="未能从响应中提取位置信息。",
                additional_kwargs={"message": "未能从响应中提取位置信息。"}
            ))
        
    yield {"messages": final_messages}


def _clean_message_content(content: str) -> str:
    """清理内容中的JSON代码块（仅用于显示给用户的文本）"""
    # 移除 ```json ... ``` 代码块
    clean_content = re.sub(r'```json\s*\{[^`]*?\}\s*```', '', content, flags=re.DOTALL)
    return clean_content


# ========== 构建工作流图 ==========
where_to_eat_workflow = StateGraph(AgentState)
where_to_eat_workflow.add_node("agent", where_to_eat_node)
where_to_eat_workflow.set_entry_point("agent")
where_to_eat_workflow.add_edge("agent", END)
where_to_eat_graph = where_to_eat_workflow.compile()
