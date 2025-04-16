import os
from typing import Dict, Any, List

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

from state import (
    GraphState, UserState, MessageState, SpecialistContext,
    EjState, VeteranState, InternationalState
)
from validators import (
    validate_graph_state, validate_user_state,
    validate_message_state, validate_specialist_context,
    validate_ej_state, validate_veteran_state, validate_international_state
)
from llm import get_groq_llm

# Load environment variables
load_dotenv()
os.environ["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY")

# Initialize LLM with Groq for chat interactions
llm = get_groq_llm({
    "temperature": 0.7,  # Use a slightly higher temperature for more creative responses
    "max_tokens": 4096
})


def create_initial_state(user_id: str, session_id: str) -> GraphState:
    """Create initial graph state"""
    return GraphState(
        messages=[],
        user_state=UserState(
            user_id=user_id,
            session_id=session_id
        ),
        context=SpecialistContext(),
        stream_id=session_id,
        graph_state="initial"
    )

def create_specialist_state(base_state: GraphState, specialist_type: str) -> GraphState:
    """Create specialist-specific state"""
    state_data = base_state.dict()
    
    if specialist_type == "ej":
        return EjState(**state_data)
    elif specialist_type == "veteran":
        return VeteranState(**state_data)
    elif specialist_type == "international":
        return InternationalState(**state_data)
    else:
        return base_state

def update_state(current_state: GraphState, updates: Dict[str, Any]) -> GraphState:
    """Update graph state with new data"""
    state_data = current_state.dict()
    state_data.update(updates)
    
    # Determine state type and validate
    if isinstance(current_state, EjState):
        return validate_ej_state(state_data)
    elif isinstance(current_state, VeteranState):
        return validate_veteran_state(state_data)
    elif isinstance(current_state, InternationalState):
        return validate_international_state(state_data)
    else:
        return validate_graph_state(state_data)

def add_message_to_state(
    state: GraphState,
    content: str,
    role: str = "human",
    **kwargs
) -> GraphState:
    """Add a new message to the state"""
    message = (
        HumanMessage(content=content)
        if role == "human"
        else AIMessage(content=content)
    )
    
    messages = state.messages + [message]
    return update_state(state, {"messages": messages, **kwargs})



