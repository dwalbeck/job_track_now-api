import re
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text

from ..core.database import get_db
from ..models.models import Personal as PersonalModel
from ..schemas.personal import Personal, PersonalCreate, PersonalUpdate
from ..utils.logger import logger

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
async def get_personal_info(db: Session = Depends(get_db)):
    """
    Get personal information.

    Returns either the existing personal record or an empty object if none exists.
    """
    try:
        # Query to get any existing record (there should only be 0 or 1)
        query = text("""
            SELECT * FROM personal
            WHERE first_name IS NULL OR first_name IS NOT NULL
            LIMIT 1
        """)

        result = db.execute(query).first()

        if result:
            # Convert to dict and return
            return {
                "first_name": result.first_name or "",
                "last_name": result.last_name or "",
                "email": result.email or "",
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
                "country": result.country or "",
                "no_response_week": result.no_response_week,
	            "resume_extract_llm": result.resume_extract_llm or "",
                "job_extract_llm": result.job_extract_llm or "",
                "rewrite_llm": result.rewrite_llm or "",
                "cover_llm": result.cover_llm or "",
                "company_llm": result.company_llm or "",
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
        else:
            # Return empty object
            return {
                "first_name": "",
                "last_name": "",
                "email": "",
                "phone": "",
                "linkedin_url": "",
                "github_url": "",
                "website_url": "",
                "portfolio_url": "",
                "address_1": "",
                "address_2": "",
                "city": "",
                "state": "",
                "zip": "",
                "country": "",
                "no_response_week": 4,
	            "resume_extract_llm": "gpt-4.1-mini",
                "job_extract_llm": "gpt-4.1-mini",
                "rewrite_llm": "gpt-4.1-mini",
                "cover_llm": "gpt-4.1-mini",
                "company_llm": "gpt-4.1-mini",
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

    except Exception as e:
        logger.error(f"Error fetching personal info", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching personal information: {str(e)}"
        )


@router.post("/personal", status_code=status.HTTP_200_OK)
async def save_personal_info(personal_data: PersonalCreate, db: Session = Depends(get_db)):
    """
    Save personal information.

    Creates a new record if none exists, otherwise updates the existing record.
    Validates email format and URL formats for relevant fields.
    Formats phone number to standard format.
    """
    try:
        # Format phone number if provided
        if personal_data.phone and personal_data.phone.strip():
            personal_data.phone = format_phone_number(personal_data.phone)

        # Check if a record already exists
        check_query = text("""
            SELECT first_name, last_name FROM personal
            WHERE first_name IS NULL OR first_name IS NOT NULL
            LIMIT 1
        """)

        existing = db.execute(check_query).first()

        if existing:
            # Update existing record using the composite primary key
            update_query = text("""
                UPDATE personal
                SET email = :email,
                    phone = :phone,
                    linkedin_url = :linkedin_url,
                    github_url = :github_url,
                    website_url = :website_url,
                    portfolio_url = :portfolio_url,
                    address_1 = :address_1,
                    address_2 = :address_2,
                    city = :city,
                    state = :state,
                    zip = :zip,
                    country = :country,
                    no_response_week = :no_response_week,
	                resume_extract_llm = :resume_extract_llm,
                    job_extract_llm = :job_extract_llm,
                    rewrite_llm = :rewrite_llm,
                    cover_llm = :cover_llm,
                    company_llm = :company_llm,
                    openai_api_key = :openai_api_key,
                    tinymce_api_key = :tinymce_api_key,
                    convertapi_key = :convertapi_key,
                    docx2html = :docx2html,
                    odt2html = :odt2html,
                    pdf2html = :pdf2html,
                    html2docx = :html2docx,
                    html2odt = :html2odt,
                    html2pdf = :html2pdf
                WHERE first_name = :old_first_name AND last_name = :old_last_name
            """)

            db.execute(update_query, {
                "old_first_name": existing.first_name,
                "old_last_name": existing.last_name,
                "first_name": personal_data.first_name,
                "last_name": personal_data.last_name,
                "email": personal_data.email,
                "phone": personal_data.phone,
                "linkedin_url": personal_data.linkedin_url,
                "github_url": personal_data.github_url,
                "website_url": personal_data.website_url,
                "portfolio_url": personal_data.portfolio_url,
                "address_1": personal_data.address_1,
                "address_2": personal_data.address_2,
                "city": personal_data.city,
                "state": personal_data.state,
                "zip": personal_data.zip,
                "country": personal_data.country,
                "no_response_week": personal_data.no_response_week,
	            "resume_extract_llm": personal_data.resume_extract_llm,
                "job_extract_llm": personal_data.job_extract_llm,
                "rewrite_llm": personal_data.rewrite_llm,
                "cover_llm": personal_data.cover_llm,
                "company_llm": personal_data.company_llm,
                "openai_api_key": personal_data.openai_api_key,
                "tinymce_api_key": personal_data.tinymce_api_key,
                "convertapi_key": personal_data.convertapi_key,
                "docx2html": personal_data.docx2html,
                "odt2html": personal_data.odt2html,
                "pdf2html": personal_data.pdf2html,
                "html2docx": personal_data.html2docx,
                "html2odt": personal_data.html2odt,
                "html2pdf": personal_data.html2pdf
            })
            db.commit()

            logger.info(f"Updated personal information", first_name=existing.first_name, last_name=existing.last_name)

        else:
            # Insert new record
            insert_query = text("""
                INSERT INTO personal (
                    first_name, last_name, email, phone,
                    linkedin_url, github_url, website_url, portfolio_url,
                    address_1, address_2, city, state, zip, country, no_response_week,
                    resume_extract_llm, job_extract_llm, rewrite_llm, cover_llm, company_llm,
                    openai_api_key, tinymce_api_key, convertapi_key,
                    docx2html, odt2html, pdf2html, html2docx, html2odt, html2pdf
                ) VALUES (
                    :first_name, :last_name, :email, :phone,
                    :linkedin_url, :github_url, :website_url, :portfolio_url,
                    :address_1, :address_2, :city, :state, :zip, :country, :no_response_week,
                    :resume_extract_llm, :job_extract_llm, :rewrite_llm, :cover_llm, :company_llm,
                    :openai_api_key, :tinymce_api_key, :convertapi_key,
                    :docx2html, :odt2html, :pdf2html, :html2docx, :html2odt, :html2pdf
                )
            """)

            db.execute(insert_query, {
                "first_name": personal_data.first_name,
                "last_name": personal_data.last_name,
                "email": personal_data.email,
                "phone": personal_data.phone,
                "linkedin_url": personal_data.linkedin_url,
                "github_url": personal_data.github_url,
                "website_url": personal_data.website_url,
                "portfolio_url": personal_data.portfolio_url,
                "address_1": personal_data.address_1,
                "address_2": personal_data.address_2,
                "city": personal_data.city,
                "state": personal_data.state,
                "zip": personal_data.zip,
                "country": personal_data.country,
                "no_response_week": personal_data.no_response_week,
	            "resume_extract_llm": personal_data.resume_extract_llm,
                "job_extract_llm": personal_data.job_extract_llm,
                "rewrite_llm": personal_data.rewrite_llm,
                "cover_llm": personal_data.cover_llm,
                "company_llm": personal_data.company_llm,
                "openai_api_key": personal_data.openai_api_key,
                "tinymce_api_key": personal_data.tinymce_api_key,
                "convertapi_key": personal_data.convertapi_key,
                "docx2html": personal_data.docx2html,
                "odt2html": personal_data.odt2html,
                "pdf2html": personal_data.pdf2html,
                "html2docx": personal_data.html2docx,
                "html2odt": personal_data.html2odt,
                "html2pdf": personal_data.html2pdf
            })
            db.commit()

            logger.info(f"Created new personal information record")

        return {"status": "success"}

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
