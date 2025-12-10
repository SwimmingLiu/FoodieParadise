"""
LLM调用工具模块

提供LLM模型创建、消息构建、流式调用等公共函数。
封装与LangChain/OpenAI交互的通用逻辑，供各Agent节点复用。
"""

import re
from typing import List, Dict, Any, AsyncGenerator

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.callbacks.manager import adispatch_custom_event
from langchain_openai import ChatOpenAI

from app.config import settings
from app.utils.stream_utils import ContentSplitter


def create_chat_model(
    model: str = None,
    timeout: float = None,
    max_retries: int = None
) -> ChatOpenAI:
    """创建配置了超时和重试的 ChatOpenAI 实例
    
    统一管理 LLM 客户端的创建，确保所有调用都具有一致的错误处理配置。
    使用此工厂函数而非直接创建 ChatOpenAI 实例，可以自动获得：
    - 超时保护：防止请求长时间挂起
    - 自动重试：处理临时性网络故障
    
    Args:
        model: 模型名称，默认使用配置文件中的 default_model
        timeout: 请求超时时间（秒），默认使用配置文件中的 request_timeout
        max_retries: 最大重试次数，默认使用配置文件中的 max_retries
        
    Returns:
        ChatOpenAI: 配置好的聊天模型实例
    """
    llm_config = settings.llm
    
    return ChatOpenAI(
        model=model or llm_config.default_model,
        base_url=llm_config.openai_api_base,
        api_key=llm_config.openai_api_key,
        timeout=timeout or llm_config.request_timeout,
        max_retries=max_retries or llm_config.max_retries
    )


def build_vision_messages(
    system_prompt: str,
    user_text: str,
    image_url: str
) -> List[Dict[str, Any]]:
    """构建带图片的消息列表
    
    创建包含系统提示词和用户消息（文本+图片）的标准消息格式。
    
    Args:
        system_prompt: 系统提示词内容
        user_text: 用户问题或指令文本
        image_url: Base64编码的图片数据URL
        
    Returns:
        List: 包含SystemMessage和HumanMessage的消息列表
    """
    return [
        SystemMessage(content=system_prompt),
        HumanMessage(content=[
            {"type": "text", "text": user_text},
            {"type": "image_url", "image_url": {"url": image_url}}
        ])
    ]


async def stream_llm_with_events(
    model: ChatOpenAI,
    messages: List,
    config: RunnableConfig,
    use_splitter: bool = True
) -> AsyncGenerator[Dict[str, str], None]:
    """流式调用LLM并派发自定义事件
    
    封装LLM的流式调用逻辑，处理以下内容：
    1. 推理模型的reasoning_content（作为thought事件）
    2. 结构化的content_blocks
    3. 普通的content字段
    
    如果启用splitter，会使用ContentSplitter解析输出中的
    reason-content和answer块，分别派发为thought和message事件。
    
    Args:
        model: ChatOpenAI模型实例
        messages: 消息列表
        config: LangChain运行配置，用于事件派发
        use_splitter: 是否使用ContentSplitter进行内容分流
        
    Yields:
        Dict[str, str]: 事件字典，包含type和content字段
    """
    splitter = ContentSplitter() if use_splitter else None
    response_content = ""
    thought_content = ""
    
    async for chunk in model.astream(messages, config=config):
        chunk_content = ""
        
        # ===== 优先级1: 处理推理内容（专用字段） =====
        if hasattr(chunk, "additional_kwargs") and chunk.additional_kwargs:
            reasoning = chunk.additional_kwargs.get("reasoning_content", "")
            if reasoning:
                await adispatch_custom_event("thought", {"content": reasoning}, config=config)
                thought_content += reasoning
                continue
        
        # ===== 优先级2: 处理 content_blocks（结构化输出） =====
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
            
            if splitter:
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
            else:
                # 不使用splitter，直接作为message发送
                await adispatch_custom_event("message", {"content": chunk_content}, config=config)
    
    # ===== 刷新缓冲区 =====
    if splitter:
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
    
    # 返回完整响应和思考内容供后续处理
    yield {"response_content": response_content, "thought_content": thought_content}


def _clean_json_markers(content: str) -> str:
    """清理内容中的JSON残留标记
    
    移除LLM输出中可能残留的JSON代码块标记和格式字符。
    
    Args:
        content: 待清理的内容
        
    Returns:
        str: 清理后的内容
    """
    clean_content = re.sub(r'```json\s*\{[^`]*?\}\s*```', '', content)
    clean_content = re.sub(r'\s*"\s*\}\s*$', '', clean_content)
    clean_content = re.sub(r'^\s*"\s*\}\s*', '', clean_content)
    return clean_content
