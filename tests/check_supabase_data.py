import os
import json
import sys
from dotenv import load_dotenv
from supabase import create_client
import psycopg2
from psycopg2.extras import RealDictCursor

# Load environment variables
load_dotenv()

# Initialize Supabase client with service role key for admin access
try:
    supabase = create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    )
    print("✅ Supabase client initialized successfully")
except Exception as e:
    print(f"❌ Failed to initialize Supabase client: {e}")
    sys.exit(1)

# Direct database connection parameters
DB_USER = os.getenv("user")
DB_PASSWORD = os.getenv("password")
DB_HOST = os.getenv("host")
DB_PORT = os.getenv("port")
DB_NAME = os.getenv("dbname", "postgres")

def get_db_connection():
    """Get a direct database connection, bypassing Supabase API"""
    if not all([DB_USER, DB_PASSWORD, DB_HOST, DB_PORT]):
        print("❌ Database connection parameters are missing from environment variables")
        return None
        
    try:
        connection = psycopg2.connect(
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME
        )
        print("✅ Direct PostgreSQL connection successful")
        return connection
    except Exception as e:
        print(f"❌ Failed to connect directly to database: {e}")
        return None

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
        print(f"❌ Error executing direct query: {e}")
        if connection:
            connection.close()
        return []

def print_table_data(table_name, limit=5):
    """Print data from a table"""
    try:
        result = supabase.table(table_name).select("*").limit(limit).execute()
        count = supabase.table(table_name).select("count", count="exact").execute()
        
        print(f"\n=== {table_name.upper()} ===")
        print(f"Total records: {count.count}")
        
        if result.data:
            print("\nSample data:")
            for i, item in enumerate(result.data):
                print(f"\nItem {i+1}:")
                # Print a cleaner version for readability
                clean_item = {k: v for k, v in item.items() if k not in ["created_at", "updated_at", "id"]}
                print(json.dumps(clean_item, indent=2, default=str))
        else:
            print("No data found via Supabase API")
            
            # Try direct database access as fallback
            print("Trying direct database access...")
            direct_query = f"SELECT * FROM {table_name} LIMIT {limit};"
            direct_results = direct_db_query(direct_query)
            
            if direct_results:
                print(f"Found {len(direct_results)} records via direct database access:")
                for i, item in enumerate(direct_results):
                    print(f"\nItem {i+1}:")
                    # Print a cleaner version for readability
                    clean_item = {k: v for k, v in item.items() if k not in ["created_at", "updated_at", "id"]}
                    print(json.dumps(clean_item, indent=2, default=str))
            else:
                print("No data found via direct database access either")
    except Exception as e:
        print(f"❌ Error querying {table_name}: {e}")
        
        # Try direct database access as fallback
        print("Trying direct database access...")
        direct_query = f"SELECT * FROM {table_name} LIMIT {limit};"
        direct_results = direct_db_query(direct_query)
        
        if direct_results:
            print(f"Found {len(direct_results)} records via direct database access:")
            for i, item in enumerate(direct_results):
                print(f"\nItem {i+1}:")
                # Print a cleaner version for readability
                clean_item = {k: v for k, v in item.items() if k not in ["created_at", "updated_at", "id"]}
                print(json.dumps(clean_item, indent=2, default=str))
        else:
            print("No data found via direct database access either")

def test_knowledge_base_search(query="clean energy careers"):
    """Test if knowledge_base search function exists"""
    try:
        print(f"\n=== TESTING KNOWLEDGE BASE SEARCH ===")
        print(f"Query: '{query}'")
        
        # First try with search_knowledge_base function
        try:
            response = supabase.rpc(
                'search_knowledge_base',
                {'search_query': query}
            ).execute()
            
            if response.data:
                print(f"✅ search_knowledge_base function works! Found {len(response.data)} results:")
                for i, item in enumerate(response.data[:3]):
                    print(f"\nResult {i+1}:")
                    print(json.dumps(item, indent=2, default=str))
                return
            else:
                print("No results found with search_knowledge_base function")
        except Exception as e:
            print(f"❌ Error using search_knowledge_base function: {e}")
        
        # Try with match_documents function if search_knowledge_base fails
        try:
            print("\nTrying match_documents function instead...")
            
            # This requires embeddings, which we don't have here
            # Let's try direct SQL query as fallback
            print("\nUsing direct SQL query with keyword search as fallback...")
            
            sql_query = f"""
                SELECT id, title, content, summary, metadata
                FROM knowledge_chunks
                WHERE content ILIKE '%{query}%' OR title ILIKE '%{query}%'
                LIMIT 5;
            """
            
            direct_results = direct_db_query(sql_query)
            
            if direct_results:
                print(f"✅ Found {len(direct_results)} results via direct SQL:")
                for i, item in enumerate(direct_results):
                    print(f"\nResult {i+1}:")
                    print(json.dumps(item, indent=2, default=str))
            else:
                print("No results found via direct SQL either")
                
        except Exception as e:
            print(f"❌ Error with direct SQL search: {e}")
            
    except Exception as e:
        print(f"❌ Error testing knowledge base search: {e}")

def check_postgres_functions():
    """Check if required PostgreSQL functions exist"""
    print("\n=== CHECKING POSTGRESQL FUNCTIONS ===")
    
    functions_to_check = [
        "match_documents",
        "search_knowledge_base",
        "langchain_match_documents"
    ]
    
    # SQL to check function existence
    sql = """
    SELECT p.proname AS function_name,
           pg_get_function_arguments(p.oid) AS argument_data_types,
           pg_get_function_result(p.oid) AS result_data_type
    FROM pg_proc p
    JOIN pg_namespace n ON p.pronamespace = n.oid
    WHERE n.nspname = 'public' AND p.proname = %s;
    """
    
    conn = get_db_connection()
    if not conn:
        print("❌ Cannot check PostgreSQL functions without database connection")
        return
    
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        for func_name in functions_to_check:
            cursor.execute(sql, (func_name,))
            results = cursor.fetchall()
            
            if results:
                print(f"✅ Function '{func_name}' exists with {len(results)} overloads:")
                for i, func in enumerate(results):
                    print(f"  {i+1}. {func['function_name']}({func['argument_data_types']}) RETURNS {func['result_data_type']}")
            else:
                print(f"❌ Function '{func_name}' does not exist")
        
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"❌ Error checking PostgreSQL functions: {e}")
        if conn:
            conn.close()

def check_schema_tables():
    """Check database schema and list all tables"""
    print("\n=== CHECKING DATABASE SCHEMA ===")
    
    # SQL to list all tables in public schema
    sql = """
    SELECT table_name
    FROM information_schema.tables
    WHERE table_schema = 'public'
    ORDER BY table_name;
    """
    
    results = direct_db_query(sql)
    
    if results:
        print(f"Found {len(results)} tables in public schema:")
        for i, table in enumerate(results):
            print(f"  {i+1}. {table['table_name']}")
    else:
        print("No tables found or error accessing schema information")

def main():
    """Check all tables and functions in the database"""
    print("\n=== SUPABASE DATABASE CHECK ===")
    print(f"URL: {os.getenv('SUPABASE_URL')}")
    print(f"Service Role Key: {os.getenv('SUPABASE_SERVICE_ROLE_KEY')[:10]}..." if os.getenv('SUPABASE_SERVICE_ROLE_KEY') else "Not set")
    
    # Check database schema first
    check_schema_tables()
    
    # Check PostgreSQL functions
    check_postgres_functions()
    
    # Check tables
    tables = [
        "partner_organizations", 
        "target_audiences",
        "audience_resources",
        "domain_reports",
        "knowledge_chunks",
        "resource_urls"
    ]
    
    for table in tables:
        print_table_data(table)
    
    # Test knowledge base search functionality
    test_knowledge_base_search("clean energy careers in Massachusetts")
    
    print("\n=== CHECK COMPLETE ===")

if __name__ == "__main__":
    main() 