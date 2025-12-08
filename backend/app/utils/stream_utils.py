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
    
    根据提示词设计的格式（``` reason-content 和 ``` answer）
    将LLM输出分割为思考过程和最终答案两部分。
    
    支持两种模式：
    1. 流式模式：逐chunk累积并实时检测状态切换
    2. 完整模式：解析完整响应文本
    """
    
    # 定义状态常量
    STATE_INITIAL = "initial"      # 初始状态
    STATE_THINKING = "thinking"    # 思考过程阶段
    STATE_ANSWER = "answer"        # 最终答案阶段
    STATE_OUTSIDE = "outside"      # 代码块外部
    
    # 定义标记正则表达式（匹配 prompts.py 中的 JSON 样式标记）
    # 匹配 {"reason-content":" 或 { "reason-content" : "（开始标记）
    REASON_START_PATTERN = re.compile(r'\{\s*"reason-content"\s*:\s*"', re.IGNORECASE)
    # 匹配 {"answer":" 或 { "answer" : "（开始标记，带 { 前缀）
    ANSWER_START_PATTERN = re.compile(r'\{\s*"answer"\s*:\s*"', re.IGNORECASE)
    # 匹配 "answer":" 作为 JSON 对象内部字段（不带 { 前缀，用于 reason-content 后直接跟 answer 的情况）
    ANSWER_INLINE_PATTERN = re.compile(r'[,}]?\s*"answer"\s*:\s*"', re.IGNORECASE)
    # 匹配 JSON 块结束标记 "}（注意：需要排除 json 代码块中的嵌套情况）
    BLOCK_END_PATTERN = re.compile(r'"\s*\}')
    
    def __init__(self):
        """初始化分割器状态"""
        self.reset()
    
    def reset(self):
        """重置分割器状态，用于新请求开始"""
        self.buffer = ""              # 累积缓冲区
        self.current_state = self.STATE_INITIAL
        self.thought_buffer = ""      # 思考过程累积
        self.answer_buffer = ""       # 答案累积
        self.block_content = ""       # 当前代码块内容
        self.pending_emit = []        # 待发射的事件队列
    
    def _find_json_block_end(self, text: str, skip_code_blocks: bool = False):
        """查找 JSON 块的结束标记 "}
        
        在 answer 块中，可能包含嵌套的 ```json ... ``` 代码块，
        需要跳过这些嵌套的代码块，找到真正的 JSON 块结束标记。
        
        Args:
            text: 要搜索的文本
            skip_code_blocks: 是否跳过代码块内的 "} 标记
            
        Returns:
            Match 对象或 None：找到的结束标记位置
        """
        if not skip_code_blocks:
            # 简单情况：直接查找第一个 "}
            return self.BLOCK_END_PATTERN.search(text)
        
        # 复杂情况：需要跳过 ```json ... ``` 代码块
        # 使用状态机遍历文本
        in_code_block = False
        i = 0
        while i < len(text):
            # 检查是否进入代码块
            if text[i:i+3] == "```":
                if not in_code_block:
                    in_code_block = True
                    i += 3
                    # 跳过代码块类型标识（如 json）
                    while i < len(text) and text[i] not in ('\n', '`'):
                        i += 1
                    continue
                else:
                    # 代码块结束
                    in_code_block = False
                    i += 3
                    continue
            
            # 如果不在代码块中，检查 "}
            if not in_code_block:
                # 检查是否是 "}（JSON 块结束标记）
                match = self.BLOCK_END_PATTERN.match(text, i)
                if match:
                    return match
            
            i += 1
        
        return None

    def process_chunk(self, chunk: str) -> list:
        """处理单个流式chunk并返回待发射的事件列表
        
        根据当前状态和chunk内容判断是否需要状态切换，
        并返回应该发射的事件（thought或message）。
        
        Args:
            chunk: 流式输入的文本片段
            
        Returns:
            list: 事件列表，格式为 [{"type": "thought"|"message", "content": str}]
        """
        events = []
        self.buffer += chunk
        
        # 逐字符/逐段处理以检测标记
        while True:
            if self.current_state == self.STATE_INITIAL:
                # 初始状态：寻找 reason-content 或 answer 开始标记
                reason_match = self.REASON_START_PATTERN.search(self.buffer)
                answer_match = self.ANSWER_START_PATTERN.search(self.buffer)
                
                if reason_match:
                    # 发现思考过程开始标记
                    # 标记前的内容作为普通消息输出
                    before = self.buffer[:reason_match.start()]
                    if before.strip():
                        events.append({"type": "message", "content": before})
                    
                    self.buffer = self.buffer[reason_match.end():]
                    self.current_state = self.STATE_THINKING
                    self.block_content = ""
                    continue
                
                elif answer_match:
                    # 发现答案开始标记
                    before = self.buffer[:answer_match.start()]
                    if before.strip():
                        events.append({"type": "thought", "content": before})
                    
                    self.buffer = self.buffer[answer_match.end():]
                    self.current_state = self.STATE_ANSWER
                    self.block_content = ""
                    continue
                
                else:
                    # 没有找到标记，但内容可能不完整
                    # 保留可能的部分标记（最后20个字符）避免截断
                    if len(self.buffer) > 20:
                        emit_content = self.buffer[:-20]
                        self.buffer = self.buffer[-20:]
                        if emit_content.strip():
                            # 初始状态的内容视为思考过程
                            events.append({"type": "thought", "content": emit_content})
                    break
            
            elif self.current_state == self.STATE_THINKING:
                # 思考阶段：寻找 JSON 块结束标记 "} 或 answer 开始标记
                # 同时检查带 { 前缀和不带 { 前缀的 answer 标记
                answer_match = self.ANSWER_START_PATTERN.search(self.buffer)
                answer_inline_match = self.ANSWER_INLINE_PATTERN.search(self.buffer)
                
                # 选择位置更靠前的 answer 匹配
                effective_answer_match = None
                if answer_match and answer_inline_match:
                    effective_answer_match = answer_match if answer_match.start() < answer_inline_match.start() else answer_inline_match
                elif answer_match:
                    effective_answer_match = answer_match
                elif answer_inline_match:
                    effective_answer_match = answer_inline_match
                
                # 查找 JSON 块结束标记 "}
                # 注意：需要找到最外层的 "}，而不是嵌套 JSON 中的
                end_match = self._find_json_block_end(self.buffer)
                
                if effective_answer_match and (end_match is None or effective_answer_match.start() < end_match.start()):
                    # 遇到 answer 标记，先发射当前思考内容，然后切换状态
                    content = self.buffer[:effective_answer_match.start()]
                    if content.strip():
                        events.append({"type": "thought", "content": content})
                        self.thought_buffer += content
                    
                    self.buffer = self.buffer[effective_answer_match.end():]
                    self.current_state = self.STATE_ANSWER
                    self.block_content = ""
                    continue

                
                elif end_match is not None:
                    # 找到思考块结束标记
                    content = self.buffer[:end_match.start()]
                    if content.strip():
                        events.append({"type": "thought", "content": content})
                        self.thought_buffer += content
                    
                    self.buffer = self.buffer[end_match.end():]
                    self.current_state = self.STATE_OUTSIDE
                    continue
                
                else:
                    # 没有找到结束标记，保留缓冲
                    if len(self.buffer) > 10:
                        emit_content = self.buffer[:-10]
                        self.buffer = self.buffer[-10:]
                        if emit_content:
                            events.append({"type": "thought", "content": emit_content})
                            self.thought_buffer += emit_content
                    break
            
            elif self.current_state == self.STATE_ANSWER:
                # 答案阶段：寻找 JSON 块结束标记 "}
                # 注意：answer 块中包含嵌套的 ```json ... ``` 代码块，需要跳过
                end_match = self._find_json_block_end(self.buffer, skip_code_blocks=True)
                
                if end_match is not None:
                    # 找到答案块结束标记
                    content = self.buffer[:end_match.start()]
                    if content.strip():
                        events.append({"type": "message", "content": content})
                        self.answer_buffer += content
                    
                    self.buffer = self.buffer[end_match.end():]
                    self.current_state = self.STATE_OUTSIDE
                    continue
                
                else:
                    # 没有找到结束标记，继续累积
                    if len(self.buffer) > 10:
                        emit_content = self.buffer[:-10]
                        self.buffer = self.buffer[-10:]
                        if emit_content:
                            events.append({"type": "message", "content": emit_content})
                            self.answer_buffer += emit_content
                    break
            
            elif self.current_state == self.STATE_OUTSIDE:
                # 代码块外部：寻找新的标记
                reason_match = self.REASON_START_PATTERN.search(self.buffer)
                answer_match = self.ANSWER_START_PATTERN.search(self.buffer)
                answer_inline_match = self.ANSWER_INLINE_PATTERN.search(self.buffer)
                
                # 选择位置更靠前的 answer 匹配
                effective_answer_match = None
                if answer_match and answer_inline_match:
                    effective_answer_match = answer_match if answer_match.start() < answer_inline_match.start() else answer_inline_match
                elif answer_match:
                    effective_answer_match = answer_match
                elif answer_inline_match:
                    effective_answer_match = answer_inline_match
                
                if reason_match:
                    before = self.buffer[:reason_match.start()]
                    if before.strip():
                        events.append({"type": "message", "content": before})
                    
                    self.buffer = self.buffer[reason_match.end():]
                    self.current_state = self.STATE_THINKING
                    continue
                
                elif effective_answer_match:
                    before = self.buffer[:effective_answer_match.start()]
                    if before.strip():
                        events.append({"type": "message", "content": before})
                    
                    self.buffer = self.buffer[effective_answer_match.end():]
                    self.current_state = self.STATE_ANSWER
                    continue
                
                else:
                    # 外部内容作为消息输出
                    if len(self.buffer) > 20:
                        emit_content = self.buffer[:-20]
                        self.buffer = self.buffer[-20:]
                        if emit_content.strip():
                            events.append({"type": "message", "content": emit_content})
                    break
            
            else:
                break
        
        return events
    
    def flush(self) -> list:
        """刷新缓冲区，返回剩余内容
        
        在流式传输结束时调用，处理缓冲区中剩余的内容。
        
        Returns:
            list: 剩余事件列表
        """
        events = []
        
        if self.buffer.strip():
            if self.current_state == self.STATE_THINKING:
                events.append({"type": "thought", "content": self.buffer})
                self.thought_buffer += self.buffer
            elif self.current_state == self.STATE_ANSWER:
                events.append({"type": "message", "content": self.buffer})
                self.answer_buffer += self.buffer
            else:
                # 初始或外部状态，根据内容判断
                events.append({"type": "message", "content": self.buffer})
        
        self.buffer = ""
        return events
    
    def get_parsed_content(self) -> ParsedContent:
        """获取解析后的完整内容
        
        Returns:
            ParsedContent: 包含思考过程和答案的解析结果
        """
        # 清理 answer 中的 JSON 残留标记
        clean_answer = self.answer_buffer.strip()
        # 移除 JSON 代码块
        clean_answer = re.sub(r'```json\s*\{[^`]*?\}\s*```', '', clean_answer)
        # 移除 JSON 样式块的残留结束标记 "}
        clean_answer = re.sub(r'\s*"\s*\}\s*$', '', clean_answer)
        clean_answer = re.sub(r'^\s*"\s*\}\s*', '', clean_answer)
        clean_answer = clean_answer.strip()
        
        return ParsedContent(
            thought=self.thought_buffer.strip(),
            answer=clean_answer,
            raw_content=self.buffer
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
