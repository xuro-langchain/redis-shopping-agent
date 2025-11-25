import os
from typing_extensions import TypedDict
from typing import Annotated, NotRequired
from langgraph.graph.message import AnyMessage, add_messages
from langgraph.checkpoint.redis import RedisSaver
from langchain.agents import create_agent
from redis import Redis

from agents.prompts import invoice_subagent_prompt, music_subagent_prompt
from agents.tools import invoice_tools, music_tools
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
    name="invoice_subagent",
    tools=invoice_tools, 
    system_prompt=invoice_subagent_prompt, 
    state_schema=State,
    checkpointer=RedisSaver(
        redis_client=Redis.from_url(
            os.getenv("REDIS_URL", "redis://localhost:6379")
        )
    )
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
    checkpointer=RedisSaver(
        redis_client=Redis.from_url(
            os.getenv("REDIS_URL", "redis://localhost:6379")
        )
    )
)

# ------------------------------------------------------------
# Opensearch E-commerce Subagent
# ------------------------------------------------------------

# TODO: Add Opensearch E-commerce Subagent