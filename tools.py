from typing import Annotated, List, Optional, Dict, Any
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor

from langchain_community.document_loaders import WebBaseLoader
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain.tools import tool
from langchain_community.vectorstores.supabase import SupabaseVectorStore
from langchain_openai import OpenAIEmbeddings
from supabase import create_client, Client
from bs4 import BeautifulSoup
import requests
from chat import llm
import os
from datetime import date
from dotenv import load_dotenv
import json
import redis

# Load environment variables
load_dotenv()

# Database connection parameters
DB_USER = os.getenv("user")
DB_PASSWORD = os.getenv("password")
DB_HOST = os.getenv("host")
DB_PORT = os.getenv("port", "6543")
DB_NAME = os.getenv("dbname", "postgres")

# Direct database connection function
def get_db_connection():
    """Get a direct database connection, bypassing Supabase API"""
    try:
        connection = psycopg2.connect(
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME
        )
        return connection
    except Exception as e:
        print(f"Failed to connect directly to database: {e}")
        return None

# Query database directly
def direct_db_query(query, params=None, dict_cursor=True):
    """Execute a query directly against the PostgreSQL database"""
    connection = get_db_connection()
    if not connection:
        return []
    
    try:
        cursor = connection.cursor(cursor_factory=RealDictCursor if dict_cursor else None)
        cursor.execute(query, params or {})
        results = cursor.fetchall()
        cursor.close()
        connection.close()
        return results
    except Exception as e:
        print(f"Error executing direct query: {e}")
        if connection:
            connection.close()
        return []

# Initialize Supabase and Redis clients
try:
    supabase = create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_ANON_KEY")
    )
    
    # Create admin client with service role key for operations requiring higher privileges
    supabase_admin = create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    )
    
    embeddings = OpenAIEmbeddings()
    
    # Try to initialize vector store with match_documents function (if it exists)
    vector_store = None
    try:
        vector_store = SupabaseVectorStore(
            client=supabase_admin,  # Use service role client to bypass RLS
            embedding=embeddings,
            table_name="knowledge_chunks",
            query_name="match_documents"  # Try standard function name first
        )
    except Exception as e:
        print(f"Could not initialize vector store with match_documents: {e}")
        try:
            # Fall back to search_knowledge_base function
            vector_store = SupabaseVectorStore(
                client=supabase_admin,
                embedding=embeddings,
                table_name="knowledge_chunks",
                query_name="search_knowledge_base"
            )
        except Exception as e2:
            print(f"Could not initialize vector store with search_knowledge_base: {e2}")
    
    supabase_available = True
except Exception as e:
    print(f"Failed to initialize Supabase: {e}")
    supabase_available = False
    supabase = None
    supabase_admin = None
    vector_store = None

try:
    redis_client = redis.Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", 6379)),
        password=os.getenv("REDIS_PASSWORD"),
        decode_responses=True
    )
    redis_available = True
except Exception as e:
    print(f"Failed to initialize Redis: {e}")
    redis_available = False
    redis_client = None

tavily_tool = TavilySearchResults(max_results=5)

# Authentication and User Management Tools
@tool
def validate_user_age(birth_date: str) -> Dict[str, bool]:
    """Validate if user meets the minimum age requirement (>10 years)."""
    try:
        birth = datetime.strptime(birth_date, "%Y-%m-%d").date()
        today = date.today()
        age = today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))
        return {
            "is_valid": age > 10,
            "message": "Age verification successful" if age > 10 else "Users must be over 10 years old"
        }
    except ValueError:
        return {"is_valid": False, "message": "Invalid date format. Use YYYY-MM-DD"}

# Ecosystem Knowledge Base Tools
@tool
def search_ecosystem_partners(query: str) -> str:
    """Search Massachusetts climate ecosystem partners' information from Supabase vector store."""
    results = vector_store.similarity_search(
        query,
        k=5,
        filter={"region": "massachusetts"}
    )
    return "\n\n".join([doc.page_content for doc in results])

@tool
def get_partner_programs(partner_name: str) -> str:
    """Get specific educational programs and resources from ecosystem partners."""
    query = f"educational programs and resources from {partner_name} in Massachusetts climate sector"
    results = vector_store.similarity_search(
        query,
        k=3,
        filter={"type": "program", "partner": partner_name}
    )
    return "\n\n".join([doc.page_content for doc in results])

# Profile Analysis Tools
@tool
def analyze_linkedin_profile(linkedin_url: str) -> Dict[str, Any]:
    """Extract and analyze professional information from LinkedIn profile."""
    try:
        loader = WebBaseLoader(linkedin_url)
        docs = loader.load()
        content = docs[0].page_content
        
        # Extract relevant sections (simplified version)
        analysis = {
            "experience": [],
            "education": [],
            "skills": [],
            "climate_relevant_experience": False,
            "international_experience": False,
            "veteran_status": False
        }
        
        # Add to vector store for future reference
        vector_store.add_texts(
            texts=[content],
            metadatas=[{"source": "linkedin", "url": linkedin_url}]
        )
        
        return analysis
    except Exception as e:
        return {"error": f"Failed to analyze LinkedIn profile: {str(e)}"}

@tool
def analyze_personal_website(website_url: str) -> Dict[str, Any]:
    """Extract and analyze information from personal website."""
    try:
        loader = WebBaseLoader(website_url)
        docs = loader.load()
        content = docs[0].page_content
        
        analysis = {
            "projects": [],
            "interests": [],
            "climate_related_content": False
        }
        
        vector_store.add_texts(
            texts=[content],
            metadatas=[{"source": "personal_website", "url": website_url}]
        )
        
        return analysis
    except Exception as e:
        return {"error": f"Failed to analyze personal website: {str(e)}"}

# Job Search and Matching Tools
@tool
def search_ecosystem_jobs(job_title: str, location: str = "Massachusetts") -> str:
    """Search for job listings specifically from Massachusetts climate ecosystem partners."""
    query = f"climate jobs {job_title} {location}"
    results = vector_store.similarity_search(
        query,
        k=5,
        filter={
            "type": "job_posting",
            "status": "active",
            "region": "massachusetts"
        }
    )
    return "\n\n".join([doc.page_content for doc in results])

@tool
def get_training_programs(skill_area: str) -> str:
    """Find relevant training programs from ecosystem partners based on skill area."""
    query = f"training programs in {skill_area} Massachusetts climate sector"
    results = vector_store.similarity_search(
        query,
        k=3,
        filter={"type": "training_program", "status": "active"}
    )
    return "\n\n".join([doc.page_content for doc in results])

# Specialist Tools
@tool
def international_credential_evaluation(credentials: str, country: str) -> str:
    """Evaluate international credentials against Massachusetts ecosystem partner requirements."""
    query = f"credential evaluation standards {credentials} {country} Massachusetts climate sector"
    results = vector_store.similarity_search(query, k=3)
    return "\n\n".join([doc.page_content for doc in results])

@tool
def find_ej_opportunities(location: str) -> str:
    """Find environmental justice opportunities within ecosystem partners."""
    query = f"environmental justice opportunities {location} Massachusetts"
    results = vector_store.similarity_search(
        query,
        k=3,
        filter={"category": "environmental_justice"}
    )
    return "\n\n".join([doc.page_content for doc in results])

@tool
def translate_military_experience(mos_code: str) -> str:
    """Translate military experience to Massachusetts climate sector opportunities."""
    query = f"military {mos_code} civilian equivalent Massachusetts climate sector"
    results = vector_store.similarity_search(
        query,
        k=3,
        filter={"category": "veteran_opportunities"}
    )
    return "\n\n".join([doc.page_content for doc in results])

# Tool Groups for Different Agents
supervisor_tools = [
    search_ecosystem_partners,
    get_partner_programs,
    search_ecosystem_jobs,
    get_training_programs
]

international_specialist_tools = [
    international_credential_evaluation,
    search_ecosystem_jobs,
    get_training_programs
]

ej_specialist_tools = [
    find_ej_opportunities,
    search_ecosystem_jobs,
    get_training_programs
]

veteran_specialist_tools = [
    translate_military_experience,
    search_ecosystem_jobs,
    get_training_programs
]

profile_analyzer_tools = [
    analyze_linkedin_profile,
    analyze_personal_website,
    validate_user_age
]

# Create specialized LLMs with their specific tools
supervisor_llm = llm.bind_tools(supervisor_tools)
international_specialist_llm = llm.bind_tools(international_specialist_tools)
ej_specialist_llm = llm.bind_tools(ej_specialist_tools)
veteran_specialist_llm = llm.bind_tools(veteran_specialist_tools)
profile_analyzer_llm = llm.bind_tools(profile_analyzer_tools)

# === KNOWLEDGE BASE TOOLS ===
@tool
def search_knowledge_base(query: str) -> List[Dict[str, Any]]:
    """Search knowledge base for relevant information using vector similarity"""
    if not supabase_available and not DB_USER:
        return [{"error": "Knowledge base is not available"}]
    
    try:
        # Cache key for this query
        cache_key = f"kb_search:{query}"
        
        # Try to get from cache first if Redis is available
        if redis_available:
            cached_result = get_from_cache(cache_key)
            if cached_result:
                print("Retrieved results from cache")
                return cached_result
        
        # Try vector store search if available
        results = []
        if vector_store:
            try:
                similarity_results = vector_store.similarity_search_with_score(query, k=5)
                
                for doc, score in similarity_results:
                    results.append({
                        "id": doc.metadata.get("id", "unknown"),
                        "content": doc.page_content,
                        "title": doc.metadata.get("title", "Untitled"),
                        "summary": doc.metadata.get("summary", ""),
                        "metadata": doc.metadata,
                        "similarity": score
                    })
            except Exception as ve:
                print(f"Vector store search failed: {ve}")
        
        # If vector store search failed or returned no results, try direct function call
        if not results:
            # Try with match_documents function, specifying all parameters to avoid overloading
            try:
                embeddings_vector = embeddings.embed_query(query)
                response = supabase_admin.rpc(
                    'match_documents',
                    {
                        'query_embedding': embeddings_vector,
                        'match_count': 5,
                        'filter_domain': ''  # Specify the optional parameter to avoid ambiguity
                    }
                ).execute()
                
                if response.data:
                    for item in response.data:
                        results.append({
                            "id": item.get("id", "unknown"),
                            "content": item.get("content", ""),
                            "title": item.get("title", "Untitled"),
                            "summary": item.get("summary", ""),
                            "metadata": item.get("metadata", {}),
                            "similarity": item.get("similarity", 0)
                        })
            except Exception as me:
                print(f"match_documents function call failed: {me}")
                
                # Try direct database connection as fallback
                try:
                    print("Trying direct database query...")
                    # Prepare keywords for search
                    keywords = query.lower().split()
                    if keywords:
                        # Build a query with multiple keywords using OR conditions
                        conditions = []
                        for keyword in keywords[:3]:  # Limit to first 3 keywords
                            if len(keyword) > 2:  # Skip very short words
                                conditions.append(f"content ILIKE '%{keyword}%'")
                        
                        if conditions:
                            sql_conditions = " OR ".join(conditions)
                            sql_query = f"""
                                SELECT id, title, content, summary, metadata 
                                FROM knowledge_chunks 
                                WHERE {sql_conditions}
                                LIMIT 5
                            """
                            
                            # Execute the query directly against PostgreSQL
                            db_results = direct_db_query(sql_query)
                            
                            if db_results:
                                for item in db_results:
                                    results.append({
                                        "id": item.get("id", "unknown"),
                                        "content": item.get("content", ""),
                                        "title": item.get("title", "Untitled"),
                                        "summary": item.get("summary", ""),
                                        "metadata": item.get("metadata", {}),
                                        "similarity": 0.75  # Default similarity for direct query
                                    })
                except Exception as dbe:
                    print(f"Direct database query failed: {dbe}")
                
                # If all else fails, try keyword matching via Supabase API
                if not results:
                    try:
                        # Simple keyword matching
                        keywords = query.lower().split()
                        if keywords:
                            main_keyword = keywords[0]
                            response = supabase_admin.table("knowledge_chunks").select("*").ilike("content", f"%{main_keyword}%").limit(5).execute()
                            
                            if response.data:
                                for item in response.data:
                                    results.append({
                                        "id": item.get("id", "unknown"),
                                        "content": item.get("content", ""),
                                        "title": item.get("title", "Untitled"),
                                        "summary": item.get("summary", ""),
                                        "metadata": item.get("metadata", {}),
                                        "similarity": 0.8  # Default similarity score for keyword matches
                                    })
                    except Exception as ke:
                        print(f"Keyword matching failed: {ke}")
        
        # Cache results if Redis is available
        if redis_available and results:
            set_in_cache(cache_key, results)
        
        return results
    except Exception as e:
        print(f"Error in search_knowledge_base: {e}")
        return [{"error": f"Search failed: {str(e)}"}]

@tool
def get_ecosystem_partners(filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Get ecosystem partners based on filters"""
    if not supabase_available:
        return [{"error": "Database is not available"}]
    
    try:
        # Always use admin client to bypass RLS
        query = supabase_admin.table('partner_organizations').select('*')
        
        if filters:
            # Build the filter for each key
            for key, value in filters.items():
                # We need to convert this to ilike for text search
                if isinstance(value, str):
                    query = query.ilike(key, f"%{value}%")
                else:
                    query = query.eq(key, value)
        
        # Execute the query
        response = query.execute()
        
        # Return the data or empty list
        return response.data if response.data else []
    except Exception as e:
        print(f"Error getting ecosystem partners: {e}")
        return []

# === CACHING TOOLS ===
def get_from_cache(key: str) -> Optional[Dict[str, Any]]:
    """Get data from Redis cache"""
    try:
        if not redis_available or not redis_client:
            return None
        data = redis_client.get(key)
        return json.loads(data) if data else None
    except Exception as e:
        print(f"Error getting from cache: {e}")
        return None

def set_in_cache(key: str, value: Dict[str, Any], expire: int = 3600) -> bool:
    """Set data in Redis cache with expiration"""
    try:
        if not redis_available or not redis_client:
            return False
        return redis_client.setex(key, expire, json.dumps(value))
    except Exception as e:
        print(f"Error setting cache: {e}")
        return False

# === WEB SEARCH TOOLS ===
@tool
def search_clean_energy_web(query: str) -> str:
    """Search the web for clean energy information in Massachusetts."""
    try:
        tavily_search = TavilySearchResults(max_results=3)
        enhanced_query = f"Massachusetts clean energy {query}"
        results = tavily_search.invoke(enhanced_query)
        
        formatted_results = []
        for i, doc in enumerate(results):
            source = doc.get("url", "unknown source")
            content = doc.get("content", "")
            formatted_results.append(f"Source {i+1} ({source}): {content}")
        
        return "\n\n".join(formatted_results)
    except Exception as e:
        return f"Error searching web: {str(e)}"

@tool
def search_massachusetts_resources(query: str) -> str:
    """Search for Massachusetts-specific clean energy resources."""
    try:
        tavily_search = TavilySearchResults(max_results=3)
        ecosystem_partners = [
            "MassCEC", "Mass Save", "Urban League of Eastern Massachusetts",
            "ACT", "Greentown Labs", "TPS Energy", "Headlamp",
            "Franklin Cummings Tech", "MassHire", "African Bridge Network"
        ]
        partner_string = " OR ".join(ecosystem_partners)
        enhanced_query = f"Massachusetts ({partner_string}) {query} clean energy workforce"
        results = tavily_search.invoke(enhanced_query)
        
        formatted_results = []
        for i, doc in enumerate(results):
            source = doc.get("url", "unknown source")
            content = doc.get("content", "")
            formatted_results.append(f"Source {i+1} ({source}): {content}")
        
        return "\n\n".join(formatted_results)
    except Exception as e:
        return f"Error searching resources: {str(e)}"

# === SPECIALIST TOOLS ===
# Environmental Justice Tools
@tool
def locate_ej_training_resources(location: str) -> str:
    """Find EJ-accessible training programs in Massachusetts locations."""
    try:
        tavily_search = TavilySearchResults(max_results=3)
        enhanced_query = f"Massachusetts {location} clean energy training accessibility Gateway City Environmental Justice"
        results = tavily_search.invoke(enhanced_query)
        
        formatted_results = []
        for i, doc in enumerate(results):
            source = doc.get("url", "unknown source")
            content = doc.get("content", "")
            formatted_results.append(f"Source {i+1} ({source}): {content}")
        
        return "\n\n".join(formatted_results)
    except Exception as e:
        return f"Error locating EJ resources: {str(e)}"

@tool
def find_dei_programs(group: str) -> str:
    """Find DEI programs for underrepresented groups in clean energy."""
    try:
        tavily_search = TavilySearchResults(max_results=3)
        enhanced_query = f"Massachusetts clean energy {group} diversity equity inclusion workforce programs"
        results = tavily_search.invoke(enhanced_query)
        
        formatted_results = []
        for i, doc in enumerate(results):
            source = doc.get("url", "unknown source")
            content = doc.get("content", "")
            formatted_results.append(f"Source {i+1} ({source}): {content}")
        
        return "\n\n".join(formatted_results)
    except Exception as e:
        return f"Error finding DEI programs: {str(e)}"

# Veteran Tools
@tool
def translate_military_occupation(military_code: str) -> str:
    """Translate military occupations to clean energy careers."""
    try:
        tavily_search = TavilySearchResults(max_results=3)
        enhanced_query = f"military {military_code} civilian equivalent clean energy career Massachusetts"
        results = tavily_search.invoke(enhanced_query)
        
        formatted_results = []
        for i, doc in enumerate(results):
            source = doc.get("url", "unknown source")
            content = doc.get("content", "")
            formatted_results.append(f"Source {i+1} ({source}): {content}")
        
        return "\n\n".join(formatted_results)
    except Exception as e:
        return f"Error translating military occupation: {str(e)}"

@tool
def find_veteran_benefits(benefit_type: str) -> str:
    """Find veteran benefits for clean energy training."""
    try:
        tavily_search = TavilySearchResults(max_results=3)
        enhanced_query = f"Massachusetts veteran {benefit_type} clean energy training education benefit"
        results = tavily_search.invoke(enhanced_query)
        
        formatted_results = []
        for i, doc in enumerate(results):
            source = doc.get("url", "unknown source")
            content = doc.get("content", "")
            formatted_results.append(f"Source {i+1} ({source}): {content}")
        
        return "\n\n".join(formatted_results)
    except Exception as e:
        return f"Error finding veteran benefits: {str(e)}"

# International Professional Tools
@tool
def evaluate_international_credential(credential: str, country: str) -> str:
    """Evaluate international credentials for Massachusetts clean energy sector."""
    try:
        tavily_search = TavilySearchResults(max_results=3)
        enhanced_query = f"{country} {credential} US equivalent Massachusetts clean energy license"
        results = tavily_search.invoke(enhanced_query)
        
        formatted_results = []
        for i, doc in enumerate(results):
            source = doc.get("url", "unknown source")
            content = doc.get("content", "")
            formatted_results.append(f"Source {i+1} ({source}): {content}")
        
        return "\n\n".join(formatted_results)
    except Exception as e:
        return f"Error evaluating credentials: {str(e)}"

@tool
def find_international_integration_resources(nationality: str) -> str:
    """Find resources for international professional integration."""
    try:
        tavily_search = TavilySearchResults(max_results=3)
        enhanced_query = f"Massachusetts {nationality} immigrant professional integration clean energy workforce"
        results = tavily_search.invoke(enhanced_query)
        
        formatted_results = []
        for i, doc in enumerate(results):
            source = doc.get("url", "unknown source")
            content = doc.get("content", "")
            formatted_results.append(f"Source {i+1} ({source}): {content}")
        
        return "\n\n".join(formatted_results)
    except Exception as e:
        return f"Error finding integration resources: {str(e)}"

# === TOOL SETS FOR EACH AGENT ===
SUPERVISOR_TOOLS = [
    search_knowledge_base,
    get_ecosystem_partners,
    search_clean_energy_web,
    search_massachusetts_resources
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
    translate_military_occupation,
    find_veteran_benefits
]

MIGUEL_TOOLS = [
    search_knowledge_base,
    search_clean_energy_web,
    search_massachusetts_resources,
    evaluate_international_credential,
    find_international_integration_resources
]

# Liv's Career Development Tools
def analyze_resume(resume_text: str) -> Dict[str, Any]:
    """Analyze resume for clean energy sector alignment"""
    try:
        response = supabase.rpc(
            'analyze_resume',
            {
                'resume_content': resume_text,
                'sector': 'clean_energy'
            }
        ).execute()
        return {
            'skills': response.data.get('skills', []),
            'experience': response.data.get('experience', []),
            'education': response.data.get('education', []),
            'gaps': response.data.get('gaps', []),
            'recommendations': response.data.get('recommendations', [])
        }
    except Exception as e:
        print(f"Error analyzing resume: {e}")
        return {}

def get_career_paths(current_role: str) -> List[Dict[str, Any]]:
    """Get potential career paths in clean energy sector"""
    try:
        response = supabase.rpc(
            'get_career_paths',
            {'current_role': current_role}
        ).execute()
        return response.data if response.data else []
    except Exception as e:
        print(f"Error getting career paths: {e}")
        return []

def find_training_resources(skills: List[str]) -> List[Dict[str, Any]]:
    """Find training resources for specific skills"""
    try:
        response = supabase.rpc(
            'find_training_resources',
            {'required_skills': skills}
        ).execute()
        return response.data if response.data else []
    except Exception as e:
        print(f"Error finding training resources: {e}")
        return []

def match_jobs(skills: List[str], experience_level: str) -> List[Dict[str, Any]]:
    """Match jobs based on skills and experience"""
    try:
        response = supabase.rpc(
            'match_jobs',
            {
                'candidate_skills': skills,
                'experience_level': experience_level
            }
        ).execute()
        return response.data if response.data else []
    except Exception as e:
        print(f"Error matching jobs: {e}")
        return []

def create_development_plan(
    current_skills: List[str],
    target_role: str
) -> Dict[str, Any]:
    """Create personalized development plan"""
    try:
        response = supabase.rpc(
            'create_development_plan',
            {
                'current_skills': current_skills,
                'target_role': target_role
            }
        ).execute()
        return response.data if response.data else {}
    except Exception as e:
        print(f"Error creating development plan: {e}")
        return {}

# Specialist Tools (Environmental Justice)
def search_ej_programs(location: str) -> List[Dict[str, Any]]:
    """Search for environmental justice programs"""
    try:
        response = supabase.rpc(
            'search_ej_programs',
            {'location': location}
        ).execute()
        return response.data if response.data else []
    except Exception as e:
        print(f"Error searching EJ programs: {e}")
        return []

# Veteran Tools
def translate_military_skills(mos_code: str) -> Dict[str, Any]:
    """Translate military skills to civilian equivalents"""
    try:
        response = supabase.rpc(
            'translate_military_skills',
            {'mos_code': mos_code}
        ).execute()
        return response.data if response.data else {}
    except Exception as e:
        print(f"Error translating military skills: {e}")
        return {}

# International Professional Tools
def evaluate_credentials(
    credentials: Dict[str, Any],
    country: str
) -> Dict[str, Any]:
    """Evaluate international credentials"""
    try:
        response = supabase.rpc(
            'evaluate_credentials',
            {
                'credentials': credentials,
                'origin_country': country
            }
        ).execute()
        return response.data if response.data else {}
    except Exception as e:
        print(f"Error evaluating credentials: {e}")
        return {}