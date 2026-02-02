from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text

from ..core.database import get_db
from ..models.models import Calendar, Job
from ..schemas.calendar import Calendar as CalendarSchema, CalendarUpdate
from ..utils.date_helpers import get_month_date_range, get_week_date_range, validate_week_start
from ..utils.job_helpers import update_job_activity, calc_avg_score
from ..utils.logger import logger
from ..middleware.auth_middleware import get_current_user

router = APIRouter()


@router.get('/calendar/appt')
async def get_job_appointments(
    job_id: int = Query(..., description="Job ID to get appointments for"),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    """
    Get all appointments for a specific job.
    """
    query = """
        SELECT calendar_id, calendar_type, start_time, end_time, start_date, end_date,
               participant, calendar_desc, outcome_score
        FROM calendar
        WHERE job_id = :job_id AND user_id = :user_id
        ORDER BY start_date DESC, start_time DESC
    """

    result = db.execute(text(query), {"job_id": job_id, "user_id": user_id})

    return [
        {
            "calendar_id": row.calendar_id,
            "calendar_type": row.calendar_type,
            "start_time": str(row.start_time) if row.start_time else None,
            "end_time": str(row.end_time) if row.end_time else None,
            "start_date": str(row.start_date) if row.start_date else None,
            "end_date": str(row.end_date) if row.end_date else None,
            "participant": row.participant or [],
            "calendar_desc": row.calendar_desc,
            "outcome_score": row.outcome_score
        }
        for row in result
    ]


@router.get("/calendar/month", response_model=List[CalendarSchema])
async def get_month_calendar(
    date: str = Query(..., description="Date in YYYY-MM format"),
    job_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    """
    Get calendar appointments for a specific month.
    """
    try:
        start_date, end_date = get_month_date_range(date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM")

    query = """
        SELECT c.*, j.company
        FROM calendar c
        JOIN job j ON c.job_id = j.job_id
        WHERE c.start_date BETWEEN :start_date AND :end_date AND c.user_id = :user_id
    """

    params = {"start_date": start_date, "end_date": end_date, "user_id": user_id}

    if job_id:
        query += " AND c.job_id = :job_id"
        params["job_id"] = job_id

    query += " ORDER BY c.start_date ASC, c.start_time ASC"

    result = db.execute(text(query), params)

    return [
        CalendarSchema(
            calendar_id=row.calendar_id,
            job_id=row.job_id,
            company=row.company,
            calendar_type=row.calendar_type,
            start_date=row.start_date,
            start_time=row.start_time,
            end_date=row.end_date,
            end_time=row.end_time,
            duration_hour=float(row.duration_hour) if row.duration_hour else None,
            participant=row.participant or [],
            calendar_desc=row.calendar_desc,
            calendar_note=row.calendar_note,
            outcome_score=row.outcome_score,
            outcome_note=row.outcome_note,
            video_link=row.video_link
        )
        for row in result
    ]


@router.get("/calendar/week", response_model=List[CalendarSchema])
async def get_week_calendar(
    date: str = Query(..., description="Date in YYYY-MM-DD format (must be Monday)"),
    job_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    """
    Get calendar appointments for a specific week.
    """
    if not validate_week_start(date):
        raise HTTPException(status_code=400, detail="Date must be a Monday (first day of the week)")

    try:
        start_date, end_date = get_week_date_range(date)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    query = """
        SELECT c.*, j.company
        FROM calendar c
        JOIN job j ON c.job_id = j.job_id
        WHERE c.user_id = :user_id AND c.start_date BETWEEN :start_date AND :end_date
    """

    params = {"start_date": start_date, "end_date": end_date, "user_id": user_id}

    if job_id:
        query += " AND c.job_id = :job_id"
        params["job_id"] = job_id

    query += " ORDER BY c.start_date ASC, c.start_time ASC"

    result = db.execute(text(query), params)

    return [
        CalendarSchema(
            calendar_id=row.calendar_id,
            job_id=row.job_id,
            company=row.company,
            calendar_type=row.calendar_type,
            start_date=row.start_date,
            start_time=row.start_time,
            end_date=row.end_date,
            end_time=row.end_time,
            duration_hour=float(row.duration_hour) if row.duration_hour else None,
            participant=row.participant or [],
            calendar_desc=row.calendar_desc,
            calendar_note=row.calendar_note,
            outcome_score=row.outcome_score,
            outcome_note=row.outcome_note,
            video_link=row.video_link
        )
        for row in result
    ]


@router.get("/calendar/day", response_model=List[CalendarSchema])
async def get_day_calendar(
    date: str = Query(..., description="Date in YYYY-MM-DD format"),
    job_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    """
    Get calendar appointments for a specific day.
    """
    query = """
        SELECT c.*, j.company
        FROM calendar c
        JOIN job j ON c.job_id = j.job_id
        WHERE c.user_id = :user_id AND c.start_date = :date
    """

    params = {"date": date, "user_id": user_id}

    if job_id:
        query += " AND c.job_id = :job_id"
        params["job_id"] = job_id

    query += " ORDER BY c.start_date ASC, c.start_time ASC"

    result = db.execute(text(query), params)

    return [
        CalendarSchema(
            calendar_id=row.calendar_id,
            job_id=row.job_id,
            company=row.company,
            calendar_type=row.calendar_type,
            start_date=row.start_date,
            start_time=row.start_time,
            end_date=row.end_date,
            end_time=row.end_time,
            duration_hour=float(row.duration_hour) if row.duration_hour else None,
            participant=row.participant or [],
            calendar_desc=row.calendar_desc,
            calendar_note=row.calendar_note,
            outcome_score=row.outcome_score,
            outcome_note=row.outcome_note,
            video_link=row.video_link
        )
        for row in result
    ]


@router.post("/calendar")
async def create_or_update_calendar(
    calendar_data: CalendarUpdate,
    job_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user)
):
    """
    Create a new calendar event or update an existing one.
    """

    calendar_data.user_id = user_id
    # Use job_id from query parameter if provided and not in body
    if job_id and not calendar_data.job_id:
        calendar_data.job_id = job_id

    if not calendar_data.job_id:
        raise HTTPException(status_code=400, detail="job_id is required")

    # Verify job exists and belongs to user
    job = db.query(Job).filter(Job.job_id == calendar_data.job_id, Job.user_id == user_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if calendar_data.calendar_id:
        # Update existing calendar event - ensure it belongs to user
        calendar_event = db.query(Calendar).filter(
            Calendar.calendar_id == calendar_data.calendar_id,
            Calendar.user_id == user_id
        ).first()
        if not calendar_event:
            raise HTTPException(status_code=404, detail="Calendar event not found")

        # Update fields that are provided
        update_data = calendar_data.dict(exclude_unset=True, exclude={'calendar_id'})
        for field, value in update_data.items():
            setattr(calendar_event, field, value)

    else:
        # Create new calendar event
        calendar_dict = calendar_data.model_dump(exclude={'calendar_id'}, exclude_unset=True)
        calendar_event = Calendar(**calendar_dict)
        db.add(calendar_event)

    db.commit()
    db.refresh(calendar_event)

    # Update job activity
    if calendar_event.job_id:
        try:
            update_job_activity(db, calendar_event.job_id)
        except Exception as e:
            logger.warning(f"Failed to update job activity", job_id=calendar_event.job_id, error=str(e))

        # Calculate and update average score
        try:
            calc_avg_score(db, calendar_event.job_id)
        except Exception as e:
            logger.warning(f"Failed to calculate average score", job_id=calendar_event.job_id, error=str(e))

    return {"status": "success", "calendar_id": calendar_event.calendar_id}


@router.get("/calendar/{calendar_id}", response_model=CalendarSchema)
async def get_calendar_event(
    calendar_id: int,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    """
    Get a single calendar event by ID.
    This route must be defined AFTER the specific routes (/month, /week, /day)
    to avoid path conflicts.
    """

    query = """
        SELECT c.*, j.company
        FROM calendar c
        JOIN job j ON c.job_id = j.job_id
        WHERE c.user_id = :user_id AND c.calendar_id = :calendar_id
    """

    result = db.execute(text(query), {"calendar_id": calendar_id, "user_id": user_id}).fetchone()

    if not result:
        raise HTTPException(status_code=404, detail="Calendar event not found")

    return CalendarSchema(
        calendar_id=result.calendar_id,
        job_id=result.job_id,
        company=result.company,
        calendar_type=result.calendar_type,
        start_date=result.start_date,
        start_time=result.start_time,
        end_date=result.end_date,
        end_time=result.end_time,
        duration_hour=float(result.duration_hour) if result.duration_hour else None,
        participant=result.participant or [],
        calendar_desc=result.calendar_desc,
        calendar_note=result.calendar_note,
        outcome_score=result.outcome_score,
        outcome_note=result.outcome_note,
        video_link=result.video_link
    )


@router.delete("/calendar/appt")
async def delete_calendar_appointment(
    appointment_id: int = Query(..., description="Calendar appointment ID to delete"),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    """
    Delete a calendar appointment by ID.
    """

    try:
        # Check if appointment exists and belongs to user
        appointment = db.query(Calendar).filter(
            Calendar.calendar_id == appointment_id,
            Calendar.user_id == user_id
        ).first()

        if not appointment:
            raise HTTPException(status_code=404, detail="Appointment not found")

        # Store job_id before deleting for average score recalculation
        job_id = appointment.job_id

        # Delete the appointment
        db.delete(appointment)
        db.commit()

        # Recalculate average score if appointment had a job_id
        if job_id:
            try:
                calc_avg_score(db, job_id)
            except Exception as e:
                logger.warning(f"Failed to recalculate average score after delete", job_id=job_id, error=str(e))

        logger.info(f"Deleted calendar appointment", appointment_id=appointment_id, job_id=job_id, user_id=user_id)

        return {"message": "Appointment deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting calendar appointment", appointment_id=appointment_id, error=str(e), user_id=user_id)
        raise HTTPException(status_code=500, detail="Failed to delete appointment")