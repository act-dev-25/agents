"""Authentication module for the Climate Ecosystem Assistant."""
import os
from datetime import timedelta

import httpx
import jwt
from jwt.exceptions import InvalidTokenError
from dotenv import load_dotenv
from langgraph_sdk import Auth

# Load environment variables
load_dotenv()

# Supabase JWT configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
JWT_SECRET = os.getenv("JWT_SECRET")
ALGORITHM = "HS256"

AUTH_EXCEPTION = Auth.exceptions.HTTPException(
    status_code=401,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)

# Create a global auth instance
auth = Auth()

@auth.authenticate
async def get_current_user(
    authorization: str | None,  # "Bearer <token>"
) -> tuple[list[str], Auth.types.MinimalUserDict]:
    """Authenticate the user's JWT token."""
    if not authorization:
        raise AUTH_EXCEPTION
    
    try:
        token = authorization.split(" ", 1)[1]
        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[ALGORITHM],
            audience="authenticated",
            leeway=timedelta(seconds=60),
        )

        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(
                f"{SUPABASE_URL}/auth/v1/user",
                headers={
                    "Authorization": f"Bearer {token}",
                    "apikey": SUPABASE_SERVICE_KEY,
                },
            )
    except (IndexError, InvalidTokenError, ConnectionError) as e:
        raise AUTH_EXCEPTION from e
    
    if response.status_code != 200:
        raise AUTH_EXCEPTION

    user_data = response.json()
    scopes = [payload.get("role", "authenticated")]

    return scopes, {
        "identity": user_data["id"],
        "display_name": user_data.get("user_metadata", {}).get("full_name"),
        "is_authenticated": True,
    }

@auth.on
async def add_owner(
    ctx: Auth.types.AuthContext,
    value: dict,
):
    """Add the owner to the resource metadata and return filters."""
    filters = {"owner": ctx.user.identity}
    metadata = value.setdefault("metadata", {})
    metadata.update(filters)
    return filters
