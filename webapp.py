"""
FastAPI web application for Climate Ecosystem Assistant with custom lifespan events.
"""
import os
import time
from contextlib import asynccontextmanager
import redis
from dotenv import load_dotenv
from fastapi import FastAPI, Depends, Request, HTTPException
from supabase import create_client
from starlette.middleware.base import BaseHTTPMiddleware
# Import auth from our custom auth module instead of creating a new instance
from auth import auth

# Load environment variables
load_dotenv()

# Initialize LangGraph Auth - make sure this is at module level
# auth = Auth()  # Removed this line as we're importing auth from auth.py

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for logging request details and timing.
    """
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Log request details
        print(f"🔹 Request: {request.method} {request.url.path}")
        
        # Process the request
        response = await call_next(request)
        
        # Calculate and log processing time
        process_time = time.time() - start_time
        print(f"🔹 Response: {response.status_code} (took {process_time:.4f}s)")
        
        # Add custom headers
        response.headers["X-Process-Time"] = str(process_time)
        response.headers["X-Climate-Assistant"] = "v1.0"
        
        return response

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifecycle management for the FastAPI application.
    Initializes and cleans up connections to Redis and Supabase.
    """
    print("🚀 Starting Climate Ecosystem Assistant server...")
    
    # Initialize Redis client
    redis_client = redis.Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", 6379)),
        username=os.getenv("REDIS_USERNAME", "default"),
        password=os.getenv("REDIS_PASSWORD"),
        decode_responses=True
    )
    
    # Test Redis connection
    try:
        redis_client.ping()
        print("✅ Redis connection established")
        # Store in app state for use in routes
        app.state.redis = redis_client
    except Exception as e:
        print(f"⚠️ Redis connection failed: {e}")
        app.state.redis = None
    
    # Initialize Supabase client
    try:
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        
        if supabase_url and supabase_key:
            supabase_client = create_client(supabase_url, supabase_key)
            print("✅ Supabase client initialized")
            # Store in app state for use in routes
            app.state.supabase = supabase_client
        else:
            print("⚠️ Supabase environment variables not set")
            app.state.supabase = None
    except Exception as e:
        print(f"⚠️ Supabase initialization failed: {e}")
        app.state.supabase = None
    
    # Yield control back to the server
    yield
    
    # Cleanup connections on shutdown
    print("🛑 Shutting down Climate Ecosystem Assistant server...")
    
    # Clean up Redis connection
    if hasattr(app.state, "redis") and app.state.redis:
        try:
            app.state.redis.close()
            print("✅ Redis connection closed")
        except Exception as e:
            print(f"⚠️ Error closing Redis connection: {e}")
    
    print("✅ All connections cleaned up")

# Create FastAPI app with custom lifespan
app = FastAPI(
    title="Climate Ecosystem Assistant API",
    description="API for the Climate Ecosystem Assistant providing career guidance in the clean energy sector",
    version="1.0.0",
    lifespan=lifespan
)

# Add middleware
app.add_middleware(RequestLoggingMiddleware)

# LangGraph will automatically mount this app
# Make sure any additional routes are added here

# Health check endpoint
@app.get("/health")
async def health_check():
    """
    Health check endpoint to verify the service is running.
    Also checks the status of connected services.
    """
    health_status = {
        "status": "ok",
        "services": {
            "redis": "connected" if app.state.redis else "disconnected",
            "supabase": "connected" if app.state.supabase else "disconnected"
        }
    }
    return health_status

# Example of a protected endpoint using LangGraph Auth
@app.get("/user-info")
async def user_info(request: Request, user=Depends(auth.user_middleware)):
    """
    Protected endpoint that requires authentication.
    Returns the current user's information.
    """
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    return {
        "user_id": user.id,
        "metadata": user.metadata
    }

# Example of how to access state in routes
@app.get("/redis-status")
async def redis_status(request: Request):
    """
    Example of accessing the Redis client from app state.
    """
    if not request.app.state.redis:
        return {"status": "disconnected"}
    
    try:
        # Check if Redis is still responding
        request.app.state.redis.ping()
        return {"status": "connected"}
    except Exception as e:
        return {"status": "error", "message": str(e)} 