import os
import redis
import json
import time
import random
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

# Redis connection parameters
REDIS_HOST = os.getenv("REDIS_HOST")
REDIS_PORT = int(os.getenv("REDIS_PORT", "12673"))
REDIS_USERNAME = os.getenv("REDIS_USERNAME", "default")
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")
REDIS_CACHE_TTL = int(os.getenv("REDIS_CACHE_TTL", "3600"))  # 1 hour default TTL

# Initialize Redis client
def get_redis_client():
    """Get a Redis client connection"""
    try:
        client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            username=REDIS_USERNAME,
            password=REDIS_PASSWORD,
            decode_responses=True
        )
        # Test connection
        client.ping()
        return client
    except Exception as e:
        print(f"Error connecting to Redis: {e}")
        return None

# Mock knowledge base search function (simulates database query)
def search_knowledge_base(query, use_cache=True):
    """
    Search knowledge base with caching
    
    Args:
        query: The search query
        use_cache: Whether to use Redis cache
        
    Returns:
        List of search results
    """
    start_time = time.time()
    cache_key = f"kb_search:{query}"
    redis_client = get_redis_client()
    
    # Try to get from cache first
    if use_cache and redis_client:
        cached_result = redis_client.get(cache_key)
        if cached_result:
            results = json.loads(cached_result)
            elapsed = time.time() - start_time
            print(f"✅ CACHE HIT: Retrieved results from cache in {elapsed:.4f} seconds")
            print(f"🔑 Cache key: {cache_key}")
            return results
    
    print("⏳ Cache miss or cache disabled. Performing database search...")
    
    # Simulate database search (slow operation)
    time.sleep(1.5)  # Simulate slow database query
    
    # Generate mock results based on the query
    results = []
    
    # Some predefined queries for demo purposes
    if "clean energy" in query.lower():
        results = [
            {
                "id": f"doc-{random.randint(1000, 9999)}",
                "title": "Clean Energy Careers in Massachusetts",
                "content": "Massachusetts is a leader in clean energy jobs, with over 104,000 workers in the sector.",
                "similarity": round(random.uniform(0.85, 0.99), 2)
            },
            {
                "id": f"doc-{random.randint(1000, 9999)}",
                "title": "Renewable Energy Growth",
                "content": "The clean energy sector has grown 73% since 2010, contributing to job creation.",
                "similarity": round(random.uniform(0.75, 0.95), 2)
            }
        ]
    elif "solar" in query.lower():
        results = [
            {
                "id": f"doc-{random.randint(1000, 9999)}",
                "title": "Solar Installation Career Path",
                "content": "Solar photovoltaic installers are projected to see 40% job growth by 2030.",
                "similarity": round(random.uniform(0.85, 0.99), 2)
            }
        ]
    elif "veteran" in query.lower():
        results = [
            {
                "id": f"doc-{random.randint(1000, 9999)}",
                "title": "Veterans in Clean Energy",
                "content": "Programs to help veterans transition to careers in the clean energy sector.",
                "similarity": round(random.uniform(0.85, 0.99), 2)
            }
        ]
    else:
        results = [
            {
                "id": f"doc-{random.randint(1000, 9999)}",
                "title": "General Energy Information",
                "content": f"General information about '{query}'",
                "similarity": round(random.uniform(0.60, 0.85), 2)
            }
        ]
    
    # Store in cache if Redis is available
    if redis_client and use_cache:
        try:
            redis_client.setex(
                cache_key,
                REDIS_CACHE_TTL,
                json.dumps(results)
            )
            print(f"📝 Cached results for {REDIS_CACHE_TTL} seconds")
        except Exception as e:
            print(f"⚠️ Error caching results: {e}")
    
    elapsed = time.time() - start_time
    print(f"🔍 Database search completed in {elapsed:.4f} seconds")
    
    return results

def clear_cache_for_query(query):
    """Clear the cache for a specific query"""
    redis_client = get_redis_client()
    if redis_client:
        cache_key = f"kb_search:{query}"
        redis_client.delete(cache_key)
        print(f"🧹 Cleared cache for key: {cache_key}")

def list_cache_keys(pattern="kb_search:*"):
    """List all cache keys matching a pattern"""
    redis_client = get_redis_client()
    if redis_client:
        keys = redis_client.keys(pattern)
        print(f"\n📋 Found {len(keys)} cached keys matching '{pattern}':")
        for i, key in enumerate(keys, 1):
            ttl = redis_client.ttl(key)
            value = redis_client.get(key)
            if value:
                try:
                    results = json.loads(value)
                    result_count = len(results) if isinstance(results, list) else 1
                    print(f"{i}. {key} - TTL: {ttl}s - {result_count} result(s)")
                except:
                    print(f"{i}. {key} - TTL: {ttl}s - (Invalid JSON)")
            else:
                print(f"{i}. {key} - TTL: {ttl}s - (No value)")
        return keys
    return []

def demo_caching():
    """Run a demonstration of Redis caching"""
    print("\n===== REDIS CACHING DEMONSTRATION =====")
    print(f"Using Redis at {REDIS_HOST}:{REDIS_PORT}")
    print(f"Default cache TTL: {REDIS_CACHE_TTL} seconds")
    print("=======================================\n")
    
    # List of test queries
    test_queries = [
        "clean energy careers in Massachusetts",
        "solar installation jobs",
        "veteran transition to clean energy",
        "environmental justice in clean energy"
    ]
    
    # First run - should be cache misses
    print("\n🔄 FIRST RUN - NO CACHE")
    print("------------------------")
    for query in test_queries:
        print(f"\n📊 Query: '{query}'")
        results = search_knowledge_base(query)
        print(f"Found {len(results)} results:")
        for i, result in enumerate(results, 1):
            print(f"  {i}. {result['title']} (Similarity: {result['similarity']})")
    
    # Second run - should be cache hits
    print("\n\n🔄 SECOND RUN - SHOULD USE CACHE")
    print("-------------------------------")
    for query in test_queries:
        print(f"\n📊 Query: '{query}'")
        results = search_knowledge_base(query)
        print(f"Found {len(results)} results:")
        for i, result in enumerate(results, 1):
            print(f"  {i}. {result['title']} (Similarity: {result['similarity']})")
    
    # List all cache keys
    list_cache_keys()
    
    # Clear cache for one query
    print("\n\n🧹 CLEARING CACHE FOR ONE QUERY")
    clear_cache_for_query(test_queries[0])
    
    # Third run - mixed cache hits and misses
    print("\n\n🔄 THIRD RUN - MIXED CACHE HITS/MISSES")
    print("------------------------------------")
    for query in test_queries:
        print(f"\n📊 Query: '{query}'")
        results = search_knowledge_base(query)
        print(f"Found {len(results)} results:")
        for i, result in enumerate(results, 1):
            print(f"  {i}. {result['title']} (Similarity: {result['similarity']})")
    
    # Show final cache state
    list_cache_keys()
    
    print("\n===== DEMONSTRATION COMPLETE =====")

if __name__ == "__main__":
    # Run the caching demonstration
    demo_caching() 