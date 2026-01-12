import os
import re
from pathlib import Path
from ..core.config import settings


def create_job_directory(company: str, job_title: str) -> str:
    """
    Create a directory structure for job documents.

    Args:
        company: Company name
        job_title: Job title

    Returns:
        str: The created directory path
    """
    # Clean company name for directory use
    company_clean = re.sub(r'[^\w\s-]', '', company).strip()
    company_clean = re.sub(r'[-\s]+', '_', company_clean)

    # Clean job title and replace spaces with underscores
    job_title_clean = re.sub(r'[^\w\s-]', '', job_title).strip()
    job_title_clean = re.sub(r'[-\s]+', '_', job_title_clean)

    # Create the path
    base_path = Path(settings.base_job_file_path)
    full_path = base_path / company_clean / job_title_clean

    # Create directories if they don't exist
    try:
        full_path.mkdir(parents=True, exist_ok=True)
        return str(full_path)
    except Exception as e:
        # Return the path even if creation fails
        return str(full_path)