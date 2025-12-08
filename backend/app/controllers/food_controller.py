"""
Food控制器模块

处理所有与食物相关的API请求路由。
包括文件上传、去哪吃、查预制、吃多少三个功能的流式响应接口。
"""

from fastapi import APIRouter, UploadFile, File
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage
import shutil
import os
import logging
import sys

# ========== 日志配置 ==========
# 配置日志输出到标准输出，方便调试和监控
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# ========== 导入业务模块 ==========
from app.models.schemas import ChatRequest, CaloriesRequest, HistoryRecord
from app.services.agent_service import where_to_eat_graph, premade_graph, calories_graph
from app.utils.stream_utils import stream_generator
from app.repositories.history_repo import save_history
from app.services.oss_service import QiniuService

# 创建API路由器
router = APIRouter()

# 初始化OSS服务
oss_service = QiniuService()


@router.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """文件上传接口
    
    接收用户上传的文件，保存到临时目录后上传至七牛云OSS。
    上传成功后返回文件的公开访问URL。
    
    Args:
        file: 上传的文件对象
        
    Returns:
        dict: 包含文件URL的字典 {"file_path": "https://..."}
    """
    # 先保存到临时文件
    temp_file_path = f"/tmp/{file.filename}"
    with open(temp_file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    try:
        # 上传到OSS
        file_url = oss_service.upload_file(temp_file_path, file.filename)
        return {"file_path": file_url}
    finally:
        # 清理临时文件
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

@router.post("/api/where-to-eat")
async def where_to_eat(request: ChatRequest):
    """去哪吃功能接口
    
    接收用户上传的图片和问题，使用AI识别图片中的餐厅位置。
    返回流式响应，包括思考过程（thought）和最终的位置信息（message）。
    
    LLM输出分割逻辑：
    - ``` reason-content ``` 块内容作为 thought 事件发送
    - ``` answer ``` 块内容作为 message 事件发送
    
    Args:
        request: 包含图片路径和用户问题的请求对象
        
    Returns:
        StreamingResponse: SSE流式响应
    """
    # 构建Agent输入
    inputs = {
        "messages": [HumanMessage(content=request.query or "这是哪里？")],
        "image_path": request.file_path
    }

    async def agent_stream():
        """处理Agent流式输出的生成器函数
        
        捕获两类事件：
        1. custom_event: 思考过程(thought)和消息内容(message)
        2. chain_end: 节点完成后的最终结果，包含function_call
        """
        logger.info(f"[CONTROLLER] 开始处理去哪吃请求: {inputs}")
        
        # 使用astream_events捕获自定义事件和节点输出
        async for event in where_to_eat_graph.astream_events(inputs, version="v2"):
            kind = event["event"]
            name = event["name"]
            
            # 1. 捕获思考过程事件（从reason-content块解析）
            if kind == "on_custom_event" and name == "thought":
                data = event["data"]
                if "content" in data:
                    logger.info(f"[CONTROLLER] 发送思考过程: {data['content'][:30]}...")
                    yield {"thought": data["content"]}
            
            # 2. 捕获消息内容事件（从answer块解析）
            elif kind == "on_custom_event" and name == "message":
                data = event["data"]
                if "content" in data:
                    logger.info(f"[CONTROLLER] 发送答案内容: {data['content'][:30]}...")
                    yield {"message": data["content"]}
            
            # 3. 捕获"agent"节点的最终输出，获取function_call/结果
            elif kind == "on_chain_end" and name == "agent":
                data = event["data"]
                output = data.get("output")
                if output and "messages" in output:
                    messages = output["messages"]
                    logger.info(f"[CONTROLLER] Agent节点完成，消息数: {len(messages)}")
                    for msg in messages:
                        # 跳过用户消息
                        if isinstance(msg, HumanMessage):
                            continue
                        
                        # 发送地图功能调用
                        if "function_call" in msg.additional_kwargs:
                            logger.info("[CONTROLLER] 发送地图调用")
                            yield {"function_call": msg.additional_kwargs["function_call"]}

    return StreamingResponse(stream_generator(agent_stream()), media_type="text/event-stream")

@router.post("/api/check-premade")
async def check_premade(request: ChatRequest):
    """查预制功能接口
    
    接收用户上传的菜品图片，使用AI分析是否为预制菜。
    返回流式响应，包括分析过程（thought）和分析结论（message）。
    
    LLM输出分割逻辑：
    - ``` reason-content ``` 块内容作为 thought 事件发送
    - ``` answer ``` 块内容作为 message 事件发送
    
    Args:
        request: 包含图片路径的请求对象
        
    Returns:
        StreamingResponse: SSE流式响应
    """
    # 构建Agent输入
    inputs = {
        "messages": [HumanMessage(content="分析这道菜是否为预制菜")],
        "image_path": request.file_path
    }
    
    async def agent_stream():
        """处理Agent流式输出的生成器函数
        
        捕获两类事件：
        1. custom_event: 分析过程(thought)和分析结论(message)
        2. chain_end: 节点完成后的最终结果
        """
        logger.info(f"[CONTROLLER] 开始处理查预制请求: {inputs}")
        
        # 使用astream_events捕获自定义事件
        async for event in premade_graph.astream_events(inputs, version="v2"):
            kind = event["event"]
            name = event["name"]
            
            # 1. 捕获分析过程事件（从reason-content块解析）
            if kind == "on_custom_event" and name == "thought":
                data = event["data"]
                if "content" in data:
                    logger.info(f"[CONTROLLER] 发送分析过程: {data['content'][:30]}...")
                    yield {"thought": data["content"]}
            
            # 2. 捕获分析结论事件（从answer块解析）
            elif kind == "on_custom_event" and name == "message":
                data = event["data"]
                if "content" in data:
                    logger.info(f"[CONTROLLER] 发送分析结论: {data['content'][:30]}...")
                    yield {"message": data["content"]}
            
            # 3. 捕获"agent"节点的最终输出
            elif kind == "on_chain_end" and name == "agent":
                data = event["data"]
                output = data.get("output")
                if output and "messages" in output:
                    messages = output["messages"]
                    logger.info(f"[CONTROLLER] Agent节点完成，消息数: {len(messages)}")

    return StreamingResponse(stream_generator(agent_stream()), media_type="text/event-stream")

@router.post("/api/calories")
async def calories(request: CaloriesRequest):
    """吃多少功能接口
    
    接收用户上传的食物图片和用餐时间，使用AI并发分析食物热量。
    返回流式响应，包括思考过程、热量报告和食物卡片信息。
    
    工作流节点：
    - 食物识别节点：识别图片中的所有食物
    - 热量估算节点：估算每种食物的热量
    - 运动消耗节点：计算消耗热量所需的运动量
    - 聚合节点：汇总结果并生成最终报告
    
    Args:
        request: 包含图片路径和用餐时间的请求对象
        
    Returns:
        StreamingResponse: SSE流式响应
    """
    # 构建Agent输入
    inputs = {
        "messages": [HumanMessage(content="分析热量")],
        "image_path": request.file_path,
        "meal_time": request.meal_time or "午餐"
    }
    
    async def agent_stream():
        """处理Agent流式输出的生成器函数
        
        捕获并发工作流的各类事件：
        1. thought: 分析过程
        2. message: 分析结果
        3. function_call: 食物卡片数据
        """
        logger.info(f"[CONTROLLER] 开始处理吃多少请求: {inputs}")
        
        # 使用astream_events捕获自定义事件
        async for event in calories_graph.astream_events(inputs, version="v2"):
            kind = event["event"]
            name = event["name"]
            
            # 1. 捕获思考过程事件
            if kind == "on_custom_event" and name == "thought":
                data = event["data"]
                if "content" in data:
                    logger.info(f"[CONTROLLER] 发送分析过程: {data['content'][:30]}...")
                    yield {"thought": data["content"]}
            
            # 2. 捕获消息内容事件
            elif kind == "on_custom_event" and name == "message":
                data = event["data"]
                if "content" in data:
                    logger.info(f"[CONTROLLER] 发送分析结果: {data['content'][:30]}...")
                    yield {"message": data["content"]}
            
            # 3. 捕获function_call事件（食物卡片数据）
            elif kind == "on_custom_event" and name == "function_call":
                data = event["data"]
                if "content" in data:
                    import json
                    try:
                        func_data = json.loads(data["content"])
                        logger.info(f"[CONTROLLER] 发送食物卡片数据")
                        yield {"function_call": func_data}
                    except:
                        yield {"function_call": data["content"]}
            
            # 4. 捕获聚合节点的最终输出
            elif kind == "on_chain_end" and name == "aggregator":
                data = event["data"]
                output = data.get("output")
                if output and "messages" in output:
                    messages = output["messages"]
                    logger.info(f"[CONTROLLER] 聚合节点完成，消息数: {len(messages)}")

    return StreamingResponse(stream_generator(agent_stream()), media_type="text/event-stream")

@router.get("/api/history")
async def get_history():
    """获取历史记录接口
    
    返回用户的所有历史记录。
    
    Returns:
        list: 历史记录列表
    """
    from app.repositories.history_repo import get_user_history
    return get_user_history()


@router.post("/api/history")
async def add_history(record: HistoryRecord):
    """添加历史记录接口
    
    保存一条新的历史记录到数据库。
    
    Args:
        record: 历史记录对象
        
    Returns:
        dict: 操作状态 {"status": "ok"}
    """
    save_history(record.dict())
    return {"status": "ok"}
