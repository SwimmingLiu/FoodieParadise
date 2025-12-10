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
            
            # ===== 优先级1: 处理推理内容（专用字段） =====
            if hasattr(chunk, "additional_kwargs") and chunk.additional_kwargs:
                reasoning = chunk.additional_kwargs.get("reasoning_content", "")
                if reasoning:
                    await adispatch_custom_event("thought", {"content": reasoning}, config=config)
                    thought_content += reasoning
                    continue
            
            # ===== 优先级2: 处理 content_blocks =====
            has_content_blocks = False
            if hasattr(chunk, "content_blocks") and chunk.content_blocks:
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
                events = splitter.process_chunk(chunk_content)
                
                for event in events:
                    event_type = event["type"]
                    event_content = event["content"]
                    
                    if event_type == "thought":
                        await adispatch_custom_event("thought", {"content": event_content}, config=config)
                    elif event_type == "message":
                        clean_content = _clean_json_markers(event_content)
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
                clean_content = _clean_json_markers(event_content)
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
    combined_thought = thought_content + parsed.thought
    if combined_thought:
        final_messages.append(AIMessage(
            content=combined_thought,
            additional_kwargs={"thought": combined_thought}
        ))

    # 使用解析的answer作为最终结果
    result_content = parsed.answer if parsed.answer else response_content
    result_content = _clean_json_markers(result_content)
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
        final_messages.append(AIMessage(
            content="未能从响应中提取位置信息。",
            additional_kwargs={"message": "未能从响应中提取位置信息。"}
        ))
        
    yield {"messages": final_messages}


def _clean_json_markers(content: str) -> str:
    """清理内容中的JSON残留标记"""
    clean_content = re.sub(r'```json\s*\{[^`]*?\}\s*```', '', content)
    clean_content = re.sub(r'\s*"\s*\}\s*$', '', clean_content)
    clean_content = re.sub(r'^\s*"\s*\}\s*', '', clean_content)
    return clean_content


# ========== 构建工作流图 ==========
where_to_eat_workflow = StateGraph(AgentState)
where_to_eat_workflow.add_node("agent", where_to_eat_node)
where_to_eat_workflow.set_entry_point("agent")
where_to_eat_workflow.add_edge("agent", END)
where_to_eat_graph = where_to_eat_workflow.compile()
