from typing import Annotated, List,NotRequired
from typing_extensions import TypedDict
from pydantic import BaseModel, Field

from langchain.messages import SystemMessage, HumanMessage, AIMessage
from langchain.agents import create_agent
from langchain.tools import tool, ToolRuntime

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import AnyMessage, add_messages
from langgraph.managed.is_last_step import RemainingSteps
from langgraph.store.base import BaseStore
from langgraph.types import interrupt

from agents.subagents import invoice_subagent
from agents.prompts import (
    supervisor_system_prompt,
    extract_customer_info_prompt,
    verify_customer_info_prompt,
    create_memory_prompt
)
from agents.utils import (
    llm, 
    get_customer_id_from_identifier,
    format_user_memory
)


# ------------------------------------------------------------
# State Schema
# ------------------------------------------------------------
class InputState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]

class State(InputState):
    customer_id: NotRequired[str]
    loaded_memory: NotRequired[str]


# ------------------------------------------------------------
# Supervisor Graph
# ------------------------------------------------------------
@tool(
    name_or_callable="invoice_subagent",
    description="""An agent that can assistant with all invoice-related queries. It can retrieve information about a customers past purchases or invoices."""
)
def call_invoice_subagent(runtime: ToolRuntime, query: str):
    print('made it here')
    print(f"invoice subagent input: {query}")
    result = invoice_subagent.invoke({
        "messages": [{"role": "user", "content": query}],
        "customer_id": runtime.state.get("customer_id", {})
    })
    subagent_response = result["messages"][-1].content
    return subagent_response

# TODO: Add Opensearch E-commerce Agent as tool

supervisor = create_agent(
    model="openai:gpt-4o", 
    tools=[call_invoice_subagent], # TODO: Add Opensearch E-commerce Agent as tool
    name="supervisor",
    system_prompt=supervisor_system_prompt, 
    state_schema=State, 
)

# ------------------------------------------------------------
# Human Feedback Nodes
# ------------------------------------------------------------

# Schema for parsing user-provided account information
class UserInput(BaseModel):
    identifier: str = Field(description = "Identifier, which can be a customer ID, email, or phone number.")

def verify_info(state: State):
    """Verify the customer's account by parsing their input and matching it with the database."""
    if state.get("customer_id") is None: 
        user_input = state["messages"][-1] 
        # Parse for customer ID
        parsed_info = llm.with_structured_output(schema=UserInput).invoke([SystemMessage(content=extract_customer_info_prompt)] + [user_input])
        # Extract details
        identifier = parsed_info.identifier
        customer_id = ""

        if (identifier):
            customer_id = get_customer_id_from_identifier(identifier)
        if customer_id != "":
            intent_message = AIMessage(
                content= f"Thank you for providing your information! I was able to verify your account with customer id {customer_id}."
            )
            return {"customer_id": customer_id, "messages" : [intent_message]}
        else:
          response = llm.invoke([SystemMessage(content=verify_customer_info_prompt)]+state['messages'])
          return {"messages": [response]}
    else: 
        pass

def human_input(state: State):
    """ No-op node that should be interrupted on """
    user_input = interrupt("Please provide input.")
    return {"messages": [HumanMessage(content=user_input)]}

# Edge Condition for interrupts
def should_interrupt(state: State):
    if state.get("customer_id") is not None:
        return "continue"
    else:
        return "interrupt"


# ------------------------------------------------------------
# Long Term Memory Nodes
# ------------------------------------------------------------

def load_memory(state: State, store: BaseStore):
    """Loads music preferences from users, if available."""
    user_id = state["customer_id"]
    namespace = ("memory_profile", user_id)
    existing_memory = store.get(namespace, "user_memory")
    formatted_memory = ""
    if existing_memory and existing_memory.value:
        formatted_memory = format_user_memory(existing_memory.value)
    return {"loaded_memory" : formatted_memory}

# User profile structure for creating memory
class UserProfile(BaseModel):
    customer_id: str = Field(description="The customer ID of the customer")
    music_preferences: List[str] = Field(description="The music preferences of the customer")

def create_memory(state: State, store: BaseStore):
    user_id = str(state["customer_id"])
    namespace = ("memory_profile", user_id)
    formatted_memory = state["loaded_memory"]
    formatted_system_message = SystemMessage(content=create_memory_prompt.format(conversation=state["messages"], memory_profile=formatted_memory))
    updated_memory = llm.with_structured_output(UserProfile).invoke([formatted_system_message])
    key = "user_memory"
    store.put(namespace, key, {"memory": updated_memory})


# ------------------------------------------------------------
# State Graph
# ------------------------------------------------------------
workflow_builder = StateGraph(State, input_schema = InputState) 
workflow_builder.add_node("verify_info", verify_info)
workflow_builder.add_node("human_input", human_input)
workflow_builder.add_node("load_memory", load_memory)
workflow_builder.add_node("supervisor", supervisor)
workflow_builder.add_node("create_memory", create_memory)

workflow_builder.add_edge(START, "verify_info")
workflow_builder.add_conditional_edges(
    "verify_info",
    should_interrupt,
    {
        "continue": "load_memory",
        "interrupt": "human_input",
    },
)
workflow_builder.add_edge("human_input", "verify_info")
workflow_builder.add_edge("load_memory", "supervisor")
workflow_builder.add_edge("supervisor", "create_memory")
workflow_builder.add_edge("create_memory", END)

graph = workflow_builder.compile(name="multi_agent_verify")
