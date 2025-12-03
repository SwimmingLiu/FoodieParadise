from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import uvicorn
import os
import shutil
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage

from agent import app_graph
from stream_utils import stream_generator

load_dotenv()

app = FastAPI(title="FoodieParadise Backend")

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify the frontend origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.get("/")
async def root():
    return {"message": "Welcome to FoodieParadise API"}

from pydantic import BaseModel

class ChatRequest(BaseModel):
    file_path: str
    query: str = None

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return {"file_path": file_path}

@app.post("/api/where-to-eat")
async def where_to_eat(request: ChatRequest):
    # Initialize agent input
    inputs = {
        "messages": [HumanMessage(content=request.query or "Where is this?")],
        "image_path": request.file_path
    }
    
    # Create a generator for the agent execution
    async def agent_stream():
        async for output in app_graph.astream(inputs, stream_mode="updates"):
            # output is a dict with node name as key and state update as value
            for node_name, state_update in output.items():
                if "messages" in state_update:
                    messages = state_update["messages"]
                    for msg in messages:
                        if isinstance(msg, HumanMessage):
                            continue
                        
                        # Check for thoughts
                        if "thought" in msg.additional_kwargs:
                            yield {"thought": msg.additional_kwargs["thought"]}
                        
                        # Check for tool calls (function_call in our custom protocol)
                        if "function_call" in msg.additional_kwargs:
                            yield {"function_call": msg.additional_kwargs["function_call"]}
                            
                        # Check for content (message)
                        if msg.content:
                            yield {"message": msg.content}

    return StreamingResponse(stream_generator(agent_stream()), media_type="text/event-stream")

from agent import premade_graph

@app.post("/api/check-premade")
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

from agent import calories_graph

@app.post("/api/calories")
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

from history import get_user_history, save_history

@app.get("/api/history")
async def get_history():
    return get_user_history()

# We should also call save_history in the other endpoints when analysis is done.
# But since they are streaming, it's a bit tricky to capture the full result at the end of the stream in the main handler.
# A middleware or a callback in the stream generator could work.
# For simplicity, we might skip saving automatically for now, or add a separate "save" endpoint if the frontend wants to save.
# Let's add a save endpoint for the frontend to call after receiving the result.

class HistoryRecord(BaseModel):
    type: str # 'where-to-eat', 'check-premade', 'calories'
    image_path: str
    summary: str
    details: Dict[str, Any] = {}

@app.post("/api/history")
async def add_history(record: HistoryRecord):
    save_history(record.dict())
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
