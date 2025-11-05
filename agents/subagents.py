from typing_extensions import TypedDict
from typing import Annotated, NotRequired
from langgraph.graph.message import AnyMessage, add_messages
from langchain.agents import create_agent

from agents.prompts import invoice_subagent_prompt
from agents.tools import invoice_tools
from agents.utils import llm

class InputState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]

class State(InputState):
    customer_id: NotRequired[int]
    loaded_memory: NotRequired[str]


# ------------------------------------------------------------
# Invoice Subagent
# ------------------------------------------------------------
invoice_subagent = create_agent(
    llm, 
    tools=invoice_tools, 
    name="invoice_subagent", 
    system_prompt=invoice_subagent_prompt, 
    state_schema=State
)

# ------------------------------------------------------------
# Opensearch E-commerce Subagent
# ------------------------------------------------------------

# TODO: Add Opensearch E-commerce Subagent