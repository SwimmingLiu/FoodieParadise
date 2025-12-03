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

# ... (Previous imports and code)

# Define Tools for Check Pre-made
@tool
def analyze_premade(image_path: str):
    """Analyze if the food in the image is pre-made."""
    # Mock analysis
    return json.dumps({
        "dish_name": "Braised Pork Rice",
        "is_premade": True,
        "score": 85, # 85% probability of being pre-made
        "freshness": "Semi-premade",
        "confidence": 0.9,
        "reasons": [
            "Uniform shape of meat cuts suggests industrial processing.",
            "Sauce consistency is too perfect/gelatinous.",
            "Vegetables lack natural color variation."
        ]
    })

# Define Node for Check Pre-made
async def check_premade_node(state: AgentState):
    messages = state["messages"]
    # Simulate analysis
    return {
        "messages": [
            AIMessage(content="Analyzing the food for pre-made signs...", 
                      additional_kwargs={"thought": "Checking texture, color, and consistency..."}),
            AIMessage(content="", tool_calls=[{"name": "analyze_premade", "args": {"image_path": state["image_path"]}, "id": "call_2"}])
        ]
    }

async def premade_tools_node(state: AgentState):
    messages = state["messages"]
    last_message = messages[-1]
    
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        tool_call = last_message.tool_calls[0]
        if tool_call["name"] == "analyze_premade":
            result = analyze_premade.invoke(tool_call["args"])
            data = json.loads(result)
            
            report = f"**Dish Name**: {data['dish_name']}\n"
            report += f"**Pre-made Probability**: {data['score']}%\n"
            report += f"**Freshness**: {data['freshness']}\n"
            report += "**Analysis**:\n" + "\n".join([f"- {r}" for r in data['reasons']])
            
            return {
                "messages": [
                    AIMessage(content=report, 
                              additional_kwargs={"message": report}) # Send as message
                ]
            }
    return {"messages": []}

# We need a way to route to different agents. 
# For simplicity, we can create separate graphs or use a router.
# Let's create a separate graph for Check Pre-made.

premade_workflow = StateGraph(AgentState)
premade_workflow.add_node("agent", check_premade_node)
premade_workflow.add_node("tools", premade_tools_node)
premade_workflow.set_entry_point("agent")
premade_workflow.add_conditional_edges("agent", should_continue)
premade_workflow.add_edge("tools", END)

# ... (Previous imports and code)

# Define Tools for Calories
@tool
def analyze_calories(image_path: str):
    """Analyze calories in the food image."""
    # Mock analysis
    return json.dumps({
        "items": [
            {"name": "Rice", "calories": 200, "bbox": [100, 100, 200, 200]},
            {"name": "Pork", "calories": 350, "bbox": [200, 100, 300, 200]},
            {"name": "Vegetables", "calories": 50, "bbox": [150, 200, 250, 250]}
        ],
        "total_calories": 600,
        "advice": "Moderate meal, good protein content."
    })

# Define Node for Calories
async def calories_node(state: AgentState):
    messages = state["messages"]
    return {
        "messages": [
            AIMessage(content="Identifying food items and estimating calories...", 
                      additional_kwargs={"thought": "Detecting objects: Rice, Pork, Veggies..."}),
            AIMessage(content="", tool_calls=[{"name": "analyze_calories", "args": {"image_path": state["image_path"]}, "id": "call_3"}])
        ]
    }

async def calories_tools_node(state: AgentState):
    messages = state["messages"]
    last_message = messages[-1]
    
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        tool_call = last_message.tool_calls[0]
        if tool_call["name"] == "analyze_calories":
            result = analyze_calories.invoke(tool_call["args"])
            data = json.loads(result)
            
            # Construct a report and pass structured data for frontend annotation
            report = f"**Total Calories**: {data['total_calories']} kcal\n\n"
            for item in data['items']:
                report += f"- **{item['name']}**: {item['calories']} kcal\n"
            report += f"\n**Advice**: {data['advice']}"
            
            return {
                "messages": [
                    AIMessage(content=report, 
                              additional_kwargs={
                                  "message": report,
                                  "function_call": {"action": "annotate_image", "items": data['items']}
                              })
                ]
            }
    return {"messages": []}

calories_workflow = StateGraph(AgentState)
calories_workflow.add_node("agent", calories_node)
calories_workflow.add_node("tools", calories_tools_node)
calories_workflow.set_entry_point("agent")
calories_workflow.add_conditional_edges("agent", should_continue)
calories_workflow.add_edge("tools", END)

calories_graph = calories_workflow.compile()


