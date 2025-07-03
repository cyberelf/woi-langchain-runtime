"""Authentication middleware for runtime token validation."""


from fastapi import HTTPException, Request, status

from .config import settings


class RuntimeTokenAuth:
    """Runtime token authentication."""
    
    def __init__(self) -> None:
        self.token = settings.runtime_token
    
    def verify_token(self, token: str) -> bool:
        """Verify runtime token."""
        return token == self.token
    
    def __call__(self, request: Request) -> bool:
        """Validate runtime token from request headers."""
        token = request.headers.get("X-Runtime-Token")
        
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing X-Runtime-Token header",
            )
        
        if not self.verify_token(token):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid runtime token",
            )
        
        return True


# Global auth instance
runtime_auth = RuntimeTokenAuth() 