import json
import asyncio
from typing import AsyncGenerator, Any

async def stream_generator(generator: AsyncGenerator[Any, None]) -> AsyncGenerator[str, None]:
    """
    Converts a LangGraph/LangChain stream into a custom SSE-like format for WeChat Mini Program.
    
    Format:
    event: thought
    data: <content>
    
    event: message
    data: <content>
    
    event: function_call
    data: <json_content>
    """
    async for chunk in generator:
        # This part needs to be adapted based on the actual output structure of LangGraph
        # For now, we assume a generic structure and will refine it later.
        
        # Example handling (needs adjustment based on actual LangGraph events):
        if isinstance(chunk, dict):
            if "thought" in chunk:
                 yield f"event: thought\ndata: {chunk['thought']}\n\n"
            elif "message" in chunk:
                 yield f"event: message\ndata: {chunk['message']}\n\n"
            elif "function_call" in chunk:
                 yield f"event: function_call\ndata: {json.dumps(chunk['function_call'])}\n\n"
        else:
            # Default to message if it's just a string
            yield f"event: message\ndata: {str(chunk)}\n\n"

async def mock_stream_generator():
    """Mock generator for testing"""
    yield "event: thought\ndata: Thinking about the request...\n\n"
    await asyncio.sleep(0.5)
    yield "event: thought\ndata: Searching for restaurants...\n\n"
    await asyncio.sleep(0.5)
    yield "event: message\ndata: I found some great places!\n\n"
    await asyncio.sleep(0.5)
    yield 'event: function_call\ndata: {"action": "open_map", "lat": 30.2741, "lng": 120.1551}\n\n'
