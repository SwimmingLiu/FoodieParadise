from fastapi import APIRouter, UploadFile, File
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage
import shutil
import os
import logging
import sys

# 配置 logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

from app.models.schemas import ChatRequest, HistoryRecord
from app.services.agent_service import app_graph, where_to_eat_graph, premade_graph, calories_graph
from app.utils.stream_utils import stream_generator
from app.repositories.history_repo import save_history

router = APIRouter()

from app.services.oss_service import QiniuService

oss_service = QiniuService()

@router.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    # Save to temp file first
    temp_file_path = f"/tmp/{file.filename}"
    with open(temp_file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    try:
        # Upload to OSS
        file_url = oss_service.upload_file(temp_file_path, file.filename)
        return {"file_path": file_url}
    finally:
        # Clean up temp file
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

@router.post("/api/where-to-eat")
async def where_to_eat(request: ChatRequest):
    inputs = {
        "messages": [HumanMessage(content=request.query or "Where is this?")],
        "image_path": request.file_path
    }

    async def agent_stream():
        logger.info(f"[CONTROLLER] Starting agent_stream with inputs: {inputs}")
        # Use astream_events to capture custom thought events and node outputs
        async for event in where_to_eat_graph.astream_events(inputs, version="v2"):
            kind = event["event"]
            name = event["name"]
            
            # 1. Capture custom "thought" events dispatched from the node
            if kind == "on_custom_event" and name == "thought":
                data = event["data"]
                if "content" in data:
                     logger.info(f"[CONTROLLER] Yielding thought: {data['content'][:20]}...")
                     yield {"thought": data["content"]}
            
            # 2. Capture the final output of the "agent" node to get function_call/results
            elif kind == "on_chain_end" and name == "agent":
                data = event["data"]
                output = data.get("output")
                if output and "messages" in output:
                    messages = output["messages"]
                    logger.info(f"[CONTROLLER] Node 'agent' finished. Messages: {len(messages)}")
                    for msg in messages:
                        if isinstance(msg, HumanMessage): continue
                        
                        # We already streamed "thought", so we skip it here usually,
                        # unless we want to send the full thought block again (which we don't).
                        
                        if "function_call" in msg.additional_kwargs:
                            logger.info("[CONTROLLER] Yielding function_call")
                            yield {"function_call": msg.additional_kwargs["function_call"]}
                            
                        if "message" in msg.additional_kwargs:
                            # This is the "Result" text or Error text
                            logger.info("[CONTROLLER] Yielding message")
                            yield {"message": msg.additional_kwargs["message"]}
                        elif msg.content and "thought" not in msg.additional_kwargs:
                            # Generic content that isn't thought
                            logger.info("[CONTROLLER] Yielding message from content")
                            yield {"message": msg.content}

    return StreamingResponse(stream_generator(agent_stream()), media_type="text/event-stream")

@router.post("/api/check-premade")
async def check_premade(request: ChatRequest):
    inputs = {
        "messages": [HumanMessage(content="Analyze this food")],
        "image_path": request.file_path
    }
    
    async def agent_stream():
        async for output in premade_graph.astream(inputs, stream_mode="updates"):
            for node_name, state_update in output.items():
                if "messages" in state_update:
                    messages = state_update["messages"]
                    for msg in messages:
                        if isinstance(msg, HumanMessage): continue
                        if "thought" in msg.additional_kwargs:
                            yield {"thought": msg.additional_kwargs["thought"]}
                        if "message" in msg.additional_kwargs:
                            yield {"message": msg.additional_kwargs["message"]}
                        elif msg.content:
                             yield {"message": msg.content}

    return StreamingResponse(stream_generator(agent_stream()), media_type="text/event-stream")

@router.post("/api/calories")
async def calories(request: ChatRequest):
    inputs = {
        "messages": [HumanMessage(content="Analyze calories")],
        "image_path": request.file_path
    }
    
    async def agent_stream():
        async for output in calories_graph.astream(inputs, stream_mode="updates"):
            for node_name, state_update in output.items():
                if "messages" in state_update:
                    messages = state_update["messages"]
                    for msg in messages:
                        if isinstance(msg, HumanMessage): continue
                        if "thought" in msg.additional_kwargs:
                            yield {"thought": msg.additional_kwargs["thought"]}
                        if "function_call" in msg.additional_kwargs:
                            yield {"function_call": msg.additional_kwargs["function_call"]}
                        if "message" in msg.additional_kwargs:
                            yield {"message": msg.additional_kwargs["message"]}
                        elif msg.content:
                             yield {"message": msg.content}

    return StreamingResponse(stream_generator(agent_stream()), media_type="text/event-stream")

@router.get("/api/history")
async def get_history():
    from app.repositories.history_repo import get_user_history
    return get_user_history()

@router.post("/api/history")
async def add_history(record: HistoryRecord):
    save_history(record.dict())
    return {"status": "ok"}
