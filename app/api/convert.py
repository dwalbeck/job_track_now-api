from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import text
from enum import Enum
import os

from ..core.database import get_db
from ..core.config import settings
from ..utils.conversion import Conversion
from ..utils.logger import logger
from ..middleware.auth_middleware import get_current_user

router = APIRouter()


class OutputFormat(str, Enum):
    """Valid output formats for conversion"""
    odt = "odt"
    docx = "docx"
    pdf = "pdf"
    html = "html"


class ConvertRequest(BaseModel):
    file_name: str


class ConvertResponse(BaseModel):
    file_content: str


@router.post("/convert/odt2md", response_model=ConvertResponse)
async def convert_odt_to_md(request: ConvertRequest):
    """
    Convert ODT file to Markdown.

    Args:
        request: Contains file_name to convert

    Returns:
        ConvertResponse with markdown content
    """
    try:
        markdown_content = Conversion.odtToMd(request.file_name)
        return ConvertResponse(file_content=markdown_content)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/convert/odt2html", response_model=ConvertResponse)
async def convert_odt_to_html(request: ConvertRequest):
    """
    Convert ODT file to HTML.

    Args:
        request: Contains file_name to convert

    Returns:
        ConvertResponse with HTML content
    """
    try:
        html_content = Conversion.odtToHtml(request.file_name)
        return ConvertResponse(file_content=html_content)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/convert/docx2md", response_model=ConvertResponse)
async def convert_docx_to_md(request: ConvertRequest):
    """
    Convert DOCX file to Markdown.

    Args:
        request: Contains file_name to convert

    Returns:
        ConvertResponse with markdown content
    """
    try:
        markdown_content = Conversion.docxToMd(request.file_name)
        return ConvertResponse(file_content=markdown_content)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/convert/docx2html", response_model=ConvertResponse)
async def convert_docx_to_html(request: ConvertRequest):
    """
    Convert DOCX file to HTML.

    Args:
        request: Contains file_name to convert

    Returns:
        ConvertResponse with HTML content
    """
    try:
        html_content = Conversion.docxToHtml(request.file_name)
        return ConvertResponse(file_content=html_content)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/convert/pdf2md", response_model=ConvertResponse)
async def convert_pdf_to_md(request: ConvertRequest):
    """
    Convert PDF file to Markdown.

    Args:
        request: Contains file_name to convert

    Returns:
        ConvertResponse with markdown content
    """
    try:
        markdown_content = Conversion.pdfToMd(request.file_name)
        return ConvertResponse(file_content=markdown_content)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/convert/pdf2html", response_model=ConvertResponse)
async def convert_pdf_to_html(request: ConvertRequest):
    """
    Convert PDF file to HTML.

    Args:
        request: Contains file_name to convert

    Returns:
        ConvertResponse with HTML content
    """
    try:
        html_content = Conversion.pdfToHtml(request.file_name)
        return ConvertResponse(file_content=html_content)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class Html2DocxResponse(BaseModel):
    file_name: str


@router.get("/convert/html2docx", response_model=Html2DocxResponse)
async def convert_html_to_docx(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Performs the conversion from HTML to DOCX and returns the new filename.

    Requires authentication via Bearer token.

    Query parameters:
    - job_id: ID of the job

    Returns:
    - file_name: Name of the generated DOCX file
    """
    user_id = current_user.get("user_id")

    logger.info(f"HTML to DOCX /convert/html2docx conversion requested", job_id=job_id, user_id=user_id)

    # Retrieve first and last name from users table for the authenticated user
    query = text("""SELECT u.first_name, u.last_name, j.resume_id
                    FROM users u LEFT JOIN job j ON (j.job_id = :job_id AND j.user_id = :user_id)
                    WHERE u.user_id = :user_id""")
    result = db.execute(query, {"job_id": job_id, "user_id": user_id}).first()

    if not result:
        logger.error("Failed to retrieve user info", user_id=user_id)
        raise HTTPException(status_code=404, detail="User not found")

    full_name = result.first_name + " " + result.last_name

    try:
        # Otherwise, perform the conversion from HTML to DOCX
        logger.debug(f"Performing HTML to DOCX conversion", job_id=job_id)
        conversion_result = Conversion.html2docx_from_job(job_id, db)
        logger.debug(f"html2docx_from_job returned {conversion_result}\n")

        if Conversion.pageFormatting(conversion_result['file_name'], full_name):
            logger.info(f"Custom page formatting succeeded")
        else:
            logger.info(f"Custom page formatting failed")

        logger.info(f"HTML to DOCX conversion completed", job_id=job_id, file_name=conversion_result['file_name'])
        return Html2DocxResponse(file_name=conversion_result['file_name'])

    except ValueError as e:
        logger.error(f"Validation error during conversion", job_id=job_id, error=str(e))
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error during HTML to DOCX conversion", job_id=job_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Error converting HTML to DOCX: {str(e)}"
        )


@router.get("/file/download/resume/{file_name}")
async def download_resume_file(
    file_name: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Download a resume file from the resume directory.

    Requires authentication via Bearer token.

    The file is stored with company-jobtitle naming but downloaded as
    resume-firstname_lastname.extension for consistency.

    Args:
        file_name: Name of the file to download
        current_user: Current user dict from JWT
        db: Database session

    Returns:
        FileResponse with the requested file
    """
    user_id = current_user.get("user_id")

    logger.info(f"Resume file download requested", file_name=file_name, user_id=user_id)

    # Retrieve first and last name from users table for the authenticated user
    query = text("SELECT first_name, last_name FROM users WHERE user_id = :user_id")
    user_result = db.execute(query, {"user_id": user_id}).first()

    if not user_result:
        logger.error("Failed to retrieve user info", user_id=user_id)
        raise HTTPException(status_code=404, detail="User not found")

    full_name = user_result.first_name + " " + user_result.last_name

    try:
        # Construct the full file path
        resume_dir = os.path.join('/app', settings.base_job_file_path, 'resumes')
        file_path = os.path.join(resume_dir, file_name)

        # Check if file exists
        if not os.path.exists(file_path):
            logger.warning(f"Resume file not found", file_name=file_name, file_path=file_path)
            raise HTTPException(status_code=404, detail=f"File not found: {file_name}")

        # Check if it's actually a file (not a directory)
        if not os.path.isfile(file_path):
            logger.warning(f"Path is not a file", file_name=file_name, file_path=file_path)
            raise HTTPException(status_code=400, detail=f"Invalid file path: {file_name}")

        # Extract file extension
        file_extension = file_name.rsplit('.', 1)[-1] if '.' in file_name else 'docx'

        # Create download filename as resume-firstname_lastname.extension using authenticated user's name
        if user_result.first_name and user_result.last_name:
            download_filename = f"resume-{user_result.first_name}_{user_result.last_name}.{file_extension}"
        else:
            # Fallback to original filename if user info not complete
            download_filename = file_name

        logger.info(f"Serving resume file", file_name=file_name, download_filename=download_filename)

        # Determine media type based on extension
        media_types = {
            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'odt': 'application/vnd.oasis.opendocument.text',
            'pdf': 'application/pdf',
            'html': 'text/html'
        }
        media_type = media_types.get(file_extension.lower(), 'application/octet-stream')

        if Conversion.pageFormatting(file_name, full_name):
            logger.info(f"Custom page formatting succeeded")
        else:
            logger.info(f"Custom page formatting failed")

        # Return the file with renamed download filename
        return FileResponse(
            path=file_path,
            filename=download_filename,
            media_type=media_type
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading resume file", file_name=file_name, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Error downloading file: {str(e)}"
        )


class ConvertFinalRequest(BaseModel):
    """Request schema for /v1/convert/final endpoint"""
    resume_id: int
    output_format: OutputFormat


class ConvertFinalResponse(BaseModel):
    """Response schema for /v1/convert/final endpoint"""
    file_name: str


@router.post("/convert/final", response_model=ConvertFinalResponse)
async def convert_final(
    request: ConvertFinalRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Convert the final resume (resume_md_rewrite) to the specified output format.

    This endpoint:
    1. Retrieves the resume_md_rewrite content from resume_detail table
    2. Queries the baseline resume to get original format (for reference styling)
    3. Converts to the requested format (odt, docx, pdf, or html)
    4. Uses the original file as a reference if formats match
    5. Saves the file with the same base name as the original but with new extension
    6. Returns the new filename

    Args:
        request: ConvertFinalRequest with resume_id and output_format
        current_user: Current user dict from JWT
        db: Database session

    Returns:
        ConvertFinalResponse with the generated file_name

    Raises:
        HTTPException: If resume not found or conversion fails
    """
    user_id = current_user.get("user_id")
    try:
        logger.info(f"Converting final resume", resume_id=request.resume_id, output_format=request.output_format, user_id=user_id)

        # Query to get resume data
        query = text("""
	         SELECT r.file_name, rd.resume_html_rewrite, rr.file_name AS orig_file_name, rr.original_format
	         FROM resume r
	                  JOIN resume_detail rd ON (r.resume_id = rd.resume_id)
	                  JOIN resume rr ON (r.baseline_resume_id = rr.resume_id)
	         WHERE r.resume_id = :resume_id AND r.user_id = :user_id
	         """)

        result = db.execute(query, {"resume_id": request.resume_id, "user_id": user_id}).first()

        if not result:
            logger.error(f"Resume not found", resume_id=request.resume_id)
            raise HTTPException(status_code=404, detail=f"Resume not found for resume_id: {request.resume_id}")

        if not result.resume_html_rewrite:
            logger.error(f"No rewritten HTML content found", resume_id=request.resume_id)
            raise HTTPException(status_code=400, detail=f"No rewritten HTML content found for resume_id: {request.resume_id}")

        # Extract values
        original_file_name = result.file_name
        html_content = result.resume_html_rewrite

        # Determine if we should use a reference file
        reference_file = None
        if result.original_format:
            # Check if baseline format matches requested format
            baseline_format = result.original_format.lower()
            requested_format = request.output_format.value.lower()

            if baseline_format == requested_format:
                reference_file = result.orig_file_name
                logger.debug(f"Using reference file for styling", reference_file=reference_file)

        # Generate new filename with requested extension
        new_file_name = Conversion.rename_file(original_file_name, request.output_format.value)

        logger.debug(f"Converting resume", original_file_name=original_file_name, new_file_name=new_file_name,
                     reference_file=reference_file)

        # Convert based on output format
        if request.output_format.value == "html":
            # For HTML, save the HTML content directly
            output_path = Conversion._get_file_path(new_file_name)
            # Ensure directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            logger.debug(f"HTML file created", file_path=str(output_path))

        elif request.output_format.value == "docx":
            # For DOCX, use html2docx
            output_path, cleaned_html = Conversion.html2docx(html_content, new_file_name)
            logger.debug(f"DOCX file created", file_path=output_path)

            # Update database with cleaned HTML
            update_query = text("""
                UPDATE resume_detail
                SET resume_html_rewrite = :cleaned_html
                WHERE resume_id = :resume_id
            """)
            db.execute(update_query, {"cleaned_html": cleaned_html, "resume_id": request.resume_id})
            db.commit()
            logger.debug(f"Updated resume_html_rewrite with cleaned HTML")

        elif request.output_format.value == "odt":
            # For ODT, use html2odt
            output_path = Conversion.html2odt(html_content, new_file_name)
            logger.debug(f"ODT file created", file_path=output_path)

        elif request.output_format.value == "pdf":
            # For PDF, use html2pdf
            output_path = Conversion.html2pdf(html_content, new_file_name)
            logger.debug(f"PDF file created", file_path=output_path)

        logger.info(f"Resume conversion completed successfully", resume_id=request.resume_id, output_file=new_file_name)

        return ConvertFinalResponse(file_name=new_file_name)

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error converting resume", resume_id=request.resume_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Error converting resume: {str(e)}")


class ConvertFileRequest(BaseModel):
    """Request schema for /v1/convert/file endpoint"""
    resume_id: int
    source_format: str
    target_format: str


class ConvertFileResponse(BaseModel):
    """Response schema for /v1/convert/file endpoint"""
    file: str
    file_content: str


@router.post("/convert/file", response_model=ConvertFileResponse)
async def convert_file(
    request: ConvertFileRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Convert resume file using user configuration settings.

    This endpoint:
    1. Retrieves resume and resume_detail data from database
    2. Determines input and output paths based on source/target formats
    3. Calls Conversion.convert_file() with user settings
    4. Returns the filename and content (for md/html targets)

    For baseline resumes (source: docx, odt, pdf):
    - input_path: resume directory + resume.file_name
    - output_path: change extension to target_format
    - Returns: filename and file_content

    For optimized resumes (source: md, html):
    - input_path: resume.file_name (html) or swap extension to md
    - output_path: append '-final' to avoid collision with baseline
    - Returns: filename and file_content

    Args:
        request: ConvertFileRequest with resume_id, source_format, target_format
        current_user: Current user dict from JWT
        db: Database session

    Returns:
        ConvertFileResponse with file name and content

    Raises:
        HTTPException: If resume not found or conversion fails
    """
    user_id = current_user.get("user_id")
    try:
        logger.info(f"File conversion requested", resume_id=request.resume_id,
                   source_format=request.source_format, target_format=request.target_format, user_id=user_id)

        # Normalize formats
        source_format = request.source_format.lower().strip()
        target_format = request.target_format.lower().strip()

        # Query to get resume data
        query = text("""
            SELECT r.file_name, r.original_format, r.is_baseline
            FROM resume r
            WHERE r.resume_id = :resume_id AND r.user_id = :user_id
        """)

        result = db.execute(query, {"resume_id": request.resume_id, "user_id": user_id}).first()

        if not result:
            logger.error(f"Resume not found", resume_id=request.resume_id)
            raise HTTPException(status_code=404, detail=f"Resume not found for resume_id: {request.resume_id}")

        file_name = result.file_name

        # Check if file_name is None
        if not file_name:
            logger.error(f"Resume file_name is NULL", resume_id=request.resume_id)
            raise HTTPException(status_code=400, detail=f"Resume file_name is missing for resume_id: {request.resume_id}")

        # Determine paths based on source format
        resume_dir = settings.resume_dir

        # Check if resume_dir is None
        if not resume_dir:
            logger.error(f"RESUME_DIR configuration is missing")
            raise HTTPException(status_code=500, detail="Server configuration error: RESUME_DIR not configured")

        if source_format in ['docx', 'odt', 'pdf']:
            # Baseline resume
            input_path = os.path.join(resume_dir, file_name)
            # Change extension to target format
            output_file_name = Conversion.rename_file(file_name, target_format)
            output_path = os.path.join(resume_dir, output_file_name)

        elif source_format in ['md', 'html']:
            # Optimized resume
            if source_format == 'html':
                # Use file_name as-is
                input_file_name = file_name
            else:  # md
                # Swap extension from html to md
                input_file_name = Conversion.rename_file(file_name, 'md')

            input_path = os.path.join(resume_dir, input_file_name)

            # For HTML source, check if file exists on disk
            # If not, retrieve from database and write to disk
            if source_format == 'html' and not os.path.exists(input_path):
                logger.debug(f"HTML file not found on disk, retrieving from database", resume_id=request.resume_id, file_name=input_file_name)

                # Query to get HTML content from resume_detail
                html_query = text("""
                    SELECT resume_html_rewrite
                    FROM resume_detail
                    WHERE resume_id = :resume_id
                """)
                html_result = db.execute(html_query, {"resume_id": request.resume_id}).first()

                if not html_result or not html_result.resume_html_rewrite:
                    logger.error(f"No HTML content found in database", resume_id=request.resume_id)
                    raise HTTPException(status_code=404, detail=f"No HTML content found for resume_id: {request.resume_id}")

                # Create directory if it doesn't exist
                os.makedirs(os.path.dirname(input_path), exist_ok=True)

                # Write HTML content to disk
                with open(input_path, 'w', encoding='utf-8') as f:
                    f.write(html_result.resume_html_rewrite)

                logger.debug(f"HTML content written to disk", file_path=input_path)

            # Append '-final' to output filename to avoid collision
            base_name = file_name.rsplit('.', 1)[0] if '.' in file_name else file_name
            output_file_name = f"{base_name}-final.{target_format}"
            output_path = os.path.join(resume_dir, output_file_name)
        else:
            logger.error(f"Unsupported source format", source_format=source_format)
            raise HTTPException(status_code=400, detail=f"Unsupported source format: {source_format}")

        logger.debug(f"Conversion paths determined - starting conversion", input_path=input_path, output_path=output_path)

        # Call the conversion method
        conversion_success = Conversion.convert_file(
            source_format=source_format,
            target_format=target_format,
            input_path=input_path,
            output_path=output_path,
	        user_id=user_id
        )

        if not conversion_success:
            logger.error(f"Conversion failed", resume_id=request.resume_id)
            raise HTTPException(status_code=500, detail="File conversion failed")

        # Read file content for md and html targets
        file_content = ""
        if target_format in ['md', 'html']:
            try:
                with open(output_path, 'r', encoding='utf-8') as f:
                    file_content = f.read()
                logger.debug(f"File content read successfully", file_size=len(file_content))
            except Exception as e:
                logger.error(f"Error reading converted file", error=str(e))
                raise HTTPException(status_code=500, detail=f"Error reading converted file: {str(e)}")

        logger.info(f"File conversion completed successfully", resume_id=request.resume_id,
                   output_file=output_file_name)

        return ConvertFileResponse(file=output_file_name, file_content=file_content)

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error during file conversion", resume_id=request.resume_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Error during file conversion: {str(e)}")
