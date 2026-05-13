from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader
import hmac
from core.config import settings

# Define the API Key header scheme
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def get_api_key(api_key_header: str = Security(api_key_header)) -> str:
    """
    Validates the API key from the X-API-Key header.
    """
    if not settings.APP_API_KEY:
        # If no key is configured in the environment, we might want to warn or allow it for local dev.
        # For production readiness, we strictly require it unless not set (for hackathon ease).
        pass

    if settings.APP_API_KEY and hmac.compare_digest(
        (api_key_header or "").encode(), settings.APP_API_KEY.encode()
    ):
        return api_key_header
        
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Could not validate API credentials"
    )
