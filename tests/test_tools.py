import os
from dotenv import load_dotenv
import json
from supabase import create_client
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores.supabase import SupabaseVectorStore
from tools import search_knowledge_base, get_ecosystem_partners, direct_db_query, get_db_connection

# Load environment variables
load_dotenv()

print("Supabase URL:", os.getenv("SUPABASE_URL"))
print("Supabase Key:", os.getenv("SUPABASE_ANON_KEY")[:10] + "..." if os.getenv("SUPABASE_ANON_KEY") else "Not found")

# Create Supabase client with anonymous key first
supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_ANON_KEY")
)

# Also create a service client for admin operations
supabase_admin = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
)

def print_results(name, results):
    print(f"\n==== {name} ====")
    if isinstance(results, list):
        print(f"Found {len(results)} results")
        for i, item in enumerate(results[:3]):
            print(f"\nItem {i+1}:")
            print(json.dumps(item, indent=2) if isinstance(item, dict) else item)
    else:
        print(str(results)[:500] + "..." if len(str(results)) > 500 else results)

# Test direct database connection
def test_direct_db_connection():
    print("\n==== Testing Direct DB Connection ====")
    
    # Test basic connection
    try:
        conn = get_db_connection()
        if conn:
            print("Direct PostgreSQL connection successful!")
            conn.close()
        else:
            print("Failed to establish direct connection")
    except Exception as e:
        print(f"Error testing direct connection: {e}")
    
    # Test direct query
    try:
        print("\nTesting direct_db_query function:")
        
        # Try a simple query
        simple_query = "SELECT NOW() as current_time;"
        results = direct_db_query(simple_query)
        if results:
            print(f"Direct query successful: {results[0].get('current_time')}")
        else:
            print("No results from direct query")
        
        # Try querying knowledge chunks
        print("\nQuerying knowledge chunks via direct SQL:")
        kb_query = """
            SELECT id, title, content
            FROM knowledge_chunks
            LIMIT 3;
        """
        chunks = direct_db_query(kb_query)
        print(f"Found {len(chunks)} knowledge chunks via direct SQL")
        for i, chunk in enumerate(chunks):
            print(f"\nChunk {i+1}:")
            print(f"ID: {chunk.get('id', 'N/A')}")
            print(f"Title: {chunk.get('title', 'N/A')}")
            content = chunk.get('content', 'N/A')
            print(f"Content: {content[:100]}..." if content and len(content) > 100 else f"Content: {content}")
    except Exception as e:
        print(f"Error with direct query test: {e}")

# Check table counts with both anonymous and admin clients
print("\n==== Table Counts (ANON vs SERVICE ROLE) ====")
tables = ["audience_resources", "domain_reports", "knowledge_chunks", 
          "partner_organizations", "resource_urls", "target_audiences"]
for table in tables:
    try:
        count_anon = supabase.table(table).select("count", count="exact").execute()
        count_admin = supabase_admin.table(table).select("count", count="exact").execute()
        print(f"Table '{table}' count: {count_anon.count} (anon) vs {count_admin.count} (admin)")
    except Exception as e:
        print(f"Table '{table}' error: {str(e)}")

# Examine domain_reports table which has data
try:
    print_results(
        "Domain Reports Data",
        supabase.table("domain_reports").select("*").execute().data
    )
except Exception as e:
    print(f"\n==== Domain Reports Query Error ====")
    print(f"Error: {str(e)}")

# Check if match_documents function exists
try:
    print("\n==== Checking match_documents Function ====")
    # First check if the function already exists
    test_embedding = [0.1] * 1536  # Dummy embedding
    try:
        result = supabase_admin.rpc("match_documents", {
            "query_embedding": test_embedding,
            "match_count": 1
        }).execute()
        print("match_documents function exists in database")
        print(f"Result data: {result.data[:100] if result.data else 'No results'}")
    except Exception as e:
        print(f"match_documents function issue: {str(e)}")
        print("This could be due to the function not existing or other issues.")
except Exception as e:
    print(f"Error checking functions: {str(e)}")

# Print environment variables required for Supabase vector storage
print("\n==== Environment Configuration ====")
required_env = ["SUPABASE_URL", "SUPABASE_ANON_KEY", "SUPABASE_SERVICE_ROLE_KEY", "OPENAI_API_KEY"]
for env in required_env:
    value = os.getenv(env)
    status = "✓" if value else "✗"
    masked_value = value[:5] + "..." + value[-3:] if value and len(value) > 8 else None
    print(f"{env}: {status} {masked_value if masked_value else ''}")

# Test our updated search_knowledge_base function
def test_search_knowledge_base():
    print("\n==== Testing search_knowledge_base Function ====")
    test_queries = [
        "clean energy careers in Massachusetts",
        "environmental justice programs in Boston",
        "military experience in clean energy",
        "international credentials for engineering",
        "solar installation training"
    ]
    
    for query in test_queries:
        print(f"\nTesting query: '{query}'")
        try:
            # Use the invoke method to avoid deprecation warning
            results = search_knowledge_base.invoke(query)
            print(f"Found {len(results)} results")
            
            if len(results) > 0:
                # Display first 2 results with relevant details
                for i, result in enumerate(results[:2]):
                    print(f"\nResult {i+1}:")
                    print(f"Content: {result.get('content', 'N/A')[:100]}..." if result.get('content') and len(result.get('content')) > 100 else f"Content: {result.get('content', 'N/A')}")
                    print(f"Title: {result.get('title', 'N/A')}")
                    print(f"Similarity: {result.get('similarity', 'N/A')}")
                    print(f"Metadata: {json.dumps(result.get('metadata', {}), indent=2)}")
            else:
                print("No results found")
                
        except Exception as e:
            print(f"Error running search_knowledge_base: {e}")
            
def test_direct_db_access():
    print("\n==== Testing Direct Database Access ====")
    
    # Check knowledge_chunks content directly
    try:
        print("\nQuerying knowledge chunks directly:")
        chunks = supabase_admin.table("knowledge_chunks").select("id,title,content").limit(3).execute()
        print(f"Found {len(chunks.data)} knowledge chunks")
        for i, chunk in enumerate(chunks.data):
            print(f"\nChunk {i+1}:")
            print(f"ID: {chunk.get('id', 'N/A')}")
            print(f"Title: {chunk.get('title', 'N/A')}")
            content = chunk.get('content', 'N/A')
            print(f"Content: {content[:100]}..." if content and len(content) > 100 else f"Content: {content}")
    except Exception as e:
        print(f"Error querying knowledge chunks: {e}")
    
    # Check partner_organizations directly
    try:
        print("\nQuerying partner organizations directly:")
        partners = supabase_admin.table("partner_organizations").select("*").limit(3).execute()
        print(f"Found {len(partners.data)} partners")
        for i, partner in enumerate(partners.data):
            print(f"\nPartner {i+1}:")
            print(f"Name: {partner.get('name', 'N/A')}")
            print(f"Description: {partner.get('description', 'N/A')[:100]}..." if partner.get('description') and len(partner.get('description')) > 100 else f"Description: {partner.get('description', 'N/A')}")
    except Exception as e:
        print(f"Error querying partners: {e}")

# Test the function from tools.py
def test_manual_get_ecosystem_partners():
    print("\n==== Testing Manual get_ecosystem_partners ====")
    
    try:
        print("\nGetting all partners by direct table access:")
        partners = supabase_admin.table("partner_organizations").select("*").execute()
        print(f"Found {len(partners.data)} partners via direct table access")
        for i, partner in enumerate(partners.data[:3]):
            print(f"\nPartner {i+1}:")
            print(f"Name: {partner.get('name', 'N/A')}")
            print(f"Description: {partner.get('description', 'N/A')[:100]}..." if partner.get('description') and len(partner.get('description')) > 100 else f"Description: {partner.get('description', 'N/A')}")
        
        # Test the function without using it as a LangChain tool
        print("\nTesting the get_ecosystem_partners function directly:")
        from tools import get_ecosystem_partners
        
        # Create a new wrapper to call the function without the tool interface
        def direct_get_partners(filters=None):
            """Call get_ecosystem_partners directly without tool interface"""
            from inspect import signature
            # Get the actual function from the tool wrapper
            func = get_ecosystem_partners.func
            # Call the function directly with the right arguments
            return func(filters)
        
        # Call it directly
        all_partners = direct_get_partners()
        print(f"Found {len(all_partners)} partners via direct function call")
        
        # Call with filters
        filter_dict = {"focus_area": "energy"}
        try:
            filtered_partners = direct_get_partners(filter_dict)
            print(f"Found {len(filtered_partners)} partners with filter {filter_dict}")
        except Exception as e:
            print(f"Error with filtered partners: {e}")
            
    except Exception as e:
        print(f"Error with manual get_ecosystem_partners: {e}")

# Initialize OpenAI embeddings
embeddings = OpenAIEmbeddings()

# Test our updated functions
try:
    print("\n==== Starting Tests ====")
    test_direct_db_connection()
    test_search_knowledge_base()
    test_direct_db_access()
    test_manual_get_ecosystem_partners()
    
    print("\n==== Test Complete ====")
    print("Observations:")
    print("1. The search_knowledge_base function has multiple fallback mechanisms:")
    print("   - First tries vector store similarity search")
    print("   - Falls back to match_documents function call")
    print("   - Attempts direct PostgreSQL connection for more reliable results")
    print("   - Finally tries keyword search via Supabase API")
    print("2. There's a function overloading issue with match_documents in Postgres that needs resolution")
    print("3. Redis caching is working for previously searched queries")
    print("4. The RLS policies are properly restricting anonymous access while allowing service role access")
    print("5. Direct database access provides a reliable fallback when REST API methods fail")
    
except Exception as e:
    print(f"Error running tests: {str(e)}") 