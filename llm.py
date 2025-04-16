"""
Language model initialization for the Climate Ecosystem Assistant.
Provides centralized access to various LLM providers.
"""
import os
from typing import Dict, Any, Optional, List

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic

# Import configuration
from config import get_llm_config

# Load environment variables
load_dotenv()

# Set environment variables for API keys
os.environ["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY")
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")

# Initialize LLMs using configuration
def get_groq_llm(overrides: Optional[Dict[str, Any]] = None) -> ChatGroq:
    """
    Get a configured Groq LLM instance
    
    Args:
        overrides: Optional parameter overrides
        
    Returns:
        Configured ChatGroq instance
    """
    # Get base configuration
    config = get_llm_config("groq")
    
    # Apply overrides if provided
    if overrides:
        config.update(overrides)
    
    return ChatGroq(
        model_name=config.get("model", "llama3-8b-8192"),
        temperature=config.get("temperature", 0.2),
        max_tokens=config.get("max_tokens", 4096)
    )

def get_openai_llm(overrides: Optional[Dict[str, Any]] = None) -> ChatOpenAI:
    """
    Get a configured OpenAI LLM instance
    
    Args:
        overrides: Optional parameter overrides
        
    Returns:
        Configured ChatOpenAI instance
    """
    # Get base configuration
    config = get_llm_config("openai")
    
    # Apply overrides if provided
    if overrides:
        config.update(overrides)
    
    return ChatOpenAI(
        model=config.get("model", "gpt-4"),
        temperature=config.get("temperature", 0.2),
        max_tokens=config.get("max_tokens", 4096)
    )

def get_anthropic_llm(overrides: Optional[Dict[str, Any]] = None) -> ChatAnthropic:
    """
    Get a configured Anthropic LLM instance
    
    Args:
        overrides: Optional parameter overrides
        
    Returns:
        Configured ChatAnthropic instance
    """
    # Get base configuration
    config = get_llm_config("anthropic")
    
    # Apply overrides if provided
    if overrides:
        config.update(overrides)
    
    return ChatAnthropic(
        model=config.get("model", "claude-3-opus-20240229"),
        temperature=config.get("temperature", 0.3),
        max_tokens=config.get("max_tokens", 4096)
    )

# Default LLM to use
llm = get_groq_llm()



