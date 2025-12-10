"""
食物业务服务模块

封装与食物相关的业务逻辑，包括：
- 去哪吃功能的流式响应处理
- 查预制功能的流式响应处理
- 吃多少功能的流式响应处理

将业务逻辑从 Controller 层分离，遵循 FastAPI 分层架构最佳实践。
"""

import json
import logging
from typing import AsyncGenerator, Dict, Any

from langchain_core.messages import HumanMessage

from app.services.agents import where_to_eat_graph, premade_graph, calories_graph

logger = logging.getLogger(__name__)


class FoodService:
    """食物相关业务逻辑服务
    
    封装三个核心功能的流式响应生成逻辑，供 Controller 调用。
    每个方法都是一个异步生成器，产生 SSE 格式的事件数据。
    """
    
    async def process_where_to_eat_stream(
        self,
        file_path: str,
        query: str = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """处理'去哪吃'功能的流式响应
        
        接收图片路径和用户问题，调用 Agent 工作流进行位置识别，
        并将结果以流式事件的形式返回。
        
        Args:
            file_path: 图片文件路径或URL
            query: 用户问题，默认为"这是哪里？"
            
        Yields:
            Dict: 事件数据字典，包含以下类型：
                - {"thought": str}: 思考过程
                - {"message": str}: 消息内容
                - {"function_call": dict}: 地图功能调用
        """
        inputs = {
            "messages": [HumanMessage(content=query or "这是哪里？")],
            "image_path": file_path
        }
        
        logger.info(f"[SERVICE] 开始处理去哪吃请求: {inputs}")
        
        async for event in where_to_eat_graph.astream_events(inputs, version="v2"):
            kind = event["event"]
            name = event["name"]
            
            # 1. 捕获思考过程事件
            if kind == "on_custom_event" and name == "thought":
                data = event["data"]
                if "content" in data:
                    logger.info(f"[SERVICE] 发送思考过程: {data['content'][:30]}...")
                    yield {"thought": data["content"]}
            
            # 2. 捕获消息内容事件
            elif kind == "on_custom_event" and name == "message":
                data = event["data"]
                if "content" in data:
                    logger.info(f"[SERVICE] 发送答案内容: {data['content'][:30]}...")
                    yield {"message": data["content"]}
            
            # 3. 捕获 Agent 节点的最终输出
            elif kind == "on_chain_end" and name == "agent":
                data = event["data"]
                output = data.get("output")
                if output and "messages" in output:
                    messages = output["messages"]
                    logger.info(f"[SERVICE] Agent节点完成，消息数: {len(messages)}")
                    for msg in messages:
                        if isinstance(msg, HumanMessage):
                            continue
                        if "function_call" in msg.additional_kwargs:
                            logger.info("[SERVICE] 发送地图调用")
                            yield {"function_call": msg.additional_kwargs["function_call"]}
    
    async def process_check_premade_stream(
        self,
        file_path: str
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """处理'查预制'功能的流式响应
        
        接收菜品图片路径，调用 Agent 工作流进行预制菜分析，
        并将结果以流式事件的形式返回。
        
        Args:
            file_path: 图片文件路径或URL
            
        Yields:
            Dict: 事件数据字典，包含以下类型：
                - {"thought": str}: 分析过程
                - {"message": str}: 分析结论
        """
        inputs = {
            "messages": [HumanMessage(content="分析这道菜是否为预制菜")],
            "image_path": file_path
        }
        
        logger.info(f"[SERVICE] 开始处理查预制请求: {inputs}")
        
        async for event in premade_graph.astream_events(inputs, version="v2"):
            kind = event["event"]
            name = event["name"]
            
            # 1. 捕获分析过程事件
            if kind == "on_custom_event" and name == "thought":
                data = event["data"]
                if "content" in data:
                    logger.info(f"[SERVICE] 发送分析过程: {data['content'][:30]}...")
                    yield {"thought": data["content"]}
            
            # 2. 捕获分析结论事件
            elif kind == "on_custom_event" and name == "message":
                data = event["data"]
                if "content" in data:
                    logger.info(f"[SERVICE] 发送分析结论: {data['content'][:30]}...")
                    yield {"message": data["content"]}
            
            # 3. 捕获 Agent 节点的最终输出
            elif kind == "on_chain_end" and name == "agent":
                data = event["data"]
                output = data.get("output")
                if output and "messages" in output:
                    messages = output["messages"]
                    logger.info(f"[SERVICE] Agent节点完成，消息数: {len(messages)}")
    
    async def process_calories_stream(
        self,
        file_path: str,
        meal_time: str = "午餐"
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """处理'吃多少'功能的流式响应
        
        接收食物图片路径和用餐时间，调用 Agent 工作流进行热量分析，
        并将结果以流式事件的形式返回。
        
        Args:
            file_path: 图片文件路径或URL
            meal_time: 用餐时间，默认为"午餐"
            
        Yields:
            Dict: 事件数据字典，包含以下类型：
                - {"thought": str}: 分析过程
                - {"message": str}: 分析结果
                - {"function_call": dict}: 食物卡片数据
        """
        inputs = {
            "messages": [HumanMessage(content="分析热量")],
            "image_path": file_path,
            "meal_time": meal_time
        }
        
        logger.info(f"[SERVICE] 开始处理吃多少请求: {inputs}")
        
        async for event in calories_graph.astream_events(inputs, version="v2"):
            kind = event["event"]
            name = event["name"]
            
            # 1. 捕获思考过程事件
            if kind == "on_custom_event" and name == "thought":
                data = event["data"]
                if "content" in data:
                    logger.info(f"[SERVICE] 发送分析过程: {data['content'][:30]}...")
                    yield {"thought": data["content"]}
            
            # 2. 捕获消息内容事件
            elif kind == "on_custom_event" and name == "message":
                data = event["data"]
                if "content" in data:
                    logger.info(f"[SERVICE] 发送分析结果: {data['content'][:30]}...")
                    yield {"message": data["content"]}
            
            # 3. 捕获 function_call 事件
            elif kind == "on_custom_event" and name == "function_call":
                data = event["data"]
                if "content" in data:
                    try:
                        func_data = json.loads(data["content"])
                        logger.info("[SERVICE] 发送食物卡片数据")
                        yield {"function_call": func_data}
                    except json.JSONDecodeError:
                        yield {"function_call": data["content"]}
            
            # 4. 捕获聚合节点的最终输出
            elif kind == "on_chain_end" and name == "aggregator":
                data = event["data"]
                output = data.get("output")
                if output and "messages" in output:
                    messages = output["messages"]
                    logger.info(f"[SERVICE] 聚合节点完成，消息数: {len(messages)}")


# 默认服务实例，供 Controller 使用
food_service = FoodService()
