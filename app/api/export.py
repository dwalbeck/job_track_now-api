import os
import csv
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text

from ..core.database import get_db
from ..core.config import settings
from ..utils.logger import logger

router = APIRouter()


@router.get("/export/job", status_code=status.HTTP_200_OK)
async def export_jobs(db: Session = Depends(get_db)):
    """
    Export all job data to a CSV file.

    Queries all jobs with their detail information and creates a CSV file
    in the EXPORT_DIR directory with the naming format: job_export-YYYY-MM-DD.csv

    Returns:
        Dictionary containing:
            - job_export_dir: The directory path where the file was saved
            - job_export_file: The filename of the exported CSV
    """
    try:
        # Execute the query to get all job data
        query = text("""
            SELECT j.*, jd.job_desc, jd.job_qualification, jd.job_keyword
            FROM job j
            LEFT JOIN job_detail jd ON (j.job_id = jd.job_id)
            WHERE j.job_id > 0
            ORDER BY j.job_created DESC
        """)

        results = db.execute(query).fetchall()

        if not results:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No job data found to export"
            )

        # Create export directory if it doesn't exist
        export_dir = settings.export_dir
        os.makedirs(export_dir, exist_ok=True)

        # Generate filename with current date
        current_date = datetime.now().strftime("%Y-%m-%d")
        filename = f"job_export-{current_date}.csv"
        file_path = os.path.join(export_dir, filename)

        # Get column names from the first result
        column_names = list(results[0]._mapping.keys())

        # Write CSV file
        with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)

            # Write header row
            writer.writerow(column_names)

            # Write data rows
            for row in results:
                row_data = []
                for col_name in column_names:
                    value = row._mapping[col_name]

                    # Handle PostgreSQL arrays (like job_keyword)
                    if isinstance(value, list):
                        # Convert list to comma-separated string
                        value = ', '.join(str(item) for item in value)

                    # Handle None values
                    if value is None:
                        value = ''

                    row_data.append(value)

                writer.writerow(row_data)

        logger.info(f"Job data exported successfully",
                   file_path=file_path,
                   row_count=len(results))

        return {
            "job_export_dir": export_dir,
            "job_export_file": filename
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting job data", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error exporting job data: {str(e)}"
        )


@router.get("/export/contacts", status_code=status.HTTP_200_OK)
async def export_contacts(db: Session = Depends(get_db)):
    """
    Export all contact data to a CSV file.

    Queries all contacts and creates a CSV file
    in the EXPORT_DIR directory with the naming format: contact_export-YYYY-MM-DD.csv

    Returns:
        Dictionary containing:
            - contact_export_dir: The directory path where the file was saved
            - contact_export_file: The filename of the exported CSV
    """
    try:
        # Execute the query to get all contact data
        query = text("""
            SELECT * FROM contact
            WHERE contact_id > 0
            ORDER BY contact_created DESC
        """)

        results = db.execute(query).fetchall()

        if not results:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No contact data found to export"
            )

        # Create export directory if it doesn't exist
        export_dir = settings.export_dir
        os.makedirs(export_dir, exist_ok=True)

        # Generate filename with current date
        current_date = datetime.now().strftime("%Y-%m-%d")
        filename = f"contact_export-{current_date}.csv"
        file_path = os.path.join(export_dir, filename)

        # Get column names from the first result
        column_names = list(results[0]._mapping.keys())

        # Write CSV file
        with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)

            # Write header row
            writer.writerow(column_names)

            # Write data rows
            for row in results:
                row_data = []
                for col_name in column_names:
                    value = row._mapping[col_name]

                    # Handle PostgreSQL arrays
                    if isinstance(value, list):
                        value = ', '.join(str(item) for item in value)

                    # Handle None values
                    if value is None:
                        value = ''

                    row_data.append(value)

                writer.writerow(row_data)

        logger.info(f"Contact data exported successfully",
                   file_path=file_path,
                   row_count=len(results))

        return {
            "contact_export_dir": export_dir,
            "contact_export_file": filename
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting contact data", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error exporting contact data: {str(e)}"
        )


@router.get("/export/notes", status_code=status.HTTP_200_OK)
async def export_notes(db: Session = Depends(get_db)):
    """
    Export all note data to a CSV file.

    Queries all notes and creates a CSV file
    in the EXPORT_DIR directory with the naming format: notes_export-YYYY-MM-DD.csv

    Returns:
        Dictionary containing:
            - note_export_dir: The directory path where the file was saved
            - note_export_file: The filename of the exported CSV
    """
    try:
        # Execute the query to get all note data
        query = text("""
            SELECT * FROM note
            WHERE note_id > 0
            ORDER BY note_created DESC
        """)

        results = db.execute(query).fetchall()

        if not results:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No note data found to export"
            )

        # Create export directory if it doesn't exist
        export_dir = settings.export_dir
        os.makedirs(export_dir, exist_ok=True)

        # Generate filename with current date
        current_date = datetime.now().strftime("%Y-%m-%d")
        filename = f"notes_export-{current_date}.csv"
        file_path = os.path.join(export_dir, filename)

        # Get column names from the first result
        column_names = list(results[0]._mapping.keys())

        # Write CSV file
        with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)

            # Write header row
            writer.writerow(column_names)

            # Write data rows
            for row in results:
                row_data = []
                for col_name in column_names:
                    value = row._mapping[col_name]

                    # Handle PostgreSQL arrays
                    if isinstance(value, list):
                        value = ', '.join(str(item) for item in value)

                    # Handle None values
                    if value is None:
                        value = ''

                    row_data.append(value)

                writer.writerow(row_data)

        logger.info(f"Note data exported successfully",
                   file_path=file_path,
                   row_count=len(results))

        return {
            "note_export_dir": export_dir,
            "note_export_file": filename
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting note data", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error exporting note data: {str(e)}"
        )


@router.get("/export/calendar", status_code=status.HTTP_200_OK)
async def export_calendar(db: Session = Depends(get_db)):
    """
    Export all calendar data to a CSV file.

    Queries all calendar entries and creates a CSV file
    in the EXPORT_DIR directory with the naming format: calendar_export-YYYY-MM-DD.csv

    Returns:
        Dictionary containing:
            - calendar_export_dir: The directory path where the file was saved
            - calendar_export_file: The filename of the exported CSV
    """
    try:
        # Execute the query to get all calendar data
        query = text("""
            SELECT * FROM calendar
            WHERE note_id > 0
            ORDER BY start_date DESC
        """)

        results = db.execute(query).fetchall()

        if not results:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No calendar data found to export"
            )

        # Create export directory if it doesn't exist
        export_dir = settings.export_dir
        os.makedirs(export_dir, exist_ok=True)

        # Generate filename with current date
        current_date = datetime.now().strftime("%Y-%m-%d")
        filename = f"calendar_export-{current_date}.csv"
        file_path = os.path.join(export_dir, filename)

        # Get column names from the first result
        column_names = list(results[0]._mapping.keys())

        # Write CSV file
        with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)

            # Write header row
            writer.writerow(column_names)

            # Write data rows
            for row in results:
                row_data = []
                for col_name in column_names:
                    value = row._mapping[col_name]

                    # Handle PostgreSQL arrays
                    if isinstance(value, list):
                        value = ', '.join(str(item) for item in value)

                    # Handle None values
                    if value is None:
                        value = ''

                    row_data.append(value)

                writer.writerow(row_data)

        logger.info(f"Calendar data exported successfully",
                   file_path=file_path,
                   row_count=len(results))

        return {
            "calendar_export_dir": export_dir,
            "calendar_export_file": filename
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting calendar data", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error exporting calendar data: {str(e)}"
        )


@router.get("/export/resumes", status_code=status.HTTP_200_OK)
async def export_resumes(db: Session = Depends(get_db)):
    """
    Export all resume data to a CSV file.

    Queries all resumes with their detail information and creates a CSV file
    in the EXPORT_DIR directory with the naming format: resumes_export-YYYY-MM-DD.csv

    Returns:
        Dictionary containing:
            - resume_export_dir: The directory path where the file was saved
            - resume_export_file: The filename of the exported CSV
    """
    try:
        # Execute the query to get all resume data
        query = text("""
            SELECT * FROM resume r
            LEFT JOIN resume_detail rd ON (r.resume_id = rd.resume_id)
            WHERE r.resume_id > 0
            ORDER BY r.is_baseline, r.resume_created DESC
        """)

        results = db.execute(query).fetchall()

        if not results:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No resume data found to export"
            )

        # Create export directory if it doesn't exist
        export_dir = settings.export_dir
        os.makedirs(export_dir, exist_ok=True)

        # Generate filename with current date
        current_date = datetime.now().strftime("%Y-%m-%d")
        filename = f"resumes_export-{current_date}.csv"
        file_path = os.path.join(export_dir, filename)

        # Get column names from the first result
        column_names = list(results[0]._mapping.keys())

        # Write CSV file
        with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)

            # Write header row
            writer.writerow(column_names)

            # Write data rows
            for row in results:
                row_data = []
                for col_name in column_names:
                    value = row._mapping[col_name]

                    # Handle PostgreSQL arrays
                    if isinstance(value, list):
                        value = ', '.join(str(item) for item in value)

                    # Handle None values
                    if value is None:
                        value = ''

                    row_data.append(value)

                writer.writerow(row_data)

        logger.info(f"Resume data exported successfully",
                   file_path=file_path,
                   row_count=len(results))

        return {
            "resume_export_dir": export_dir,
            "resume_export_file": filename
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting resume data", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error exporting resume data: {str(e)}"
        )
