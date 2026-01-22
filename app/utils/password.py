"""
Password hashing utilities using passlib with bcrypt.

This module provides secure password hashing and verification functions.
Bcrypt is used as it's designed for password hashing with built-in salt generation.
"""

from passlib.context import CryptContext
from ..utils.logger import logger

# Create password context with bcrypt
# bcrypt automatically handles salt generation and storage
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.

    Args:
        password: Plain text password to hash

    Returns:
        Hashed password string (includes salt, can be stored directly)
    """
    hashed = pwd_context.hash(password)
    logger.debug("Password hashed successfully")
    return hashed


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against a hashed password.

    Args:
        plain_password: Plain text password to verify
        hashed_password: Hashed password to check against

    Returns:
        True if password matches, False otherwise
    """
    try:
        result = pwd_context.verify(plain_password, hashed_password)
        logger.debug("Password verification completed", verified=result)
        return result
    except Exception as e:
        logger.error("Password verification failed", error=str(e))
        return False
