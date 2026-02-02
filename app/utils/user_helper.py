"""
User helper functions for retrieving user information and settings.

This module provides helper functions to query user data from the normalized
user tables (users, user_address, address, user_detail, user_setting) instead
of the legacy personal table.
"""
from typing import Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import text
from .logger import logger


def get_user_info(db: Session, user_id: int) -> Optional[Dict[str, Any]]:
    """
    Get the user's information including address and details.

    Retrieves user data from users, user_address, address, and user_detail tables
    using a LEFT JOIN to include users without addresses or details.

    Args:
        db: Database session
        user_id: The user's ID

    Returns:
        Dictionary containing user info or None if user not found:
        {
            'user_id': int,
            'first_name': str,
            'last_name': str,
            'login': str,
            'email': str,
            'is_admin': bool,
            'phone': str,
            'linkedin_url': str,
            'github_url': str,
            'website_url': str,
            'portfolio_url': str,
            'address_1': str,
            'address_2': str,
            'city': str,
            'state': str,
            'zip': str,
            'country': str
        }
    """
    try:
        query = text("""
            SELECT u.user_id, u.first_name, u.last_name, u.login, u.email, u.is_admin,
                   ud.phone, ud.linkedin_url, ud.github_url, ud.website_url, ud.portfolio_url,
                   a.address_1, a.address_2, a.city, a.state, a.zip, a.country
            FROM users u
            LEFT JOIN user_address ua ON (u.user_id = ua.user_id AND ua.is_default = true)
            LEFT JOIN address a ON (ua.address_id = a.address_id)
            LEFT JOIN user_detail ud ON (u.user_id = ud.user_id)
            WHERE u.user_id = :user_id
        """)
        result = db.execute(query, {"user_id": user_id}).first()

        if result:
            return {
                "user_id": result.user_id,
                "first_name": result.first_name or "",
                "last_name": result.last_name or "",
                "login": result.login or "",
                "email": result.email or "",
                "is_admin": result.is_admin or False,
                "phone": result.phone or "",
                "linkedin_url": result.linkedin_url or "",
                "github_url": result.github_url or "",
                "website_url": result.website_url or "",
                "portfolio_url": result.portfolio_url or "",
                "address_1": result.address_1 or "",
                "address_2": result.address_2 or "",
                "city": result.city or "",
                "state": result.state or "",
                "zip": result.zip or "",
                "country": result.country or ""
            }
        return None

    except Exception as e:
        logger.error(f"Error fetching user info", user_id=user_id, error=str(e))
        return None


def get_user_settings(db: Session, user_id: int) -> Optional[Dict[str, Any]]:
    """
    Get the user's site settings.

    Retrieves settings from the user_setting table for the specified user.

    Args:
        db: Database session
        user_id: The user's ID

    Returns:
        Dictionary containing user settings or None if not found:
        {
            'user_id': int,
            'no_response_week': int,
            'default_llm': str,
            'resume_extract_llm': str,
            'job_extract_llm': str,
            'rewrite_llm': str,
            'cover_llm': str,
            'company_llm': str,
            'tools_llm': str,
            'openai_api_key': str,
            'tinymce_api_key': str,
            'convertapi_key': str,
            'docx2html': str,
            'odt2html': str,
            'pdf2html': str,
            'html2docx': str,
            'html2odt': str,
            'html2pdf': str
        }
    """
    try:
        query = text("""
            SELECT user_id, no_response_week,
                   default_llm, resume_extract_llm, job_extract_llm, rewrite_llm,
                   cover_llm, company_llm, tools_llm,
                   openai_api_key, tinymce_api_key, convertapi_key,
                   docx2html, odt2html, pdf2html, html2docx, html2odt, html2pdf
            FROM user_setting
            WHERE user_id = :user_id
        """)
        result = db.execute(query, {"user_id": user_id}).first()

        if result:
            return {
                "user_id": result.user_id,
                "no_response_week": result.no_response_week or 6,
                "default_llm": result.default_llm or "gpt-4.1-mini",
                "resume_extract_llm": result.resume_extract_llm or "gpt-4.1-mini",
                "job_extract_llm": result.job_extract_llm or "gpt-4.1-mini",
                "rewrite_llm": result.rewrite_llm or "gpt-5.2",
                "cover_llm": result.cover_llm or "gpt-4.1-mini",
                "company_llm": result.company_llm or "gpt-5.2",
                "tools_llm": result.tools_llm or "gpt-4o-mini",
                "openai_api_key": result.openai_api_key or "",
                "tinymce_api_key": result.tinymce_api_key or "",
                "convertapi_key": result.convertapi_key or "",
                "docx2html": result.docx2html or "docx-parser-converter",
                "odt2html": result.odt2html or "pandoc",
                "pdf2html": result.pdf2html or "markitdown",
                "html2docx": result.html2docx or "html4docx",
                "html2odt": result.html2odt or "pandoc",
                "html2pdf": result.html2pdf or "weasyprint"
            }
        logger.error(f"Failed to query user settings", user_id=user_id)
        return None

    except Exception as e:
        logger.error(f"Error fetching user settings", user_id=user_id, error=str(e))
        return None


def get_user_name(db: Session, user_id: int) -> str:
    """
    Get the user's first and last name.

    A convenience function for getting just the name when that's all that's needed.

    Args:
        db: Database session
        user_id: The user's ID

    Returns:
        Tuple of (first_name, last_name). Returns empty strings if not found.
    """
    try:
        query = text("""
            SELECT first_name, last_name
            FROM users
            WHERE user_id = :user_id
        """)
        result = db.execute(query, {"user_id": user_id}).first()

        if result:
            ret = result.first_name or ""
            ret += result.last_name or ""
            return ret
        return ""

    except Exception as e:
        logger.error(f"Error fetching user name", user_id=user_id, error=str(e))
        return ''


def get_user_setting_value(db: Session, user_id: int, setting_name: str) -> Optional[str]:
    """
    Get a specific setting value for a user.

    Args:
        db: Database session
        user_id: The user's ID
        setting_name: The name of the setting column to retrieve

    Returns:
        The setting value as a string, or None if not found
    """
    # Whitelist of allowed setting names to prevent SQL injection
    allowed_settings = {
        'no_response_week', 'default_llm', 'resume_extract_llm', 'job_extract_llm',
        'rewrite_llm', 'cover_llm', 'company_llm', 'tools_llm',
        'openai_api_key', 'tinymce_api_key', 'convertapi_key',
        'docx2html', 'odt2html', 'pdf2html', 'html2docx', 'html2odt', 'html2pdf'
    }

    if setting_name not in allowed_settings:
        logger.error(f"Invalid setting name requested", setting_name=setting_name)
        return None

    try:
        query = text(f"SELECT {setting_name} FROM user_setting WHERE user_id = :user_id")
        result = db.execute(query, {"user_id": user_id}).first()

        if result:
            return getattr(result, setting_name, None)
        return None

    except Exception as e:
        logger.error(f"Error fetching user setting", user_id=user_id, setting_name=setting_name, error=str(e))
        return None


