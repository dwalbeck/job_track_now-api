"""
Helper functions for job-related operations.
"""
from sqlalchemy.orm import Session
from sqlalchemy import text
from .logger import logger


def update_job_activity(db: Session, job_id: int) -> None:
    """
    Update the last_activity field for a job to the current date.

    This function should be called whenever there is activity related to a job,
    such as creating/updating resumes, cover letters, notes, calendar events, or contacts.

    Args:
        db: Database session
        job_id: The ID of the job to update

    Returns:
        None

    Raises:
        Exception: If the database update fails
    """
    try:
        query = text("""
            UPDATE job
            SET last_activity = CURRENT_DATE
            WHERE job_id = :job_id
        """)

        db.execute(query, {"job_id": job_id})
        db.commit()

        logger.debug(f"Updated last_activity for job", job_id=job_id)

    except Exception as e:
        db.rollback()
        logger.error(f"Error updating job activity", job_id=job_id, error=str(e))
        raise


def calc_avg_score(db: Session, job_id: int) -> None:
    """
    Calculate and update the average score for a job.

    This function calculates the average of all outcome scores from calendar events
    and the interest level from the job record, then updates the job's average_score field.

    Args:
        db: Database session
        job_id: The ID of the job to calculate average score for

    Returns:
        None

    Raises:
        Exception: If the database update fails
    """
    try:
        query = text("""
            UPDATE job SET average_score=(
                SELECT round(avg(merged_tbl.outcome_score), 3) FROM
                    (SELECT outcome_score FROM calendar WHERE job_id=:job_id
                        UNION
                     SELECT interest_level AS outcome_score FROM job WHERE job_id=:job_id2) AS merged_tbl)
            WHERE job_id=:job_id3
        """)

        db.execute(query, {"job_id": job_id, "job_id2": job_id, "job_id3": job_id})
        db.commit()

        logger.debug(f"Updated average_score for job", job_id=job_id)

    except Exception as e:
        db.rollback()
        logger.error(f"Error calculating average score", job_id=job_id, error=str(e))
        raise
