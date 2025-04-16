import os
import redis
import json
import time
import uuid
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Redis connection parameters
REDIS_HOST = os.getenv("REDIS_HOST")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_USERNAME = os.getenv("REDIS_USERNAME", "default")
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")

# TTL values for different types of data
SESSION_TTL = 60 * 60 * 24 * 7  # 7 days for sessions
CHAT_HISTORY_TTL = 60 * 60 * 24 * 30  # 30 days for chat history
CACHE_TTL = 60 * 60  # 1 hour for knowledge base cache

# Redis client
def get_redis_client():
    """Get a Redis client connection"""
    if not REDIS_HOST or not REDIS_PASSWORD:
        print("Error: REDIS_HOST and REDIS_PASSWORD must be set in environment variables")
        return None
        
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

# Session Management
class SessionManager:
    """Manage user sessions using Redis"""
    
    def __init__(self, redis_client):
        self.redis = redis_client
        self.prefix = "session:"
    
    def create_session(self, user_id, user_data=None):
        """Create a new session for a user"""
        session_id = str(uuid.uuid4())
        session_key = f"{self.prefix}{session_id}"
        
        session_data = {
            "user_id": user_id,
            "created_at": datetime.now().isoformat(),
            "last_active": datetime.now().isoformat(),
            "data": user_data or {}
        }
        
        # Store session in Redis
        self.redis.setex(
            session_key,
            SESSION_TTL,
            json.dumps(session_data)
        )
        
        # Also maintain a user-to-sessions index
        user_sessions_key = f"user:{user_id}:sessions"
        self.redis.sadd(user_sessions_key, session_id)
        
        print(f"Created session {session_id} for user {user_id}")
        return session_id
    
    def get_session(self, session_id):
        """Get session data by ID"""
        session_key = f"{self.prefix}{session_id}"
        session_data = self.redis.get(session_key)
        
        if not session_data:
            print(f"Session {session_id} not found")
            return None
        
        # Update last active time
        parsed_data = json.loads(session_data)
        parsed_data["last_active"] = datetime.now().isoformat()
        
        # Extend session TTL and update data
        self.redis.setex(
            session_key,
            SESSION_TTL,
            json.dumps(parsed_data)
        )
        
        return parsed_data
    
    def invalidate_session(self, session_id):
        """Invalidate a session"""
        session_key = f"{self.prefix}{session_id}"
        session_data = self.redis.get(session_key)
        
        if session_data:
            parsed_data = json.loads(session_data)
            user_id = parsed_data.get("user_id")
            
            # Remove from user-to-sessions index
            if user_id:
                user_sessions_key = f"user:{user_id}:sessions"
                self.redis.srem(user_sessions_key, session_id)
            
            # Delete session
            self.redis.delete(session_key)
            print(f"Invalidated session {session_id}")
            return True
        
        print(f"Session {session_id} not found for invalidation")
        return False
    
    def get_user_sessions(self, user_id):
        """Get all active sessions for a user"""
        user_sessions_key = f"user:{user_id}:sessions"
        session_ids = self.redis.smembers(user_sessions_key)
        
        sessions = []
        for session_id in session_ids:
            session_data = self.get_session(session_id)
            if session_data:
                sessions.append({
                    "session_id": session_id,
                    **session_data
                })
        
        return sessions

# Chat History Management
class ChatManager:
    """Manage chat history using Redis"""
    
    def __init__(self, redis_client):
        self.redis = redis_client
        self.prefix = "chat:"
    
    def create_chat(self, user_id):
        """Create a new chat for a user"""
        chat_id = str(uuid.uuid4())
        chat_key = f"{self.prefix}{chat_id}"
        
        chat_metadata = {
            "user_id": user_id,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "message_count": 0
        }
        
        # Store chat metadata
        self.redis.setex(
            chat_key,
            CHAT_HISTORY_TTL,
            json.dumps(chat_metadata)
        )
        
        # Add to user's chats
        user_chats_key = f"user:{user_id}:chats"
        self.redis.sadd(user_chats_key, chat_id)
        
        print(f"Created chat {chat_id} for user {user_id}")
        return chat_id
    
    def add_message(self, chat_id, role, content, metadata=None):
        """Add a message to a chat"""
        chat_key = f"{self.prefix}{chat_id}"
        chat_metadata_json = self.redis.get(chat_key)
        
        if not chat_metadata_json:
            print(f"Chat {chat_id} not found")
            return False
        
        chat_metadata = json.loads(chat_metadata_json)
        user_id = chat_metadata.get("user_id")
        
        # Create message
        message_id = str(uuid.uuid4())
        message = {
            "id": message_id,
            "chat_id": chat_id,
            "role": role,  # 'user', 'system', or 'assistant'
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        
        # Store message
        message_key = f"{self.prefix}{chat_id}:messages"
        self.redis.rpush(message_key, json.dumps(message))
        
        # Update chat metadata
        chat_metadata["message_count"] = chat_metadata.get("message_count", 0) + 1
        chat_metadata["updated_at"] = datetime.now().isoformat()
        
        self.redis.setex(
            chat_key,
            CHAT_HISTORY_TTL,
            json.dumps(chat_metadata)
        )
        
        # Extend message TTL
        self.redis.expire(message_key, CHAT_HISTORY_TTL)
        
        return message_id
    
    def get_messages(self, chat_id, limit=50):
        """Get messages from a chat"""
        message_key = f"{self.prefix}{chat_id}:messages"
        
        # Get all messages (or up to the limit from the end)
        message_jsons = self.redis.lrange(message_key, -limit, -1)
        messages = [json.loads(msg) for msg in message_jsons]
        
        return messages
    
    def get_user_chats(self, user_id, include_messages=False):
        """Get all chats for a user"""
        user_chats_key = f"user:{user_id}:chats"
        chat_ids = self.redis.smembers(user_chats_key)
        
        chats = []
        for chat_id in chat_ids:
            chat_key = f"{self.prefix}{chat_id}"
            chat_metadata_json = self.redis.get(chat_key)
            
            if chat_metadata_json:
                chat_metadata = json.loads(chat_metadata_json)
                chat_data = {
                    "chat_id": chat_id,
                    **chat_metadata
                }
                
                if include_messages:
                    chat_data["messages"] = self.get_messages(chat_id)
                
                chats.append(chat_data)
        
        return chats

# Auth-related state in Redis
class AuthStateManager:
    """Manage authentication state in Redis"""
    
    def __init__(self, redis_client):
        self.redis = redis_client
        self.prefix = "auth:"
    
    def store_login_attempt(self, email, ip_address):
        """Store a login attempt"""
        key = f"{self.prefix}login_attempt:{email}:{ip_address}"
        self.redis.incr(key)
        self.redis.expire(key, 60 * 10)  # 10 minutes
    
    def get_login_attempts(self, email, ip_address):
        """Get number of login attempts"""
        key = f"{self.prefix}login_attempt:{email}:{ip_address}"
        count = self.redis.get(key)
        return int(count or 0)
    
    def clear_login_attempts(self, email, ip_address):
        """Clear login attempts after successful login"""
        key = f"{self.prefix}login_attempt:{email}:{ip_address}"
        self.redis.delete(key)
    
    def store_verification_code(self, email, code):
        """Store a verification code for email verification"""
        key = f"{self.prefix}verification:{email}"
        self.redis.setex(key, 60 * 15, code)  # 15 minutes
    
    def verify_code(self, email, code):
        """Verify an email verification code"""
        key = f"{self.prefix}verification:{email}"
        stored_code = self.redis.get(key)
        
        if stored_code and stored_code == code:
            self.redis.delete(key)
            return True
        
        return False

# Connection with API
def simulate_api_flow():
    """Simulate how auth and chat state connect with the API flow"""
    
    redis_client = get_redis_client()
    if not redis_client:
        print("Could not connect to Redis. Exiting.")
        return
    
    session_manager = SessionManager(redis_client)
    chat_manager = ChatManager(redis_client)
    auth_manager = AuthStateManager(redis_client)
    
    # Simulate user login
    print("\n==== User Authentication Flow ====")
    user_id = f"user_{uuid.uuid4().hex[:8]}"
    user_email = f"{user_id}@example.com"
    
    # 1. Failed login attempts tracking
    print("\n1. Tracking login attempts...")
    for i in range(3):
        auth_manager.store_login_attempt(user_email, "192.168.1.1")
        attempts = auth_manager.get_login_attempts(user_email, "192.168.1.1")
        print(f"   Login attempts for {user_email}: {attempts}")
    
    # 2. Create session after successful login
    print("\n2. Creating session after successful login...")
    auth_manager.clear_login_attempts(user_email, "192.168.1.1")
    user_data = {
        "email": user_email,
        "name": f"Test User {user_id}",
        "preferences": {
            "theme": "dark",
            "notifications": True
        }
    }
    session_id = session_manager.create_session(user_id, user_data)
    
    # 3. Use the session
    print("\n3. Using the session...")
    session = session_manager.get_session(session_id)
    print(f"   Session data: {json.dumps(session, indent=2)}")
    
    # Simulate chat history
    print("\n==== Chat History Flow ====")
    
    # 1. Create new chat
    print("\n1. Creating new chat...")
    chat_id = chat_manager.create_chat(user_id)
    
    # 2. Add messages to chat
    print("\n2. Adding messages to chat...")
    chat_manager.add_message(chat_id, "user", "Hello, I'm looking for clean energy careers in Massachusetts")
    chat_manager.add_message(chat_id, "assistant", "I can help you find clean energy careers in Massachusetts. The sector has over 104,000 workers and is growing rapidly.")
    chat_manager.add_message(chat_id, "user", "What kinds of jobs are available?")
    
    system_metadata = {"specialist": "career_advisor", "model": "gpt-4"}
    chat_manager.add_message(chat_id, "assistant", "The top careers include Electricians, Solar Installers, and Energy Efficiency Specialists. Electricians have a median wage of $37/hour in Massachusetts.", system_metadata)
    
    # 3. Retrieve chat history
    print("\n3. Retrieving chat history...")
    messages = chat_manager.get_messages(chat_id)
    print(f"   Chat has {len(messages)} messages:")
    for i, msg in enumerate(messages, 1):
        print(f"   Message {i} - {msg['role']}: {msg['content'][:50]}...")
    
    # 4. List all user's chats
    print("\n4. Listing all user's chats...")
    chats = chat_manager.get_user_chats(user_id)
    print(f"   User has {len(chats)} chats")
    for chat in chats:
        print(f"   - Chat {chat['chat_id']} created at {chat['created_at']} with {chat['message_count']} messages")
    
    # Simulate session management
    print("\n==== Session Management Flow ====")
    
    # 1. Show all user sessions
    print("\n1. Showing all user sessions...")
    sessions = session_manager.get_user_sessions(user_id)
    print(f"   User has {len(sessions)} active sessions")
    
    # 2. Invalidate session (logout)
    print("\n2. Invalidating session (logout)...")
    session_manager.invalidate_session(session_id)
    
    # 3. Check sessions after logout
    print("\n3. Checking sessions after logout...")
    sessions = session_manager.get_user_sessions(user_id)
    print(f"   User has {len(sessions)} active sessions")
    
    # Clean up
    print("\n==== Cleanup ====")
    # Delete test data created during demo
    for key_pattern in [
        f"user:{user_id}:*",
        f"session:*",
        f"chat:{chat_id}*",
        f"auth:*{user_email}*"
    ]:
        keys = redis_client.keys(key_pattern)
        if keys:
            redis_client.delete(*keys)
            print(f"Deleted {len(keys)} keys matching '{key_pattern}'")

# Run the simulation
if __name__ == "__main__":
    simulate_api_flow() 