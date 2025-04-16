import os
import redis
from dotenv import load_dotenv
import json
import time

# Load environment variables
load_dotenv()

# Redis connection parameters
REDIS_HOST = os.getenv("REDIS_HOST")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_USERNAME = os.getenv("REDIS_USERNAME", "default")
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")
REDIS_CACHE_TTL = int(os.getenv("REDIS_CACHE_TTL", "3600"))  # 1 hour default TTL

def test_redis_connection():
    """Test connection to Redis and basic operations"""
    if not REDIS_HOST or not REDIS_PASSWORD:
        print("❌ Error: REDIS_HOST and REDIS_PASSWORD must be set in environment variables")
        return False
        
    print(f"Connecting to Redis at {REDIS_HOST}:{REDIS_PORT}...")
    
    try:
        # Initialize Redis client
        redis_client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            username=REDIS_USERNAME,
            password=REDIS_PASSWORD,
            decode_responses=True  # Automatically decode responses to strings
        )
        
        # Test connection with ping
        response = redis_client.ping()
        print(f"Connection test (ping): {'✅ Successful' if response else '❌ Failed'}")
        
        # Test setting a value
        test_key = "test_connection_key"
        test_value = {
            "message": "Hello from Redis!",
            "timestamp": time.time(),
            "test": True
        }
        
        # Set value
        redis_client.setex(
            test_key,
            REDIS_CACHE_TTL,
            json.dumps(test_value)
        )
        print(f"Set value test: ✅ Successful")
        
        # Get value back
        retrieved_value = redis_client.get(test_key)
        if retrieved_value:
            parsed_value = json.loads(retrieved_value)
            print(f"Get value test: ✅ Successful")
            print(f"Retrieved value: {json.dumps(parsed_value, indent=2)}")
        else:
            print(f"Get value test: ❌ Failed")
        
        # Get server info
        info = redis_client.info()
        print("\nRedis Server Information:")
        print(f"Redis Version: {info.get('redis_version', 'Unknown')}")
        print(f"Connected Clients: {info.get('connected_clients', 'Unknown')}")
        print(f"Memory Used: {info.get('used_memory_human', 'Unknown')}")
        print(f"Total Keys: {sum(info.get(f'db{i}', {}).get('keys', 0) for i in range(16) if f'db{i}' in info)}")
        
        # Test cache operations for knowledge base search
        kb_cache_key = "kb_search:clean energy careers in Massachusetts"
        kb_test_value = [
            {
                "id": "test-id-1",
                "title": "Clean Energy Careers",
                "content": "Massachusetts has many opportunities in clean energy.",
                "similarity": 0.95
            }
        ]
        
        # Set and get KB cache
        redis_client.setex(kb_cache_key, REDIS_CACHE_TTL, json.dumps(kb_test_value))
        cached_kb_result = redis_client.get(kb_cache_key)
        if cached_kb_result:
            print("\nKnowledge Base Cache Test: ✅ Successful")
            print(f"Cached KB Result: {json.loads(cached_kb_result)[0]['title']}")
        
        # Clean up test keys
        redis_client.delete(test_key)
        redis_client.delete(kb_cache_key)
        print("\nTest keys cleaned up")
        
        return True
    
    except redis.RedisError as e:
        print(f"❌ Redis Error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")
        return False

if __name__ == "__main__":
    success = test_redis_connection()
    print(f"\nOverall Redis Connection Test: {'✅ Successful' if success else '❌ Failed'}") 