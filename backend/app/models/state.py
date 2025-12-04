from typing import TypedDict, Annotated, List
from langchain_core.messages import BaseMessage
import operator

# Define State
class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]
    image_path: str
