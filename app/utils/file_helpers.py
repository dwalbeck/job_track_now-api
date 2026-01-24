import os
import shutil
import mimetypes
from sqlalchemy.orm import Session
from sqlalchemy import text
from .logger import logger
from .user_helper import get_user_name


def get_personal_name(db: Session, user_id: int) -> tuple[str, str]:
    """
    Get the user's first and last name.

    Args:
        db: Database session
        user_id: The user's ID (required)

    Returns:
        Tuple of (first_name, last_name). Returns empty strings if not found.

    Raises:
        ValueError: If user_id is not provided
    """
    if not user_id:
        raise ValueError("user_id is required")

    try:
        return get_user_name(db, user_id)
    except Exception as e:
        logger.error(f"Error fetching user name", user_id=user_id, error=str(e))
        return ("", "")


def get_file_extension(file_path: str) -> str:
    """
    Get the file extension from a file path.

    Args:
        file_path: Path to the file

    Returns:
        File extension including the dot (e.g., '.pdf', '.docx')
    """
    return os.path.splitext(file_path)[1]


def get_mime_type(file_path: str) -> str:
    """
    Get the MIME type for a file based on its extension.

    Args:
        file_path: Path to the file

    Returns:
        MIME type string (e.g., 'application/pdf')
    """
    mime_type, _ = mimetypes.guess_type(file_path)
    return mime_type or 'application/octet-stream'


def create_standardized_download_file(
    source_file_path: str,
    file_type: str,
    db: Session,
    user_id: int
) -> tuple[str, str, str]:
    """
    Copy a file to /tmp with standardized naming for download.

    Args:
        source_file_path: Original file path
        file_type: Either 'resume' or 'cover_letter'
        db: Database session
        user_id: The user's ID (required)

    Returns:
        Tuple of (tmp_file_path, download_filename, mime_type)

    Raises:
        ValueError: If user_id is not provided
    """
    if not user_id:
        raise ValueError("user_id is required")

    # Get user's name
    first_name, last_name = get_personal_name(db, user_id)

    # Create name parts
    name_part = f"{first_name}_{last_name}".lower().replace(" ", "_")

    # Get file extension
    extension = get_file_extension(source_file_path)

    # For cover letters, always use .docx
    if file_type == 'cover_letter':
        extension = '.docx'

    # Create download filename
    if file_type == 'resume':
        download_filename = f"resume-{name_part}{extension}"
    elif file_type == 'cover_letter':
        download_filename = f"cover_letter-{name_part}{extension}"
    else:
        download_filename = f"{file_type}-{name_part}{extension}"

    # Create temp file path
    tmp_file_path = os.path.join('/tmp', download_filename)

    # Copy file to tmp
    try:
        shutil.copy2(source_file_path, tmp_file_path)
        logger.info(f"Created standardized download file",
                   source=source_file_path,
                   temp=tmp_file_path,
                   download_name=download_filename)
    except Exception as e:
        logger.error(f"Error copying file to tmp",
                    source=source_file_path,
                    error=str(e))
        raise

    # Get MIME type
    mime_type = get_mime_type(source_file_path)

    return (tmp_file_path, download_filename, mime_type)
