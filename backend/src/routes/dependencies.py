# routes/dependencies.py
import time
import uuid
import logging
from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from config import settings


logger = logging.getLogger(__name__)


# Rate limiting storage (in production, use Redis)
rate_limit_storage: Dict[str, Dict[str, Any]] = {}

# Security scheme for API key authentication (optional)
security = HTTPBearer(auto_error=False)


def generate_session_id() -> str:
    """Generate unique session ID for tracking"""
    return str(uuid.uuid4())


def get_session_id(request: Request) -> str:
    """Get or create session ID from request"""
    session_id = request.headers.get("X-Session-ID")
    if not session_id:
        session_id = generate_session_id()
    return session_id


def get_client_ip(request: Request) -> str:
    """Get client IP address"""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    return request.client.host if request.client else "unknown"


async def rate_limit_dependency(
    request: Request,
    max_requests: int = 10,
    window_minutes: int = 5
) -> None:
    """
    Rate limiting dependency
    
    Args:
        request: FastAPI request object
        max_requests: Maximum requests allowed in window
        window_minutes: Time window in minutes
    """
    if not settings.ENABLE_RATE_LIMITING:
        return
    
    client_ip = get_client_ip(request)
    current_time = time.time()
    window_start = current_time - (window_minutes * 60)
    
    # Clean old entries
    if client_ip in rate_limit_storage:
        rate_limit_storage[client_ip]["requests"] = [
            req_time for req_time in rate_limit_storage[client_ip]["requests"]
            if req_time > window_start
        ]
    else:
        rate_limit_storage[client_ip] = {"requests": []}
    
    # Check rate limit
    request_count = len(rate_limit_storage[client_ip]["requests"])
    if request_count >= max_requests:
        logger.warning(f"Rate limit exceeded for IP: {client_ip}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "Rate limit exceeded",
                "max_requests": max_requests,
                "window_minutes": window_minutes,
                "retry_after": int(window_minutes * 60)
            },
            headers={"Retry-After": str(window_minutes * 60)}
        )
    
    # Add current request
    rate_limit_storage[client_ip]["requests"].append(current_time)


async def validate_api_key(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[str]:
    """
    Validate API key if authentication is enabled
    
    Returns:
        API key if valid, None if authentication disabled
    """
    if not settings.ENABLE_API_KEY_AUTH:
        return None
    
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    api_key = credentials.credentials
    
    # Validate API key (implement your validation logic)
    if not _is_valid_api_key(api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    return api_key


def _is_valid_api_key(api_key: str) -> bool:
    """
    Validate API key against configured keys
    
    In production, this should check against a database or external service
    """
    if not settings.API_KEYS:
        return True  # No keys configured, allow all
    
    return api_key in settings.API_KEYS


async def validate_file_upload(
    request: Request,
    max_file_size: int = 10 * 1024 * 1024,  # 10MB default
    allowed_types: Optional[list] = None
) -> None:
    """
    Validate file upload constraints
    
    Args:
        request: FastAPI request object
        max_file_size: Maximum file size in bytes
        allowed_types: List of allowed MIME types
    """
    if allowed_types is None:
        allowed_types = ["image/jpeg", "image/png", "image/webp", "image/jpg"]
    
    # Check content length
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > max_file_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size: {max_file_size / 1024 / 1024:.1f}MB"
        )


class RateLimiter:
    """Rate limiter class for different endpoints"""
    
    @staticmethod
    async def translation_rate_limit(request: Request):
        """Rate limit for translation endpoints"""
        await rate_limit_dependency(
            request, 
            max_requests=settings.TRANSLATION_RATE_LIMIT_REQUESTS,
            window_minutes=settings.TRANSLATION_RATE_LIMIT_WINDOW
        )
    
    @staticmethod
    async def preview_rate_limit(request: Request):
        """Rate limit for preview endpoints"""
        await rate_limit_dependency(
            request,
            max_requests=settings.PREVIEW_RATE_LIMIT_REQUESTS,
            window_minutes=settings.PREVIEW_RATE_LIMIT_WINDOW
        )
    
    @staticmethod
    async def batch_rate_limit(request: Request):
        """Rate limit for batch endpoints"""
        await rate_limit_dependency(
            request,
            max_requests=settings.BATCH_RATE_LIMIT_REQUESTS,
            window_minutes=settings.BATCH_RATE_LIMIT_WINDOW
        )


def log_request_info(request: Request) -> None:
    """Log request information for monitoring"""
    client_ip = get_client_ip(request)
    user_agent = request.headers.get("user-agent", "unknown")
    
    logger.info(
        f"Request: {request.method} {request.url.path} "
        f"from {client_ip} - {user_agent}"
    )