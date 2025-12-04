from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
import json
import base64
import re
import os

from app.models.state import AgentState
from app.services.tools import search_location, analyze_premade, analyze_calories
from app.constants.prompts import WHERE_TO_EAT_PROMPT

# --- Helper Functions ---
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def should_continue(state: AgentState):
    messages = state["messages"]
    last_message = messages[-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    return END

# --- Where to Eat Logic ---
async def where_to_eat_node(state: AgentState):
    image_path = state.get("image_path")
    # Check if image_path is a URL or local path
    if image_path.startswith("http"):
        image_url = image_path
    else:
        base64_image = encode_image(image_path)
        image_url = f"data:image/jpeg;base64,{base64_image}"
    
    base_url = os.getenv("OPENAI_API_BASE")
    model = ChatOpenAI(model="gpt-4o", temperature=0, base_url=base_url) # Or appropriate model
    
    messages = [
        SystemMessage(content=WHERE_TO_EAT_PROMPT),
        HumanMessage(content=[
            {"type": "text", "text": "Where is this?"},
            {"type": "image_url", "image_url": {"url": image_url}}
        ])
    ]
    
    response_content = ""
    found_answer = False
    found_json = False
    
    try:
        async for chunk in model.astream(messages):
            content = chunk.content
            response_content += content
            
            # Handle transitions within the chunk
            if not found_json and "JSON:" in content:
                parts = content.split("JSON:", 1)
                # Process the part before JSON
                pre_json = parts[0]
                if pre_json:
                    if found_answer:
                        yield {"messages": [AIMessage(content=pre_json, additional_kwargs={"message": pre_json})]}
                    else:
                         # This case shouldn't happen if ANSWER comes before JSON, but just in case
                        yield {"messages": [AIMessage(content=pre_json, additional_kwargs={"thought": pre_json})]}
                
                found_json = True
                # We do not stream the part after JSON: as text
                continue

            if not found_answer and "ANSWER:" in content:
                parts = content.split("ANSWER:", 1)
                # Process the part before ANSWER (Thought)
                thought_part = parts[0]
                if thought_part:
                    yield {"messages": [AIMessage(content=thought_part, additional_kwargs={"thought": thought_part})]}
                
                found_answer = True
                # Process the part after ANSWER (Message)
                message_part = parts[1]
                if message_part:
                    yield {"messages": [AIMessage(content=message_part, additional_kwargs={"message": message_part})]}
                continue
            
            # Normal streaming
            if found_json:
                pass # Accumulate JSON content but don't stream as text
            elif found_answer:
                yield {"messages": [AIMessage(content=content, additional_kwargs={"message": content})]}
            else:
                yield {"messages": [AIMessage(content=content, additional_kwargs={"thought": content})]}

    except Exception as e:
        yield {"messages": [AIMessage(content=f"Error calling AI service: {str(e)}", additional_kwargs={"message": f"Error: {str(e)}"})]}
        return
    
    # Extract JSON from response_content
    json_match = re.search(r'```json\n(.*?)\n```', response_content, re.DOTALL)
    if json_match:
        json_str = json_match.group(1)
        try:
            data = json.loads(json_str)
            yield {
                "messages": [
                    AIMessage(content="Found it!", 
                              additional_kwargs={
                                  "function_call": {
                                      "action": "open_map", 
                                      "lat": data["latitude"], 
                                      "lng": data["longitude"], 
                                      "name": data["name"], 
                                      "address": data["address"]
                                  }
                              })
                ]
            }
        except json.JSONDecodeError:
            print("Failed to parse JSON from LLM response")
            yield {"messages": [AIMessage(content="Could not parse location data.")]}
    else:
        yield {"messages": [AIMessage(content="Could not find location data in response.")]}

where_to_eat_workflow = StateGraph(AgentState)
where_to_eat_workflow.add_node("agent", where_to_eat_node)
where_to_eat_workflow.set_entry_point("agent")
where_to_eat_workflow.add_edge("agent", END)
where_to_eat_graph = where_to_eat_workflow.compile()


# --- General Agent Logic (Legacy/Example) ---
async def agent_node(state: AgentState):
    messages = state["messages"]
    last_message = messages[-1]
    
    if isinstance(last_message, HumanMessage):
        return {
            "messages": [
                AIMessage(content="I see a delicious looking dish. Let me try to identify the restaurant based on the visual cues.", 
                          additional_kwargs={"thought": "Analyzing image features... It looks like Dongpo Pork from a restaurant in Hangzhou."}),
                AIMessage(content="", tool_calls=[{"name": "search_location", "args": {"query": "Hangzhou Dongpo Pork Restaurant"}, "id": "call_1"}])
            ]
        }
    return {"messages": []}

async def tools_node(state: AgentState):
    messages = state["messages"]
    last_message = messages[-1]
    
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        tool_call = last_message.tool_calls[0]
        if tool_call["name"] == "search_location":
            result = search_location.invoke(tool_call["args"])
            data = json.loads(result)
            return {
                "messages": [
                    AIMessage(content=f"I found the location: {data['name']}", 
                              additional_kwargs={"function_call": {"action": "open_map", "lat": data["lat"], "lng": data["lng"], "name": data["name"], "address": data["address"]}})
                ]
            }
    return {"messages": []}

workflow = StateGraph(AgentState)
workflow.add_node("agent", agent_node)
workflow.add_node("tools", tools_node)
workflow.set_entry_point("agent")
workflow.add_conditional_edges("agent", should_continue)
workflow.add_edge("tools", END)
app_graph = workflow.compile()


# --- Check Premade Logic ---
async def check_premade_node(state: AgentState):
    messages = state["messages"]
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
                              additional_kwargs={"message": report})
                ]
            }
    return {"messages": []}

premade_workflow = StateGraph(AgentState)
premade_workflow.add_node("agent", check_premade_node)
premade_workflow.add_node("tools", premade_tools_node)
premade_workflow.set_entry_point("agent")
premade_workflow.add_conditional_edges("agent", should_continue)
premade_workflow.add_edge("tools", END)
premade_graph = premade_workflow.compile()


# --- Calories Logic ---
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
