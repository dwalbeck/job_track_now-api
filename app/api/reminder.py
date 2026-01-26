from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List
from datetime import timedelta

from ..core.database import get_db
from ..schemas.reminder import ReminderCreate, ReminderListRequest, ReminderListResponse
from ..utils.logger import logger
from ..middleware.auth_middleware import get_current_user

router = APIRouter()


@router.post("/reminder")
async def create_or_update_reminder(
    reminder: ReminderCreate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    """
    Create or update a reminder.

    If reminder_id is provided, updates existing reminder.
    Otherwise, creates a new reminder.

    Args:
        reminder: Reminder data
        db: Database session

    Returns:
        Success status with HTTP 200
    """

    try:
        if reminder.reminder_id:
            # Update existing reminder - ensure user owns it
            logger.info(f"Updating reminder", reminder_id=reminder.reminder_id, user_id=user_id)

            update_query = text("""
                UPDATE reminder
                SET reminder_date = :reminder_date,
                    reminder_time = :reminder_time,
                    reminder_message = :reminder_message,
                    reminder_dismissed = :reminder_dismissed,
                    job_id = :job_id,
                    reminder_updated = CURRENT_TIMESTAMP
                WHERE reminder_id = :reminder_id AND user_id = :user_id
            """)

            result = db.execute(update_query, {
                "reminder_date": reminder.reminder_date,
                "reminder_time": reminder.reminder_time,
                "reminder_message": reminder.reminder_message,
                "reminder_dismissed": reminder.reminder_dismissed,
                "job_id": reminder.job_id,
                "reminder_id": reminder.reminder_id,
                "user_id": user_id
            })
            db.commit()

            if result.rowcount == 0:
                raise HTTPException(status_code=404, detail="Reminder not found")

            logger.log_database_operation("UPDATE", "reminder", reminder.reminder_id)
            logger.info(f"Reminder updated successfully", reminder_id=reminder.reminder_id, user_id=user_id)

        else:
            # Create new reminder
            logger.info(f"Creating new reminder", user_id=user_id)

            insert_query = text("""
                INSERT INTO reminder (
                    user_id,
                    reminder_date,
                    reminder_time,
                    reminder_message,
                    reminder_dismissed,
                    job_id
                )
                VALUES (
                    :user_id,
                    :reminder_date,
                    :reminder_time,
                    :reminder_message,
                    :reminder_dismissed,
                    :job_id
                )
                RETURNING reminder_id
            """)

            result = db.execute(insert_query, {
                "user_id": user_id,
                "reminder_date": reminder.reminder_date,
                "reminder_time": reminder.reminder_time,
                "reminder_message": reminder.reminder_message,
                "reminder_dismissed": reminder.reminder_dismissed,
                "job_id": reminder.job_id
            })

            new_reminder_id = result.scalar()
            db.commit()

            logger.log_database_operation("INSERT", "reminder", new_reminder_id)
            logger.info(f"Reminder created successfully", reminder_id=new_reminder_id, user_id=user_id)

        return {"status": "success"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating/updating reminder", error=str(e), user_id=user_id)
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error saving reminder: {str(e)}")


@router.delete("/reminder")
async def delete_reminder(
    reminder_id: int,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    """
    Delete a reminder by ID.

    Args:
        reminder_id: ID of the reminder to delete
        db: Database session

    Returns:
        Success status with HTTP 200
    """

    try:
        logger.info(f"Deleting reminder", reminder_id=reminder_id, user_id=user_id)

        delete_query = text("""
            DELETE FROM reminder
            WHERE reminder_id = :reminder_id AND user_id = :user_id
        """)

        result = db.execute(delete_query, {"reminder_id": reminder_id, "user_id": user_id})
        db.commit()

        if result.rowcount == 0:
            logger.warning(f"Reminder not found for deletion", reminder_id=reminder_id, user_id=user_id)
            raise HTTPException(status_code=404, detail="Reminder not found")

        logger.log_database_operation("DELETE", "reminder", reminder_id)
        logger.info(f"Reminder deleted successfully", reminder_id=reminder_id, user_id=user_id)

        return {"status": "success"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting reminder", reminder_id=reminder_id, error=str(e), user_id=user_id)
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting reminder: {str(e)}")


@router.post("/reminder/list", response_model=List[ReminderListResponse])
async def list_reminders(
    request: ReminderListRequest,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    """
    Get a list of reminders based on duration and optional job_id filter.

    Duration types:
    - day: Returns reminders for the start_date only
    - week: Returns reminders for 7 days starting from start_date
    - month: Returns reminders for 30 days starting from start_date

    Args:
        request: List request with duration, start_date, and optional job_id
        db: Database session

    Returns:
        List of reminders matching the criteria
    """

    try:
        logger.info(f"Listing reminders", duration=request.duration, start_date=request.start_date, job_id=request.job_id, user_id=user_id)

        # Calculate end date based on duration
        if request.duration == "day":
            end_date = request.start_date
        elif request.duration == "week":
            end_date = request.start_date + timedelta(days=6)
        else:  # month
            end_date = request.start_date + timedelta(days=29)

        # Build query based on whether job_id is provided
        if request.job_id is not None:
            query = text("""
                SELECT reminder_id, reminder_date, reminder_time, reminder_message, job_id
                FROM reminder
                WHERE reminder_date BETWEEN :start_date AND :end_date
                  AND job_id = :job_id
                  AND user_id = :user_id
                  AND (reminder_dismissed IS NULL OR reminder_dismissed = FALSE)
                ORDER BY reminder_date DESC, reminder_time DESC
            """)

            result = db.execute(query, {
                "start_date": request.start_date,
                "end_date": end_date,
                "job_id": request.job_id,
                "user_id": user_id
            })
        else:
            query = text("""
                SELECT reminder_id, reminder_date, reminder_time, reminder_message, job_id
                FROM reminder
                WHERE reminder_date BETWEEN :start_date AND :end_date
                  AND user_id = :user_id
                  AND (reminder_dismissed IS NULL OR reminder_dismissed = FALSE)
                ORDER BY reminder_date DESC, reminder_time DESC
            """)

            result = db.execute(query, {
                "start_date": request.start_date,
                "end_date": end_date,
                "user_id": user_id
            })

        reminders = []
        for row in result:
            reminders.append({
                "reminder_id": row.reminder_id,
                "reminder_date": row.reminder_date,
                "reminder_time": row.reminder_time,
                "reminder_message": row.reminder_message,
                "job_id": row.job_id
            })

        logger.log_database_operation("SELECT", "reminder")
        logger.info(f"Retrieved reminders", count=len(reminders), duration=request.duration, user_id=user_id)

        return reminders

    except Exception as e:
        logger.error(f"Error listing reminders", error=str(e), user_id=user_id)
        raise HTTPException(status_code=500, detail=f"Error listing reminders: {str(e)}")
