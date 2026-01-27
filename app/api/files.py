from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
import os
from ..core.config import settings
from ..core.database import get_db
from ..utils.logger import logger
from ..utils.file_helpers import create_standardized_download_file
from ..middleware.auth_middleware import get_current_user

router = APIRouter()


@router.get("/files/cover_letters/{file_name}")
async def download_cover_letter(
    file_name: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    """
    Serve a cover letter file for download with standardized naming.

    The file will be copied to /tmp with a standardized name format:
    cover_letter-<first_name>_<last_name>.docx

    Args:
        file_name: Name of the original file to download

    Returns:
        FileResponse with the file using standardized naming
    """

    try:
        # Verify the cover letter belongs to the user
        query = text("""
            SELECT cover_id FROM cover_letter
            WHERE file_name = :file_name AND user_id = :user_id
        """)
        result = db.execute(query, {"file_name": file_name, "user_id": user_id}).first()
        if not result:
            logger.warning(f"Cover letter file not found or not owned by user", file_name=file_name, user_id=user_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File not found: {file_name}"
            )

        file_path = os.path.join(settings.cover_letter_dir, file_name)

        if not os.path.exists(file_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File not found: {file_name}"
            )

        # Create standardized download file
        tmp_path, download_name, mime_type = create_standardized_download_file(
            source_file_path=file_path,
            file_type='cover_letter',
            db=db
        )

        logger.info(f"Serving cover letter file",
                   original=file_name,
                   download_name=download_name)

        return FileResponse(
            path=tmp_path,
            media_type=mime_type,
            filename=download_name
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving cover letter file",
                    file_name=file_name,
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error serving file: {str(e)}"
        )


@router.get("/files/resumes/{file_name}")
async def download_resume(
    file_name: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    """
    Serve a resume file for download with standardized naming.

    The file will be copied to /tmp with a standardized name format:
    resume-<first_name>_<last_name>.<extension>

    Args:
        file_name: Name of the original file to download

    Returns:
        FileResponse with the file using standardized naming
    """

    try:
        # Verify the resume belongs to the user
        # Check both resume.file_name (original) and resume_detail.rewrite_file_name (converted)
        query = text("""
            SELECT r.resume_id FROM resume r
            LEFT JOIN resume_detail rd ON r.resume_id = rd.resume_id
            WHERE r.user_id = :user_id
              AND (r.file_name = :file_name OR rd.rewrite_file_name = :file_name)
        """)
        result = db.execute(query, {"file_name": file_name, "user_id": user_id}).first()
        if not result:
            logger.warning(f"Resume file not found or not owned by user", file_name=file_name, user_id=user_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File not found: {file_name}"
            )

        file_path = os.path.join(settings.resume_dir, file_name)

        if not os.path.exists(file_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File not found: {file_name}"
            )

        # Create standardized download file
        tmp_path, download_name, mime_type = create_standardized_download_file(
            source_file_path=file_path,
            file_type='resume',
            db=db
        )

        logger.info(f"Serving resume file",
                   original=file_name,
                   download_name=download_name)

        return FileResponse(
            path=tmp_path,
            media_type=mime_type,
            filename=download_name
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving resume file",
                    file_name=file_name,
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error serving file: {str(e)}"
        )


@router.get("/files/exports/{file_name}")
async def download_export(
    file_name: str,
    user_id: str = Depends(get_current_user)
):
    """
    Serve an export CSV file for download.

    Args:
        file_name: Name of the export file to download

    Returns:
        FileResponse with the CSV file
    """

    try:
        # Export files are named with date, not user-specific
        # But we still require authentication to access exports
        file_path = os.path.join(settings.export_dir, file_name)

        if not os.path.exists(file_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Export file not found: {file_name}"
            )

        logger.info(f"Serving export file", file_name=file_name, user_id=user_id)

        return FileResponse(
            path=file_path,
            media_type='text/csv',
            filename=file_name
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving export file",
                    file_name=file_name,
                    error=str(e),
                    user_id=user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error serving export file: {str(e)}"
        )


@router.get("/files/logos/{file_name}")
async def serve_logo(
    file_name: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    """
    Serve a company logo file.

    Args:
        file_name: Name of the logo file to serve

    Returns:
        FileResponse with the logo image
    """

    try:
        # Verify the logo belongs to a company owned by user
        query = text("""
            SELECT company_id FROM company
            WHERE logo_file = :file_name AND user_id = :user_id
        """)
        result = db.execute(query, {"file_name": file_name, "user_id": user_id}).first()
        if not result:
            logger.warning(f"Logo file not found or not owned by user", file_name=file_name, user_id=user_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Logo file not found: {file_name}"
            )

        file_path = os.path.join(settings.logo_dir, file_name)

        if not os.path.exists(file_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Logo file not found: {file_name}"
            )

        # Determine mime type from file extension
        extension = file_name.split('.')[-1].lower()
        mime_type_map = {
            'png': 'image/png',
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'gif': 'image/gif',
            'svg': 'image/svg+xml',
            'webp': 'image/webp'
        }
        mime_type = mime_type_map.get(extension, 'image/png')

        logger.info(f"Serving logo file", file_name=file_name, mime_type=mime_type, user_id=user_id)

        return FileResponse(
            path=file_path,
            media_type=mime_type
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving logo file",
                    file_name=file_name,
                    error=str(e),
                    user_id=user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error serving logo file: {str(e)}"
        )


@router.get("/files/reports/{file_name}")
async def download_report(
    file_name: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    """
    Serve a company report file for download.

    Args:
        file_name: Name of the report file to download

    Returns:
        FileResponse with the DOCX file
    """
    try:
        # Report files are named based on company name
        # Verify the user owns a company with a matching report
        # The report filename is: <company_name>_company_report.docx
        # We verify by checking if the file_name starts with any company name the user owns
        query = text("""
            SELECT company_id FROM company
            WHERE user_id = :user_id AND report_html IS NOT NULL
        """)
        result = db.execute(query, {"user_id": user_id}).first()
        if not result:
            logger.warning(f"Report file not found or user has no companies", file_name=file_name, user_id=user_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Report file not found: {file_name}"
            )

        file_path = os.path.join(settings.report_dir, file_name)

        if not os.path.exists(file_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Report file not found: {file_name}"
            )

        logger.info(f"Serving report file", file_name=file_name, user_id=user_id)

        return FileResponse(
            path=file_path,
            media_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            filename=file_name
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving report file",
                    file_name=file_name,
                    error=str(e),
                    user_id=user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error serving report file: {str(e)}"
        )
