from typing import Dict, Any, Literal, TypedDict, List

# Third-party imports
from langchain.graphs import StateGraph
from langchain.graphs.state_graph import END, START
from langgraph.types import interrupt, Command

# Local application imports
from state import GraphState, EjState, VeteranState, InternationalState, CareerState
from node import (
    supervisor_node,
    liv_node,
    jasmine_node,
    marcus_node,
    miguel_node,
    integrate_responses_node,
    human_feedback_node
)
from tools import (
    search_knowledge_base,
    search_clean_energy_web,
    search_massachusetts_resources,
    search_clean_energy_occupations,
    search_training_programs,
    locate_ej_training_resources,
    find_dei_programs,
    translate_military_occupation,
    find_veteran_benefits,
    evaluate_international_credential,
    find_international_integration_resources,
    get_ecosystem_partners
)

class GraphConfig(TypedDict):
    """Configuration for the graph"""
    tool_config: Dict[str, Any]
    checkpointer: Any | None

def create_climate_graph(config: GraphConfig) -> StateGraph:
    """
    Creates the climate career guidance system graph.
    Pendo acts as the supervisor, routing to specialists when needed.
    """
    # Initialize graph
    graph = StateGraph()
    
    # Add nodes
    graph.add_node("supervisor", supervisor_node)  # Pendo's supervisor node
    graph.add_node("liv", liv_node)  # Career development specialist
    graph.add_node("jasmine", jasmine_node)  # Environmental justice specialist
    graph.add_node("marcus", marcus_node)  # Veterans specialist
    graph.add_node("miguel", miguel_node)  # International professionals specialist
    graph.add_node("integrate", integrate_responses_node)  # Response integration
    graph.add_node("human_feedback", human_feedback_node)  # Human feedback
    
    # Set entry point to supervisor (Pendo)
    graph.set_entry_point("supervisor")
    
    # Add edges for specialists
    specialist_nodes = ["liv", "jasmine", "marcus", "miguel"]
    for node_name in specialist_nodes:
        # Connect supervisor to specialists
        graph.add_edge("supervisor", node_name)
        # Connect specialists back to supervisor
        graph.add_edge(node_name, "supervisor")
        # Connect specialists to integration
        graph.add_edge(node_name, "integrate")
    
    # Add edges for human feedback
    graph.add_edge("supervisor", "human_feedback")
    graph.add_edge("human_feedback", "supervisor")
    
    # Add edges for integration
    graph.add_edge("integrate", "supervisor")
    graph.add_edge("supervisor", "integrate")
    
    # Add edge to END
    graph.add_edge("supervisor", END)
    
    # Configure graph
    if config:
        if "checkpointer" in config:
            graph.set_checkpointer(config["checkpointer"])
        if "tool_config" in config:
            graph.config["tool"] = config["tool_config"]
    
    # Compile graph
    graph.compile()
    
    return graph

def create_graph_with_config(config: GraphConfig | None = None) -> StateGraph:
    """Create graph with configuration"""
    default_config: GraphConfig = {
        "tool_config": {
            "max_concurrent_calls": 5,
            "timeout": 30,
            "retry_attempts": 2
        },
        "checkpointer": None
    }
    
    # Merge configs
    if config:
        for key, value in config.items():
            if isinstance(value, dict):
                default_config[key].update(value)
            else:
                default_config[key] = value
    
    return create_climate_graph(default_config)

# Create graph instance with default configuration

climate_graph = create_graph_with_config()

