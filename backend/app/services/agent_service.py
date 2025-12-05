"""
Agent 服务模块

实现基于 LangGraph 的智能 Agent 工作流。
包含"去哪吃"、"查预制"、"吃多少"三个功能的完整流程。
"""

from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
import json
import base64
import re
import os
import random

from app.models.state import AgentState
from app.services.tools import search_location, analyze_premade, analyze_calories
from app.constants.prompts import WHERE_TO_EAT_PROMPT
from app.constants.preset_responses import (
    WHERE_TO_EAT_PRESETS,
    CHECK_PREMADE_PRESETS,
    CALORIES_PRESETS
)
from app.config import settings

from langchain_core.runnables import RunnableConfig
from langchain_core.callbacks.manager import adispatch_custom_event


# ========== 辅助函数 ==========

def get_preset_response(preset_list: list) -> str:
    """从预设响应列表中随机选择一条
    
    用于在LLM实际响应前给用户提供即时反馈，提升用户体验。
    每次调用随机选择，确保用户看到的提示文本每次都不同。
    
    Args:
        preset_list: 预设响应文本列表
        
    Returns:
        str: 随机选择的预设响应文本
    """
    return random.choice(preset_list)


def encode_image(image_path):
    """将图片文件编码为Base64字符串
    
    读取本地图片文件并转换为Base64编码，用于在API请求中传输图片数据。
    
    Args:
        image_path: 图片文件的本地路径
        
    Returns:
        str: Base64编码后的图片字符串
    """
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')


def should_continue(state: AgentState):
    """判断工作流是否应该继续执行
    
    检查最后一条消息是否包含工具调用，决定下一步是执行工具还是结束流程。
    
    Args:
        state: Agent状态对象，包含消息历史
        
    Returns:
        str: "tools" 表示需要执行工具，END 表示流程结束
    """
    messages = state["messages"]
    last_message = messages[-1]
    # 检查最后一条消息是否包含工具调用请求
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    return END


# --- Where to Eat Logic ---
async def where_to_eat_node(state: AgentState, config: RunnableConfig):
    """处理"去哪儿"功能的主节点，负责图片位置识别和流式输出。
    
    该节点接收用户上传的图片，调用 LLM 进行位置推理，并将思考过程
    以 custom_event 形式派发，最终结果以 state update 形式返回。
    """
    import httpx
    
    image_path = state.get("image_path")
    user_query = state.get("messages", [{}])[0].content if state.get("messages") else "这是哪里？"
    
    # 将图片转换为 Base64 编码
    if image_path.startswith("http"):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(image_path, timeout=30.0)
                response.raise_for_status()
                image_data = base64.b64encode(response.content).decode("utf-8")
                content_type = response.headers.get("content-type", "image/jpeg")
                image_url = f"data:{content_type};base64,{image_data}"
        except Exception as e:
            yield {"messages": [AIMessage(
                content=f"图片下载失败: {str(e)}",
                additional_kwargs={"message": f"图片下载失败: {str(e)}"}
            )]}
            return
    else:
        # Check if file exists to prevent errors
        if not os.path.exists(image_path):
             yield {"messages": [AIMessage(content="Image file not found")]}
             return
        base64_image = encode_image(image_path)
        image_url = f"data:image/jpeg;base64,{base64_image}"
    
    base_url = os.getenv("OPENAI_API_BASE")
    # Using a standard model name if possible, or keep as is if known to work (assuming environment is set).
    # Since we got a 500 before with 'fake image', we assume model connects.
    model = ChatOpenAI(model="gemini-2.5-pro", temperature=0, base_url=base_url)
    
    messages = [
        SystemMessage(content=WHERE_TO_EAT_PROMPT),
        HumanMessage(content=[
            {"type": "text", "text": user_query},
            {"type": "image_url", "image_url": {"url": image_url}}
        ])
    ]
    
    response_content = ""
    thought_content = ""
    print(f"[DEBUG] Starting where_to_eat_node with image: {image_path}")
    
    in_json_block = False
    
    try:
        # Pass config to astream to enable callbacks/tracing if needed by model,
        # but primarily we use manual dispatch.
        async for chunk in model.astream(messages, config=config):
            content = chunk.content
            if not content:
                continue
            
            response_content += content
            
            if not in_json_block:
                if "```json" in response_content or "## 3. JSON" in response_content:
                    in_json_block = True
                    # Do not dispatch content that is part of the marker
                else:
                    if content: # Dispatch even if space
                        await adispatch_custom_event("thought", {"content": content}, config=config)
                        thought_content += content

    except Exception as e:
        error_msg = f"AI 服务调用失败: {str(e)}"
        yield {"messages": [AIMessage(
            content=error_msg,
            additional_kwargs={"message": error_msg}
        )]}
        return
    
    # ============ Extract JSON ============
    print(f"[DEBUG] Full response length: {len(response_content)}")
    
    json_patterns = [
        r'```json\s*(.*?)\s*```',
        r'JSON:\s*(\{.*?\})',
    ]
    
    json_data = None
    for pattern in json_patterns:
        json_match = re.search(pattern, response_content, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
            try:
                json_data = json.loads(json_str)
                break
            except json.JSONDecodeError:
                continue
    
    final_messages = []
    
    # Add the full thought message for history/debug
    if thought_content:
        final_messages.append(AIMessage(
            content=thought_content,
            additional_kwargs={"thought": thought_content}
        ))

    if json_data:
        final_messages.append(AIMessage(
            content="位置已识别",
            additional_kwargs={
                "function_call": {
                    "action": "open_map",
                    "lat": json_data.get("latitude"),
                    "lng": json_data.get("longitude"),
                    "name": json_data.get("name", "未知地点"),
                    "address": json_data.get("address", "地址未知")
                }
            }
        ))
    else:
        final_messages.append(AIMessage(
            content="未能从响应中提取位置信息。",
            additional_kwargs={"message": "未能从响应中提取位置信息。"}
        ))
        
    yield {"messages": final_messages}

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
