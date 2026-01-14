import hashlib
import base64
import secrets
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import jwt, JWTError
from ..utils.logger import logger


# In-memory storage for authorization codes and their associated data
# In production, this should use Redis or a database
_auth_codes: Dict[str, Dict[str, Any]] = {}

# JWT configuration
SECRET_KEY = secrets.token_urlsafe(32)  # Generate secure random key
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24


def generate_authorization_code() -> str:
    """
    Generate a secure random authorization code

    Returns:
        str: Authorization code
    """
    return secrets.token_urlsafe(32)


def store_authorization_code(
    code: str,
    username: str,
    redirect_uri: str,
    code_challenge: str,
    code_challenge_method: str,
    state: str,
    scope: str
) -> None:
    """
    Store authorization code and associated data in memory

    Args:
        code: Authorization code
        username: Authenticated username
        redirect_uri: Callback URI
        code_challenge: PKCE code challenge
        code_challenge_method: PKCE challenge method
        state: CSRF state token
        scope: Requested scope
    """
    _auth_codes[code] = {
        "username": username,
        "redirect_uri": redirect_uri,
        "code_challenge": code_challenge,
        "code_challenge_method": code_challenge_method,
        "state": state,
        "scope": scope,
        "created_at": datetime.utcnow(),
        "used": False
    }
    logger.info(f"Stored authorization code", code_length=len(code), username=username)


def retrieve_authorization_code(code: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve authorization code data from memory

    Args:
        code: Authorization code

    Returns:
        Dict containing code data, or None if not found
    """
    code_data = _auth_codes.get(code)

    if not code_data:
        logger.warning(f"Authorization code not found", code_exists=False)
        return None

    # Check if code has already been used
    if code_data.get("used"):
        logger.warning(f"Authorization code already used", code_reused=True)
        return None

    # Check if code has expired (codes expire after 10 minutes)
    created_at = code_data.get("created_at")
    if created_at and datetime.utcnow() - created_at > timedelta(minutes=10):
        logger.warning(f"Authorization code expired", code_expired=True)
        return None

    return code_data


def mark_authorization_code_used(code: str) -> None:
    """
    Mark authorization code as used to prevent reuse

    Args:
        code: Authorization code
    """
    if code in _auth_codes:
        _auth_codes[code]["used"] = True
        logger.info(f"Marked authorization code as used")


def verify_pkce_challenge(code_verifier: str, code_challenge: str, method: str = "S256") -> bool:
    """
    Verify PKCE code verifier against code challenge

    Args:
        code_verifier: Code verifier from client
        code_challenge: Stored code challenge
        method: Challenge method (S256 or plain)

    Returns:
        bool: True if verification succeeds
    """
    if method == "S256":
        # SHA-256 hash the code verifier
        hash_digest = hashlib.sha256(code_verifier.encode('ascii')).digest()
        # Base64 URL encode without padding
        computed_challenge = base64.urlsafe_b64encode(hash_digest).decode('ascii').rstrip('=')

        verified = computed_challenge == code_challenge
        logger.info(f"PKCE verification", method=method, verified=verified)
        return verified
    elif method == "plain":
        # Plain method (not recommended but supported)
        verified = code_verifier == code_challenge
        logger.info(f"PKCE verification", method=method, verified=verified)
        return verified
    else:
        logger.error(f"Unsupported PKCE method", method=method)
        return False


def create_access_token(username: str, scope: str = "all") -> str:
    """
    Create JWT access token

    Args:
        username: Username to encode in token
        scope: Token scope

    Returns:
        str: Signed JWT token
    """
    now = datetime.utcnow()
    expires = now + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)

    # Build JWT payload similar to the example provided
    payload = {
        # Standard claims
        "sub": username,  # Subject (user identifier)
        "iss": "job-track-now-api",  # Issuer
        "aud": "account",  # Audience
        "iat": int(now.timestamp()),  # Issued at
        "exp": int(expires.timestamp()),  # Expiration
        "nbf": int(now.timestamp()),  # Not before
        "jti": str(uuid.uuid4()),  # JWT ID (unique identifier)

        # Custom claims
        "typ": "Bearer",
        "scope": scope,
        "preferred_username": username,
        "email_verified": False,
        "auth_time": int(now.timestamp()),
        "acr": "1",  # Authentication Context Class Reference
        "azp": "job-tracker-client",  # Authorized party

        # Realm and resource access
        "realm_access": {
            "roles": ["user", "job_tracker_user"]
        },
        "resource_access": {
            "account": {
                "roles": ["manage-account", "view-profile"]
            }
        },
        "session_state": str(uuid.uuid4())
    }

    # Sign the JWT
    encoded_jwt = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    logger.info(f"Created access token", username=username, expires=expires.isoformat())

    return encoded_jwt


def verify_access_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verify and decode JWT access token

    Args:
        token: JWT token string

    Returns:
        Dict containing token payload, or None if invalid
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        logger.debug(f"Token verified", username=payload.get("preferred_username"))
        return payload
    except JWTError as e:
        logger.warning(f"Token verification failed", error=str(e))
        return None


def cleanup_expired_codes() -> None:
    """
    Remove expired authorization codes from memory
    Should be called periodically
    """
    now = datetime.utcnow()
    expired_codes = [
        code for code, data in _auth_codes.items()
        if data.get("created_at") and now - data["created_at"] > timedelta(minutes=10)
    ]

    for code in expired_codes:
        del _auth_codes[code]

    if expired_codes:
        logger.info(f"Cleaned up expired codes", count=len(expired_codes))
