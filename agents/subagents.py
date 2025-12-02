from typing_extensions import TypedDict
from typing import Annotated, NotRequired
from langgraph.graph.message import AnyMessage, add_messages
from langchain.agents import create_agent

from agents.prompts import invoice_subagent_prompt, music_subagent_prompt, concert_subagent_prompt
from agents.tools import invoice_tools, music_tools, concert_tools
from agents.utils import llm
from agents.checkpoint import get_checkpointer


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
    name="invoice_subagent",
    tools=invoice_tools, 
    system_prompt=invoice_subagent_prompt, 
    state_schema=State,
    checkpointer=get_checkpointer()
)

# ------------------------------------------------------------
# Music Catalog Subagent
# ------------------------------------------------------------
music_subagent = create_agent(
    llm, 
    name="music_subagent",
    tools=music_tools, 
    system_prompt=music_subagent_prompt, 
    state_schema=State,
    checkpointer=get_checkpointer()
)

# ------------------------------------------------------------
# Concert Subagent
# ------------------------------------------------------------
concert_subagent = create_agent(
    llm,
    name="concert_subagent",
    tools=concert_tools,
    system_prompt=concert_subagent_prompt,
    state_schema=State,
    checkpointer=get_checkpointer()
)

# ------------------------------------------------------------
# Opensearch E-commerce Subagent
# ------------------------------------------------------------

# TODO: Add Opensearch E-commerce Subagent