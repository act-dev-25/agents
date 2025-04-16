from typing import Literal, Dict, Any, List, Optional
from langchain_core.messages import HumanMessage
from langgraph.types import Command

from agents import execute_agent, PERSONAS
from tools import (
    search_knowledge_base, search_clean_energy_web, search_massachusetts_resources,
    search_clean_energy_occupations, search_training_programs,
    locate_ej_training_resources, find_dei_programs,
    translate_military_occupation, find_veteran_benefits,
    evaluate_international_credential, find_international_integration_resources,
    get_ecosystem_partners,
    analyze_resume,
    get_career_paths,
    find_training_resources,
    match_jobs,
    create_development_plan
)

# Define tool sets for each specialist
PENDO_TOOLS = [
    search_knowledge_base,
    search_clean_energy_web,
    search_massachusetts_resources,
    search_clean_energy_occupations,
    search_training_programs
]

JASMINE_TOOLS = [
    search_knowledge_base,
    search_clean_energy_web,
    search_massachusetts_resources,
    locate_ej_training_resources,
    find_dei_programs
]

MARCUS_TOOLS = [
    search_knowledge_base,
    search_clean_energy_web,
    search_massachusetts_resources,
    search_clean_energy_occupations,
    translate_military_occupation,
    find_veteran_benefits
]

MIGUEL_TOOLS = [
    search_knowledge_base,
    search_clean_energy_web,
    search_massachusetts_resources,
    search_clean_energy_occupations,
    evaluate_international_credential,
    find_international_integration_resources
]

LIV_TOOLS = [
    search_knowledge_base,
    search_clean_energy_web,
    search_massachusetts_resources,
    search_clean_energy_occupations,
    analyze_resume,
    get_career_paths,
    find_training_resources,
    match_jobs,
    create_development_plan
]

def supervisor_node(state: Dict[str, Any]) -> Command:
    """
    Pendo's supervisor node that analyzes queries and routes to specialists if needed.
    Otherwise handles the query directly using knowledge base and ecosystem partner data.
    """
    messages = state.get("messages", [])
    if not messages:
        return Command(goto="END", update={"error": "No messages found"})

    latest_msg = messages[-1]
    
    # First check knowledge base
    kb_results = search_knowledge_base(latest_msg)
    context = {"knowledge_base_results": kb_results} if kb_results else {}
    
    # Check ecosystem partners
    partners = get_ecosystem_partners(latest_msg)
    if partners:
        context["ecosystem_partners"] = partners
    
    # Execute supervisor agent
    result = execute_agent(
        persona_name="pendo",
        tools=PENDO_TOOLS,
        messages=[latest_msg],
        context=context
    )
    
    # Analyze response for routing
    response_lower = result["response"].lower()
    specialists = []
    routing_reasons = []
    
    # Check for specialist keywords
    if any(kw in response_lower for kw in ["career", "resume", "skills"]):
        specialists.append("liv")
        routing_reasons.append("Career development expertise needed")
        
    if any(kw in response_lower for kw in ["environmental justice", "equity", "community"]):
        specialists.append("jasmine")
        routing_reasons.append("Environmental justice expertise needed")
        
    if any(kw in response_lower for kw in ["veteran", "military", "service"]):
        specialists.append("marcus")
        routing_reasons.append("Veteran transition expertise needed")
        
    if any(kw in response_lower for kw in ["international", "visa", "credential"]):
        specialists.append("miguel")
        routing_reasons.append("International professional expertise needed")
    
    # If no specialists needed and we have knowledge base results
    if not specialists and kb_results:
        return Command(
            goto="END",
            update={
                "final_response": result["response"],
                "context": context
            }
        )
    
    # Route to specialists if needed
    if specialists:
        return Command(
            goto="human_feedback",
            update={
                "specialists_to_call": specialists,
                "routing_reasons": routing_reasons,
                "context": context
            }
        )
    
    # Default to ending with supervisor response
    return Command(
        goto="END",
        update={
            "final_response": result["response"],
            "context": context
        }
    )

def human_feedback_node(state: Dict[str, Any]) -> Command:
    """Human feedback node for routing decisions"""
    specialists = state.get("specialists_to_call", [])
    routing_reasons = state.get("routing_reasons", [])
    context = state.get("context", {})
    
    # Create feedback prompt
    feedback_prompt = {
        "task": "Review Specialist Selection",
        "specialists": specialists,
        "reasons": routing_reasons,
        "context": context
    }
    
    # Get human feedback (implement actual feedback mechanism here)
    feedback = {"approved": True}  # Placeholder for actual feedback
    
    if feedback.get("approved"):
        # Route to first specialist
        return Command(
            goto=specialists[0],
            update={"context": context}
        )
    else:
        # Return to supervisor for re-analysis
        return Command(
            goto="supervisor",
            update={"feedback": feedback}
        )

def integrate_responses_node(state: Dict[str, Any]) -> Command:
    """Integrates specialist responses"""
    specialist_responses = state.get("specialist_responses", {})
    if not specialist_responses:
        return Command(
            goto="supervisor",
            update={"error": "No specialist responses to integrate"}
        )
    
    integrated_response = "Integrated insights from specialists:\n\n"
    for specialist, response in specialist_responses.items():
        integrated_response += f"{specialist.capitalize()}'s Analysis:\n{response}\n\n"
    
    return Command(
        goto="supervisor",
        update={"final_response": integrated_response}
    )

# Specialist Nodes
def liv_node(state: Dict[str, Any]) -> Command:
    """Career development specialist node"""
    messages = state.get("messages", [])
    context = state.get("context", {})
    
    result = execute_agent(
        persona_name="liv",
        tools=LIV_TOOLS,
        messages=messages,
        context=context
    )
    
    return Command(
        goto="supervisor",
        update={
            "specialist_responses": {
                "liv": result["response"]
            }
        }
    )

def jasmine_node(state: Dict[str, Any]) -> Command:
    """Environmental justice specialist node"""
    messages = state.get("messages", [])
    context = state.get("context", {})
    
    result = execute_agent(
        persona_name="jasmine",
        tools=JASMINE_TOOLS,
        messages=messages,
        context=context
    )
    
    return Command(
        goto="supervisor",
        update={
            "specialist_responses": {
                "jasmine": result["response"]
            }
        }
    )

def marcus_node(state: Dict[str, Any]) -> Command:
    """Veterans specialist node"""
    messages = state.get("messages", [])
    context = state.get("context", {})
    
    result = execute_agent(
        persona_name="marcus",
        tools=MARCUS_TOOLS,
        messages=messages,
        context=context
    )
    
    return Command(
        goto="supervisor",
        update={
            "specialist_responses": {
                "marcus": result["response"]
            }
        }
    )

def miguel_node(state: Dict[str, Any]) -> Command:
    """International professionals specialist node"""
    messages = state.get("messages", [])
    context = state.get("context", {})
    
    result = execute_agent(
        persona_name="miguel",
        tools=MIGUEL_TOOLS,
        messages=messages,
        context=context
    )
    
    return Command(
        goto="supervisor",
        update={
            "specialist_responses": {
                "miguel": result["response"]
            }
        }
    )
