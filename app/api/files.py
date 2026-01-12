from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import os
from ..core.config import settings
from ..core.database import get_db
from ..utils.logger import logger
from ..utils.file_helpers import create_standardized_download_file

router = APIRouter()


@router.get("/files/cover_letters/{file_name}")
async def download_cover_letter(file_name: str, db: Session = Depends(get_db)):
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
async def download_resume(file_name: str, db: Session = Depends(get_db)):
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
async def download_export(file_name: str):
    """
    Serve an export CSV file for download.

    Args:
        file_name: Name of the export file to download

    Returns:
        FileResponse with the CSV file
    """
    try:
        file_path = os.path.join(settings.export_dir, file_name)

        if not os.path.exists(file_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Export file not found: {file_name}"
            )

        logger.info(f"Serving export file", file_name=file_name)

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
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error serving export file: {str(e)}"
        )


@router.get("/files/logos/{file_name}")
async def serve_logo(file_name: str):
    """
    Serve a company logo file.

    Args:
        file_name: Name of the logo file to serve

    Returns:
        FileResponse with the logo image
    """
    try:
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

        logger.info(f"Serving logo file", file_name=file_name, mime_type=mime_type)

        return FileResponse(
            path=file_path,
            media_type=mime_type
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving logo file",
                    file_name=file_name,
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error serving logo file: {str(e)}"
        )


@router.get("/files/reports/{file_name}")
async def download_report(file_name: str):
    """
    Serve a company report file for download.

    Args:
        file_name: Name of the report file to download

    Returns:
        FileResponse with the DOCX file
    """
    try:
        file_path = os.path.join(settings.report_dir, file_name)

        if not os.path.exists(file_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Report file not found: {file_name}"
            )

        logger.info(f"Serving report file", file_name=file_name)

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
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error serving report file: {str(e)}"
        )
