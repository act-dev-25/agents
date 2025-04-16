from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel
from langchain_core.messages import AnyMessage

class UserState(BaseModel):
    """User state information"""
    user_id: str
    session_id: str
    preferences: Dict[str, Any] = {}
    last_interaction: Optional[str] = None

class MessageState(BaseModel):
    """Message state for tracking conversation"""
    messages: List[AnyMessage]
    context: Dict[str, Any] = {}
    
class SpecialistContext(BaseModel):
    """Context specific to specialist agents"""
    knowledge_results: Optional[str] = None
    partner_results: Optional[str] = None
    reasoning_steps: List[Dict[str, str]] = []
    react_process: Dict[str, str] = {}

class GraphState(BaseModel):
    """Overall graph state"""
    messages: List[AnyMessage]
    user_state: UserState
    context: SpecialistContext = SpecialistContext()
    stream_id: str
    graph_state: str
    specialists_to_call: List[str] = []
    final_response: Optional[str] = None

class CareerState(GraphState):
    """Career Development and Resume Analysis state"""
    resume_data: Optional[Dict[str, Any]] = None
    skill_analysis: Optional[Dict[str, List[str]]] = None
    career_paths: List[Dict[str, Any]] = []
    training_gaps: List[Dict[str, str]] = []
    job_matches: List[Dict[str, Any]] = []
    development_plan: Optional[Dict[str, Any]] = None

class EjState(GraphState):
    """Environmental Justice specialist state"""
    ej_community_data: Optional[Dict[str, Any]] = None
    accessibility_needs: Optional[Dict[str, str]] = None
    community_programs: List[Dict[str, Any]] = []

class VeteranState(GraphState):
    """Veteran specialist state"""
    military_background: Optional[Dict[str, str]] = None
    skill_translations: List[Dict[str, str]] = []
    benefit_eligibility: Dict[str, bool] = {}

class InternationalState(GraphState):
    """International professional specialist state"""
    origin_country: Optional[str] = None
    credentials: List[Dict[str, Any]] = []
    visa_status: Optional[str] = None
    language_proficiency: Optional[Dict[str, str]] = None

# Additional configuration classes needed by agents.py

class SearchConfig(BaseModel):
    """Configuration for search operations"""
    query: str
    filters: Dict[str, Any] = {}
    max_results: int = 5
    include_metadata: bool = True

class MemoryResult(BaseModel):
    """Results from memory/knowledge base searches"""
    content: str
    metadata: Dict[str, Any] = {}
    score: Optional[float] = None
    source: Optional[str] = None

class ResumeAnalysisConfig(BaseModel):
    """Configuration for resume analysis"""
    resume_text: str
    career_focus: Optional[str] = None
    skill_categories: List[str] = ["technical", "soft", "transferable"]

class JobRecommendationConfig(BaseModel):
    """Configuration for job recommendations"""
    skills: List[str]
    experience_level: str
    location_preference: Optional[str] = None
    salary_range: Optional[Dict[str, float]] = None

class TrainingProgramConfig(BaseModel):
    """Configuration for training program searches"""
    skill_gaps: List[str]
    preferred_format: Optional[str] = None  # online, in-person, hybrid
    location: Optional[str] = None
    max_duration_months: Optional[int] = None

class FeedbackConfig(BaseModel):
    """Configuration for user feedback"""
    rating: int  # 1-5
    comments: Optional[str] = None
    improvement_areas: List[str] = []

class EJCommunityConfig(BaseModel):
    """Configuration for Environmental Justice community searches"""
    community: str
    needs: List[str] = []
    barriers: List[str] = []

class InternationalProfessionalConfig(BaseModel):
    """Configuration for international professional credential evaluation"""
    origin_country: str
    credentials: List[Dict[str, Any]] = []
    language_proficiency: Optional[Dict[str, str]] = None

# ClimateState builds on GraphState with additional configuration fields
class ClimateState(GraphState):
    """Climate Career Guidance System state"""
    search_config: Optional[SearchConfig] = None
    memory_results: List[MemoryResult] = []
    active_specialist: Optional[str] = None
    analysis_config: Optional[Union[
        ResumeAnalysisConfig,
        JobRecommendationConfig,
        TrainingProgramConfig,
        EJCommunityConfig,
        InternationalProfessionalConfig
    ]] = None
    
    
    
    
    
    
    
    