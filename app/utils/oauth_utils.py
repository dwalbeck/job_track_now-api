import hashlib
import base64
import secrets
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import jwt, JWTError
from sqlalchemy import text
from ..core.database import SessionLocal
from ..utils.logger import logger


# JWT configuration
# IMPORTANT: In production, SECRET_KEY should be loaded from environment variable
# This ensures the same key is used across all workers
import os
SECRET_KEY = os.getenv("JWT_SECRET_KEY", secrets.token_urlsafe(32))
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
    scope: str,
    user_id: int,
    is_admin: bool
) -> None:
    """
    Store authorization code and associated data in database

    Args:
        code: Authorization code
        username: Authenticated username
        redirect_uri: Callback URI
        code_challenge: PKCE code challenge
        code_challenge_method: PKCE challenge method
        state: CSRF state token
        scope: Requested scope
    """
    db = SessionLocal()
    try:
        # Clean up expired codes first
        cleanup_query = text("""
            DELETE FROM oauth_codes
            WHERE created_at < NOW() - INTERVAL '10 minutes'
        """)
        db.execute(cleanup_query)

        # Insert new authorization code
        insert_query = text("""
            INSERT INTO oauth_codes
            (code, username, redirect_uri, code_challenge, code_challenge_method, state, scope, created_at, used, user_id, is_admin)
            VALUES (:code, :username, :redirect_uri, :code_challenge, :code_challenge_method, :state, :scope, NOW(), FALSE, :user_id, :is_admin)
        """)
        db.execute(insert_query, {
            "code": code,
            "username": username,
            "redirect_uri": redirect_uri,
            "code_challenge": code_challenge,
            "code_challenge_method": code_challenge_method,
            "state": state,
            "scope": scope,
            "user_id": user_id,
            "is_admin": is_admin
        })
        db.commit()
        logger.info(f"Stored authorization code", code_length=len(code), username=username)
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to store authorization code", error=str(e))
        raise
    finally:
        db.close()


def retrieve_authorization_code(code: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve authorization code data from database

    Args:
        code: Authorization code

    Returns:
        Dict containing code data, or None if not found
    """
    db = SessionLocal()
    try:
        # Retrieve code from database with expiration check in SQL
        # This ensures consistent timezone handling by using database's NOW()
        query = text("""
            SELECT code, username, redirect_uri, code_challenge, code_challenge_method,
                   state, scope, created_at, used, used_at, user_id, is_admin,
                   (created_at < NOW() - INTERVAL '10 minutes') as is_expired
            FROM oauth_codes
            WHERE code = :code
        """)
        result = db.execute(query, {"code": code}).first()

        if not result:
            logger.warning(f"Authorization code not found", code_exists=False)
            return None

        # Convert to dict
        code_data = {
            "code": result[0],
            "username": result[1],
            "redirect_uri": result[2],
            "code_challenge": result[3],
            "code_challenge_method": result[4],
            "state": result[5],
            "scope": result[6],
            "created_at": result[7],
            "used": result[8],
            "used_at": result[9],
            "user_id": result[10],
            "is_admin": result[11]
        }

        # Check if code has already been used
        if code_data.get("used"):
            logger.warning(f"Authorization code already used", code_reused=True)
            return None

        # Check if code has expired (using database's calculation for timezone consistency)
        is_expired = result[12]
        if is_expired:
            logger.warning(f"Authorization code expired", code_expired=True)
            return None

        return code_data
    except Exception as e:
        logger.error(f"Failed to retrieve authorization code", error=str(e))
        return None
    finally:
        db.close()


def mark_authorization_code_used(code: str) -> None:
    """
    Mark authorization code as used to prevent reuse

    Args:
        code: Authorization code
    """
    db = SessionLocal()
    try:
        update_query = text("""
            UPDATE oauth_codes
            SET used = TRUE, used_at = NOW()
            WHERE code = :code
        """)
        result = db.execute(update_query, {"code": code})
        db.commit()
        if result.rowcount > 0:
            logger.info(f"Marked authorization code as used")
        else:
            logger.warning(f"Authorization code not found when marking as used")
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to mark authorization code as used", error=str(e))
    finally:
        db.close()


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


def create_access_token(
    username: str,
    scope: str = "all",
    user_id: int = None,
    is_admin: bool = False,
    first_name: str = None,
    last_name: str = None
) -> str:
    """
    Create JWT access token

    Args:
        username: Username to encode in token
        scope: Token scope
        user_id: User's database ID
        is_admin: Whether user is an admin
        first_name: User's first name
        last_name: User's last name

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
        # Note: nbf (not before) removed due to time sync issues between containers
        "jti": str(uuid.uuid4()),  # JWT ID (unique identifier)

        # Custom claims
        "typ": "Bearer",
        "scope": scope,
        "preferred_username": username,
        "email_verified": False,
        "auth_time": int(now.timestamp()),
        "acr": "1",  # Authentication Context Class Reference
        "azp": "job-tracker-client",  # Authorized party

        # User info claims
        "user_id": user_id,
        "is_admin": is_admin,
        "first_name": first_name,
        "last_name": last_name,

        # Realm and resource access
        "realm_access": {
            "roles": ["admin", "user", "job_tracker_user"] if is_admin else ["user", "job_tracker_user"]
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
    logger.info(f"Created access token", username=username, user_id=user_id, is_admin=is_admin, expires=expires.isoformat())

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
        # Disable audience verification since we include 'aud' claim but don't need to validate it
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"verify_aud": False}
        )
        logger.debug(f"Token verified", username=payload.get("preferred_username"))
        return payload
    except JWTError as e:
        logger.warning(f"Token verification failed", error=str(e))
        return None


def cleanup_expired_codes() -> None:
    """
    Remove expired authorization codes from database
    Should be called periodically or is automatically called on new code storage
    """
    db = SessionLocal()
    try:
        delete_query = text("""
            DELETE FROM oauth_codes
            WHERE created_at < NOW() - INTERVAL '10 minutes'
        """)
        result = db.execute(delete_query)
        db.commit()
        if result.rowcount > 0:
            logger.info(f"Cleaned up expired codes", count=result.rowcount)
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to cleanup expired codes", error=str(e))
    finally:
        db.close()
