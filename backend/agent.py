from typing import TypedDict, Annotated, List, Union, Dict, Any
from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import tool
import operator
import json
import asyncio

# Define State
class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]
    image_path: str

# Define Tools
@tool
def search_location(query: str):
    """Search for a location's coordinates and address based on a query."""
    # Mock implementation for now
    print(f"Searching for: {query}")
    # In a real scenario, this would call a Map API (AMap/Baidu/Google)
    # Simulating a search result
    if "杭州" in query or "Hangzhou" in query:
        return json.dumps({
            "name": "West Lake (Xi Hu)",
            "address": "Hangzhou, Zhejiang, China",
            "lat": 30.2458,
            "lng": 120.1551
        })
    return json.dumps({
        "name": "Unknown Location",
        "address": "Unknown",
        "lat": 0.0,
        "lng": 0.0
    })

# Define Nodes
async def agent_node(state: AgentState):
    messages = state["messages"]
    image_path = state.get("image_path")
    
    # Here we would normally call a VLM (Vision Language Model) like GPT-4o or Gemini Pro Vision
    # For this demo, we'll simulate the VLM's reasoning and decision making.
    
    last_message = messages[-1]
    
    # Simple heuristic simulation of an agent
    if isinstance(last_message, HumanMessage):
        # First turn: Analyze image and decide to search
        return {
            "messages": [
                AIMessage(content="I see a delicious looking dish. Let me try to identify the restaurant based on the visual cues.", 
                          additional_kwargs={"thought": "Analyzing image features... It looks like Dongpo Pork from a restaurant in Hangzhou."}),
                AIMessage(content="", tool_calls=[{"name": "search_location", "args": {"query": "Hangzhou Dongpo Pork Restaurant"}, "id": "call_1"}])
            ]
        }
    
    # Handle tool output
    # Note: In a real LangGraph with ToolNode, this would be handled differently.
    # We are manually simulating the loop here for simplicity in this skeleton.
    return {"messages": []}

async def tools_node(state: AgentState):
    messages = state["messages"]
    last_message = messages[-1]
    
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        tool_call = last_message.tool_calls[0]
        if tool_call["name"] == "search_location":
            result = search_location.invoke(tool_call["args"])
            
            # Parse result to see if we found a location
            data = json.loads(result)
            
            # Construct function call event for frontend
            # In LangGraph, we usually return a ToolMessage. 
            # But for our custom streaming to frontend, we might want to emit a specific event.
            # The stream_utils will handle the emission if we return the right structure or if we yield it.
            
            return {
                "messages": [
                    # ToolMessage(content=result, tool_call_id=tool_call["id"]), # Standard LangChain
                    AIMessage(content=f"I found the location: {data['name']}", 
                              additional_kwargs={"function_call": {"action": "open_map", "lat": data["lat"], "lng": data["lng"], "name": data["name"], "address": data["address"]}})
                ]
            }
    return {"messages": []}

# Define Graph
workflow = StateGraph(AgentState)

workflow.add_node("agent", agent_node)
workflow.add_node("tools", tools_node)

workflow.set_entry_point("agent")

def should_continue(state: AgentState):
    messages = state["messages"]
    last_message = messages[-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    return END

workflow.add_conditional_edges("agent", should_continue)
workflow.add_edge("tools", END) # End after one tool call for simplicity in this demo

app_graph = workflow.compile()
