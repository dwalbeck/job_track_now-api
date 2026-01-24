import re
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text

from ..core.database import get_db
from ..schemas.personal import Personal, PersonalCreate, PersonalUpdate
from ..utils.logger import logger
from ..utils.user_helper import get_user_info, get_user_settings
from ..middleware.auth_middleware import get_current_user

router = APIRouter()


def format_phone_number(phone: str) -> str:
    """
    Format phone number to a standard format.
    Removes all non-digit characters and formats as (XXX) XXX-XXXX if 10 digits.

    Args:
        phone: Raw phone number string

    Returns:
        Formatted phone number
    """
    if not phone:
        return phone

    # Remove all non-digit characters
    digits = re.sub(r'\D', '', phone)

    # Format based on length
    if len(digits) == 10:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    elif len(digits) == 11 and digits[0] == '1':
        # US number with country code
        return f"+1 ({digits[1:4]}) {digits[4:7]}-{digits[7:]}"
    else:
        # Return original if not a standard format
        return phone


@router.get("/personal")
async def get_personal_info(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get personal information for the authenticated user.

    Requires authentication via Bearer token.
    Returns the user record with settings for the authenticated user.
    """
    user_id = current_user.get("user_id")
    if not user_id:
        logger.error("No user_id in token payload")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing user_id"
        )

    try:
        # Get user info
        user_info = get_user_info(db, user_id)
        if not user_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Get user settings
        user_settings = get_user_settings(db, user_id)
        if not user_settings:
            user_settings = _get_default_settings()

        # Combine user info and settings
        return {
            "user_id": user_info.get("user_id"),
            "first_name": user_info.get("first_name", ""),
            "last_name": user_info.get("last_name", ""),
            "email": user_info.get("email", ""),
            "phone": user_info.get("phone", ""),
            "linkedin_url": user_info.get("linkedin_url", ""),
            "github_url": user_info.get("github_url", ""),
            "website_url": user_info.get("website_url", ""),
            "portfolio_url": user_info.get("portfolio_url", ""),
            "address_1": user_info.get("address_1", ""),
            "address_2": user_info.get("address_2", ""),
            "city": user_info.get("city", ""),
            "state": user_info.get("state", ""),
            "zip": user_info.get("zip", ""),
            "country": user_info.get("country", ""),
            "login": user_info.get("login", ""),
            "passwd": "",  # Don't return password
            "no_response_week": user_settings.get("no_response_week", 6),
            "default_llm": user_settings.get("default_llm", "gpt-4.1-mini"),
            "resume_extract_llm": user_settings.get("resume_extract_llm", "gpt-4.1-mini"),
            "job_extract_llm": user_settings.get("job_extract_llm", "gpt-4.1-mini"),
            "rewrite_llm": user_settings.get("rewrite_llm", "gpt-4.1-mini"),
            "cover_llm": user_settings.get("cover_llm", "gpt-4.1-mini"),
            "company_llm": user_settings.get("company_llm", "gpt-4.1-mini"),
            "tools_llm": user_settings.get("tools_llm", "gpt-4.1-mini"),
            "openai_api_key": user_settings.get("openai_api_key", ""),
            "tinymce_api_key": user_settings.get("tinymce_api_key", ""),
            "convertapi_key": user_settings.get("convertapi_key", ""),
            "docx2html": user_settings.get("docx2html", "docx-parser-converter"),
            "odt2html": user_settings.get("odt2html", "pandoc"),
            "pdf2html": user_settings.get("pdf2html", "markitdown"),
            "html2docx": user_settings.get("html2docx", "html4docx"),
            "html2odt": user_settings.get("html2odt", "pandoc"),
            "html2pdf": user_settings.get("html2pdf", "weasyprint")
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching personal info", user_id=user_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching personal information: {str(e)}"
        )


def _get_default_settings():
    """Return default settings values."""
    return {
        "no_response_week": 6,
        "default_llm": "gpt-4.1-mini",
        "resume_extract_llm": "gpt-4.1-mini",
        "job_extract_llm": "gpt-4.1-mini",
        "rewrite_llm": "gpt-4.1-mini",
        "cover_llm": "gpt-4.1-mini",
        "company_llm": "gpt-4.1-mini",
        "tools_llm": "gpt-4.1-mini",
        "openai_api_key": "",
        "tinymce_api_key": "",
        "convertapi_key": "",
        "docx2html": "docx-parser-converter",
        "odt2html": "pandoc",
        "pdf2html": "markitdown",
        "html2docx": "html4docx",
        "html2odt": "pandoc",
        "html2pdf": "weasyprint"
    }


@router.post("/personal", status_code=status.HTTP_200_OK)
async def save_personal_info(
    personal_data: PersonalCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Save personal information for the authenticated user.

    Requires authentication via Bearer token.
    Updates user information across users, user_detail, address,
    user_address, and user_setting tables.

    The user can only update their own information (user_id from token).
    Validates email format and URL formats for relevant fields.
    Formats phone number to standard format.
    """
    user_id = current_user.get("user_id")
    if not user_id:
        logger.error("No user_id in token payload")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing user_id"
        )

    try:
        # Format phone number if provided
        if personal_data.phone and personal_data.phone.strip():
            personal_data.phone = format_phone_number(personal_data.phone)

        # Always update the authenticated user's data
        return await _update_existing_user(db, user_id, personal_data)

    except ValueError as e:
        # Validation error from Pydantic
        logger.warning(f"Validation error saving personal info", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error saving personal info", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error saving personal information: {str(e)}"
        )


async def _update_existing_user(db: Session, user_id: int, personal_data: PersonalCreate):
    """Update an existing user's information and settings."""

    # Update users table
    update_users_query = text("""
        UPDATE users
        SET first_name = :first_name,
            last_name = :last_name,
            email = :email,
            login = COALESCE(NULLIF(:login, ''), login)
        WHERE user_id = :user_id
    """)

    db.execute(update_users_query, {
        "user_id": user_id,
        "first_name": personal_data.first_name,
        "last_name": personal_data.last_name,
        "email": personal_data.email,
        "login": personal_data.login
    })

    # Update or insert user_detail
    upsert_detail_query = text("""
        INSERT INTO user_detail (user_id, phone, linkedin_url, github_url, website_url, portfolio_url)
        VALUES (:user_id, :phone, :linkedin_url, :github_url, :website_url, :portfolio_url)
        ON CONFLICT (user_id) DO UPDATE SET
            phone = EXCLUDED.phone,
            linkedin_url = EXCLUDED.linkedin_url,
            github_url = EXCLUDED.github_url,
            website_url = EXCLUDED.website_url,
            portfolio_url = EXCLUDED.portfolio_url
    """)

    db.execute(upsert_detail_query, {
        "user_id": user_id,
        "phone": personal_data.phone or "",
        "linkedin_url": personal_data.linkedin_url,
        "github_url": personal_data.github_url,
        "website_url": personal_data.website_url,
        "portfolio_url": personal_data.portfolio_url
    })

    # Handle address if provided
    if personal_data.address_1 or personal_data.city or personal_data.state or personal_data.zip:
        await _upsert_user_address(db, user_id, personal_data)

    # Update or insert user_setting
    upsert_setting_query = text("""
        INSERT INTO user_setting (
            user_id, no_response_week,
            default_llm, resume_extract_llm, job_extract_llm, rewrite_llm, cover_llm, company_llm, tools_llm,
            openai_api_key, tinymce_api_key, convertapi_key,
            docx2html, odt2html, pdf2html, html2docx, html2odt, html2pdf
        )
        VALUES (
            :user_id, :no_response_week,
            :default_llm, :resume_extract_llm, :job_extract_llm, :rewrite_llm, :cover_llm, :company_llm, :tools_llm,
            :openai_api_key, :tinymce_api_key, :convertapi_key,
            :docx2html, :odt2html, :pdf2html, :html2docx, :html2odt, :html2pdf
        )
        ON CONFLICT (user_id) DO UPDATE SET
            no_response_week = EXCLUDED.no_response_week,
            default_llm = EXCLUDED.default_llm,
            resume_extract_llm = EXCLUDED.resume_extract_llm,
            job_extract_llm = EXCLUDED.job_extract_llm,
            rewrite_llm = EXCLUDED.rewrite_llm,
            cover_llm = EXCLUDED.cover_llm,
            company_llm = EXCLUDED.company_llm,
            tools_llm = EXCLUDED.tools_llm,
            openai_api_key = EXCLUDED.openai_api_key,
            tinymce_api_key = EXCLUDED.tinymce_api_key,
            convertapi_key = EXCLUDED.convertapi_key,
            docx2html = EXCLUDED.docx2html,
            odt2html = EXCLUDED.odt2html,
            pdf2html = EXCLUDED.pdf2html,
            html2docx = EXCLUDED.html2docx,
            html2odt = EXCLUDED.html2odt,
            html2pdf = EXCLUDED.html2pdf
    """)

    db.execute(upsert_setting_query, {
        "user_id": user_id,
        "no_response_week": personal_data.no_response_week or 6,
        "default_llm": personal_data.default_llm or "gpt-4.1-mini",
        "resume_extract_llm": personal_data.resume_extract_llm or "gpt-4.1-mini",
        "job_extract_llm": personal_data.job_extract_llm or "gpt-4.1-mini",
        "rewrite_llm": personal_data.rewrite_llm or "gpt-4.1-mini",
        "cover_llm": personal_data.cover_llm or "gpt-4.1-mini",
        "company_llm": personal_data.company_llm or "gpt-4.1-mini",
        "tools_llm": personal_data.tools_llm or "gpt-4.1-mini",
        "openai_api_key": personal_data.openai_api_key,
        "tinymce_api_key": personal_data.tinymce_api_key,
        "convertapi_key": personal_data.convertapi_key,
        "docx2html": personal_data.docx2html or "docx-parser-converter",
        "odt2html": personal_data.odt2html or "pandoc",
        "pdf2html": personal_data.pdf2html or "markitdown",
        "html2docx": personal_data.html2docx or "html4docx",
        "html2odt": personal_data.html2odt or "pandoc",
        "html2pdf": personal_data.html2pdf or "weasyprint"
    })

    db.commit()

    logger.info(f"Updated user information", user_id=user_id)
    return {"status": "success", "user_id": user_id}


async def _upsert_user_address(db: Session, user_id: int, personal_data: PersonalCreate):
    """Create or update user's address."""

    # First, try to get or create the address
    address_query = text("""
        INSERT INTO address (address_1, address_2, city, state, zip, country)
        VALUES (:address_1, :address_2, :city, :state, :zip, :country)
        ON CONFLICT (address_1, address_2, city, state, zip) DO UPDATE SET
            country = EXCLUDED.country
        RETURNING address_id
    """)

    result = db.execute(address_query, {
        "address_1": personal_data.address_1 or "",
        "address_2": personal_data.address_2 or "",
        "city": personal_data.city or "",
        "state": personal_data.state or "",
        "zip": personal_data.zip or "",
        "country": personal_data.country or "US"
    })

    address_id = result.fetchone()[0]

    # Link user to address (set as default, remove old default)
    # First remove existing default
    db.execute(text("""
        UPDATE user_address SET is_default = false WHERE user_id = :user_id
    """), {"user_id": user_id})

    # Then insert or update the new default address
    db.execute(text("""
        INSERT INTO user_address (user_id, address_id, is_default, address_type)
        VALUES (:user_id, :address_id, true, 'home')
        ON CONFLICT (user_id, address_id) DO UPDATE SET
            is_default = true
    """), {"user_id": user_id, "address_id": address_id})
