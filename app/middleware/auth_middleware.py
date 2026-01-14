from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, Dict, Any

from ..utils.oauth_utils import verify_access_token
from ..utils.logger import logger


# HTTP Bearer token security scheme
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Dict[str, Any]:
    """
    Dependency to validate JWT token and extract user information

    Args:
        credentials: Bearer token from Authorization header

    Returns:
        Dict containing decoded token payload

    Raises:
        HTTPException: If token is missing or invalid
    """
    if not credentials:
        logger.warning("Missing authorization header")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    # Verify and decode token
    payload = verify_access_token(token)

    if not payload:
        logger.warning("Invalid token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    logger.debug("User authenticated", username=payload.get("preferred_username"))
    return payload


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[Dict[str, Any]]:
    """
    Optional authentication dependency - does not raise error if token is missing

    Args:
        credentials: Bearer token from Authorization header

    Returns:
        Dict containing decoded token payload, or None if not authenticated
    """
    if not credentials:
        return None

    token = credentials.credentials
    payload = verify_access_token(token)

    if payload:
        logger.debug("User authenticated (optional)", username=payload.get("preferred_username"))

    return payload


def require_scope(required_scope: str):
    """
    Dependency factory to require specific scope in token

    Args:
        required_scope: Required scope string

    Returns:
        Dependency function that validates scope
    """
    async def scope_checker(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        token_scope = current_user.get("scope", "")

        if required_scope not in token_scope.split():
            logger.warning("Insufficient scope",
                          required=required_scope,
                          provided=token_scope)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )

        return current_user

    return scope_checker
