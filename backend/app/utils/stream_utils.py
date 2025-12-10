"""流式响应工具模块

提供SSE格式化和LLM内容解析功能。
包含思考过程与最终答案的分割逻辑。
"""

import json
import asyncio
import re
from typing import AsyncGenerator, Any, Tuple, Optional
from dataclasses import dataclass


# ========== 内容解析相关数据结构 ==========

@dataclass
class ParsedContent:
    """LLM输出解析结果
    
    Attributes:
        thought: 思考过程内容（reason-content块）
        answer: 最终答案内容（answer块）
        raw_content: 未匹配到标记时的原始内容
    """
    thought: str = ""
    answer: str = ""
    raw_content: str = ""


class ContentSplitter:
    """LLM输出内容分割器
    
    根据提示词设计的格式（$$$ reason-content $$$ 和 $$$ answer $$$）
    将LLM输出分割为思考过程和最终答案两部分。
    """
    
    # 定义状态常量
    STATE_INITIAL = "initial"      # 初始状态
    STATE_THINKING = "thinking"    # 思考过程阶段
    STATE_ANSWER = "answer"        # 最终答案阶段
    
    # 定义标记正则表达式
    # 定义标记正则表达式
    # 匹配 @@@ reason-content @@@
    MARKER_REASON = re.compile(r'@@@\s*reason-content\s*@@@', re.IGNORECASE)
    # 匹配 @@@ answer @@@
    MARKER_ANSWER = re.compile(r'@@@\s*answer\s*@@@', re.IGNORECASE)
    
    def __init__(self):
        """初始化分割器状态"""
        self.reset()
    
    def reset(self):
        """重置分割器状态，用于新请求开始"""
        self.buffer = ""              # 累积缓冲区
        self.current_state = self.STATE_INITIAL
        self.thought_buffer = ""      # 思考过程累积
        self.answer_buffer = ""       # 答案累积
        self.pending_emit = []        # 待发射的事件队列
    
    def process_chunk(self, chunk: str) -> list:
        """处理单个流式chunk并返回待发射的事件列表"""
        events = []
        self.buffer += chunk
        
        while True:
            # 在当前缓冲区中寻找标记
            reason_match = self.MARKER_REASON.search(self.buffer)
            answer_match = self.MARKER_ANSWER.search(self.buffer)
            
            # 确定最早出现的标记
            first_match = None
            match_type = None
            
            if reason_match and answer_match:
                if reason_match.start() < answer_match.start():
                    first_match = reason_match
                    match_type = "reason"
                else:
                    first_match = answer_match
                    match_type = "answer"
            elif reason_match:
                first_match = reason_match
                match_type = "reason"
            elif answer_match:
                first_match = answer_match
                match_type = "answer"
            
            if not first_match:
                # 没有找到完整标记
                # 如果缓冲区过长，且不在等待标记完成（比如 marker 很长），则发射内容
                # 为了安全，这里只有在状态为 IN_THINKING 或 IN_ANSWER 时才发射内容
                # 初始化状态下的内容（marker之前）如果非空也应该是 message
                
                # 保留尾部以防截断了 marker (最长 marker 约 25 chars)
                keep_len = 30
                if len(self.buffer) > keep_len:
                    emit_content = self.buffer[:-keep_len]
                    self.buffer = self.buffer[-keep_len:]
                    
                    if emit_content:
                        if self.current_state == self.STATE_THINKING:
                            events.append({"type": "thought", "content": emit_content})
                            self.thought_buffer += emit_content
                        elif self.current_state == self.STATE_ANSWER:
                            events.append({"type": "message", "content": emit_content})
                            self.answer_buffer += emit_content
                        elif self.current_state == self.STATE_INITIAL:
                            # 初始状态下的杂音视为 message，或者直接丢弃？
                            # 通常是空行，或者 preamble。稳妥起见作为 message
                            if emit_content.strip():
                                events.append({"type": "message", "content": emit_content})
                break
            
            # 找到了标记 first_match
            # 1. 处理标记前的内容
            pre_content = self.buffer[:first_match.start()]
            if pre_content:
                if self.current_state == self.STATE_THINKING:
                    events.append({"type": "thought", "content": pre_content})
                    self.thought_buffer += pre_content
                elif self.current_state == self.STATE_ANSWER:
                    events.append({"type": "message", "content": pre_content})
                    self.answer_buffer += pre_content
                elif self.current_state == self.STATE_INITIAL:
                    if pre_content.strip():
                        events.append({"type": "message", "content": pre_content})
            
            # 2. 状态切换
            # 逻辑：遇到 marker 意味着状态翻转
            # reason marker: Initial -> Thinking, Thinking -> Initial/Idle
            # answer marker: Initial -> Answer, Answer -> Initial/Idle
            # 此外，如果 Thinking 中遇到 Answer marker，视为 Thinking 结束并直接开始 Answer
            
            if match_type == "reason":
                if self.current_state == self.STATE_THINKING:
                    # 结束思考
                    self.current_state = self.STATE_INITIAL
                else:
                    # 开始思考 (Initial -> Thinking 或 Answer -> Thinking)
                    if self.current_state == self.STATE_ANSWER:
                         # 异常情况：Answer 未闭合直接遇到 Reason
                         pass 
                    self.current_state = self.STATE_THINKING
                    
            elif match_type == "answer":
                if self.current_state == self.STATE_ANSWER:
                    # 结束回答
                    self.current_state = self.STATE_INITIAL
                else:
                    # 开始回答
                    self.current_state = self.STATE_ANSWER
            
            # 3. 移动缓冲区指针，跳过标记
            self.buffer = self.buffer[first_match.end():]
            
        return events
    
    def flush(self) -> list:
        """刷新缓冲区，返回剩余内容"""
        events = []
        if self.buffer:
            if self.current_state == self.STATE_THINKING:
                events.append({"type": "thought", "content": self.buffer})
                self.thought_buffer += self.buffer
            elif self.current_state == self.STATE_ANSWER:
                events.append({"type": "message", "content": self.buffer})
                self.answer_buffer += self.buffer
            else:
                if self.buffer.strip():
                    events.append({"type": "message", "content": self.buffer})
        
        self.buffer = ""
        self.current_state = self.STATE_INITIAL # Reset structure
        return events
    
    def get_parsed_content(self) -> ParsedContent:
        """获取解析后的完整内容"""
        # 清理 answer，移除可能存在的 JSON 代码块（用于结构化提取，不展示给用户）
        clean_answer = self.answer_buffer.strip()
        
        # 移除 ```json ... ``` 块
        clean_answer = re.sub(r'```json\s*\{.*?\}\s*```', '', clean_answer, flags=re.DOTALL)
        
        # 兼容性清理：有时候 JSON 没包裹好，或者有额外的残留
        clean_answer = clean_answer.strip()
        
        return ParsedContent(
            thought=self.thought_buffer.strip(),
            answer=clean_answer,
            raw_content=self.buffer # 注意：buffer在flush后为空，但这里语义略有变化，不再存raw
        )


def parse_llm_response(content: str) -> ParsedContent:
    """解析完整的LLM响应，分割思考过程和最终答案
    
    根据提示词设计的格式提取：
    - ``` reason-content ... ``` 块作为思考过程
    - ``` answer ... ``` 块作为最终答案
    
    Args:
        content: LLM完整响应文本
        
    Returns:
        ParsedContent: 解析结果
    """
    splitter = ContentSplitter()
    splitter.process_chunk(content)
    splitter.flush()
    return splitter.get_parsed_content()


def format_sse_data(content: str) -> str:
    """
    Format content for SSE data field, handling newlines properly.
    
    SSE specification requires each line of multi-line data to be prefixed with 'data:'.
    This function ensures newlines in content don't break the SSE format.
    
    Args:
        content: The content string to format
        
    Returns:
        Properly formatted data lines for SSE
    """
    if not content:
        return "data: \n"
    
    # Split by newlines and prefix each line with 'data: '
    lines = content.split('\n')
    formatted_lines = [f"data: {line}" for line in lines]
    return '\n'.join(formatted_lines) + '\n'


async def stream_generator(generator: AsyncGenerator[Any, None]) -> AsyncGenerator[str, None]:
    """
    Converts a LangGraph/LangChain stream into a custom SSE-like format for WeChat Mini Program.
    
    Format (SSE specification compliant):
    event: thought
    data: <content line 1>
    data: <content line 2>
    
    event: message
    data: <content>
    
    event: function_call
    data: <json_content>
    
    Note: Multi-line data is handled by prefixing each line with 'data:'
    """
    async for chunk in generator:
        # Handle different chunk types from LangGraph
        if isinstance(chunk, dict):
            if "thought" in chunk:
                # Format thought content with proper SSE data lines
                data_lines = format_sse_data(chunk['thought'])
                yield f"event: thought\n{data_lines}\n"
            elif "message" in chunk:
                # Format message content with proper SSE data lines
                data_lines = format_sse_data(chunk['message'])
                yield f"event: message\n{data_lines}\n"
            elif "function_call" in chunk:
                # JSON is typically single-line, but handle it safely
                json_str = json.dumps(chunk['function_call'], ensure_ascii=False)
                yield f"event: function_call\ndata: {json_str}\n\n"
        else:
            # Default to message if it's just a string
            data_lines = format_sse_data(str(chunk))
            yield f"event: message\n{data_lines}\n"

async def mock_stream_generator():
    """Mock generator for testing"""
    yield "event: thought\ndata: Thinking about the request...\n\n"
    await asyncio.sleep(0.5)
    yield "event: thought\ndata: Searching for restaurants...\n\n"
    await asyncio.sleep(0.5)
    yield "event: message\ndata: I found some great places!\n\n"
    await asyncio.sleep(0.5)
    yield 'event: function_call\ndata: {"action": "open_map", "lat": 30.2741, "lng": 120.1551}\n\n'
