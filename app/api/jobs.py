from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text

from ..core.database import get_db
from ..models.models import Job, JobDetail
from ..schemas.job import Job as JobSchema, JobCreate, JobUpdate, JobList, JobExtractRequest, JobExtractResponse, JobDetailCreate
from ..utils.directory import create_job_directory
from ..utils.ai_agent import AiAgent
from ..utils.logger import logger
from ..utils.job_helpers import calc_avg_score
from ..middleware.auth_middleware import get_current_user

router = APIRouter()


@router.get("/jobs", response_model=List[JobSchema])
async def get_all_jobs(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    """
    Get all active jobs ordered by last activity (newest first).
    Includes latest calendar appointment data if available.
    """

    logger.debug("Fetching all active jobs", user_id=user_id)

    # Use raw SQL to include calendar data from next upcoming appointment
    # Include same-day appointments regardless of time (for post-interview scoring prompts)
    query = text("""
        SELECT c.calendar_id, c.start_date, c.start_time, c.end_time, j.*
        FROM job j
            LEFT JOIN LATERAL (
                SELECT start_date, start_time, end_time, calendar_id
                FROM calendar c_inner
                WHERE c_inner.job_id=j.job_id
                    AND c_inner.user_id = :user_id
                    AND c_inner.start_date >= CURRENT_DATE
                ORDER BY start_date ASC, start_time ASC
                LIMIT 1
            ) AS c ON TRUE
        WHERE j.job_active = true AND j.user_id = :user_id
        ORDER BY j.last_activity DESC
    """)

    result = db.execute(query, {"user_id": user_id}).fetchall()

    logger.log_database_operation("SELECT", "job")
    logger.debug(f"Retrieved all jobs", count=len(result), user_id=user_id)

    # Convert rows to dicts
    jobs = [dict(row._mapping) for row in result]
    return jobs


@router.delete("/job/{job_id}")
async def delete_job(
    job_id: int,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    """
    Soft delete a job by setting job_active to false.
    """

    logger.info(f"Attempting to delete job", job_id=job_id, user_id=user_id)

    job = db.query(Job).filter(Job.job_id == job_id, Job.user_id == user_id).first()
    if not job:
        logger.warning(f"Job not found for deletion", job_id=job_id, user_id=user_id)
        raise HTTPException(status_code=404, detail="Job not found")

    job.job_active = False
    db.commit()
    logger.log_database_operation("DELETE", "jobs", job_id)
    logger.info(f"Job successfully deleted", job_id=job_id, user_id=user_id)

    return {"status": "success"}


@router.get("/job/list", response_model=List[JobList])
async def get_job_list(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    """
    Get a list of jobs for dropdown selection.
    """

    logger.debug("Fetching job list for dropdown", user_id=user_id)

    jobs = db.query(Job.job_id, Job.company, Job.job_title).filter(
        Job.job_active == True,
        Job.user_id == user_id
    ).order_by(
        Job.last_activity.desc(),
        Job.date_applied.desc()
    ).all()

    logger.log_database_operation("SELECT", "jobs")
    logger.debug(f"Job list retrieved", count=len(jobs), user_id=user_id)
    return [{"job_id": job.job_id, "company": job.company, "job_title": job.job_title} for job in jobs]


@router.get("/job/{job_id}")
async def get_job(
    job_id: int,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    """
    Get a single job by ID with job_detail fields included.
    """

    logger.debug(f"Fetching job", job_id=job_id, user_id=user_id)

    # Use a SQL query to join job and job_detail tables
    query = text("""
        SELECT j.*, jd.job_desc, jd.job_qualification, jd.job_keyword
        FROM job j
        LEFT JOIN job_detail jd ON j.job_id = jd.job_id
        WHERE j.job_id = :job_id AND j.job_active = true AND j.user_id = :user_id
    """)

    result = db.execute(query, {"job_id": job_id, "user_id": user_id}).first()

    if not result:
        logger.warning(f"Job not found", job_id=job_id, user_id=user_id)
        raise HTTPException(status_code=404, detail="Job not found")

    logger.log_database_operation("SELECT", "jobs", job_id)
    logger.debug(f"Job retrieved successfully", job_id=job_id, company=result.company, user_id=user_id)

    # Convert row to dict
    job_dict = dict(result._mapping)
    return job_dict


@router.post("/job")
async def create_or_update_job(
    job_data: JobUpdate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    """
    Create a new job or update an existing one.
    """

    is_update = bool(job_data.job_id)
    action = "update" if is_update else "create"

    logger.info(f"Attempting to {action} job", job_id=job_data.job_id, company=job_data.company, user_id=user_id)

    # Extract job_desc before processing (it belongs in job_detail table)
    job_desc = job_data.job_desc

    # Validate required fields for new jobs
    if not job_data.job_id:
        if not job_data.company or not job_data.job_title or not job_data.job_status:
            logger.error("Missing required fields for new job creation", company=job_data.company, job_title=job_data.job_title)
            raise HTTPException(
                status_code=400,
                detail="company, job_title, and job_status are required for new jobs"
            )

    if job_data.job_id:
        # Update existing job - ensure user owns this job
        job = db.query(Job).filter(Job.job_id == job_data.job_id, Job.user_id == user_id).first()
        if not job:
            logger.warning(f"Job not found for update", job_id=job_data.job_id, user_id=user_id)
            raise HTTPException(status_code=404, detail="Job not found")

        logger.debug(f"Updating existing job", job_id=job_data.job_id, user_id=user_id)
        # Update fields that are provided (excluding job_desc and average_score which are managed separately)
        update_data = job_data.dict(exclude_unset=True, exclude={'job_id', 'job_desc', 'average_score'})
        for field, value in update_data.items():
            setattr(job, field, value)

        # Update job directory if company or job_title changed
        if 'company' in update_data or 'job_title' in update_data:
            old_directory = job.job_directory
            job.job_directory = create_job_directory(job.company, job.job_title)
            logger.debug(f"Updated job directory", old_directory=old_directory, new_directory=job.job_directory)

    else:
        # Create new job
        logger.debug(f"Creating new job", company=job_data.company, job_title=job_data.job_title, user_id=user_id)
        job_dict = job_data.dict(exclude={'job_id', 'job_desc', 'average_score'}, exclude_unset=True, exclude_none=True)

        # Add user_id to new job
        job_dict['user_id'] = user_id

        # Create job directory
        job_directory = create_job_directory(job_dict['company'], job_dict['job_title'])
        job_dict['job_directory'] = job_directory
        logger.debug(f"Created job directory", directory=job_directory)

        job = Job(**job_dict)
        db.add(job)

    db.commit()
    db.refresh(job)

    # Handle job_desc in job_detail table
    if job_desc is not None:
        job_detail = db.query(JobDetail).filter(JobDetail.job_id == job.job_id).first()
        if job_detail:
            # Update existing job_detail
            job_detail.job_desc = job_desc
            logger.debug(f"Updated job_detail for job", job_id=job.job_id)
        else:
            # Create new job_detail
            job_detail = JobDetail(job_id=job.job_id, job_desc=job_desc)
            db.add(job_detail)
            logger.debug(f"Created job_detail for job", job_id=job.job_id)
        db.commit()

    # Update average score (for new jobs, sets it to interest_level; for updates, recalculates if interest_level changed)
    calc_avg_score(db, job.job_id)
    logger.debug(f"{'Recalculated' if is_update else 'Calculated'} average score for job", job_id=job.job_id)

    logger.log_database_operation("UPDATE" if is_update else "INSERT", "jobs", job.job_id)
    logger.info(f"Job {action}d successfully", job_id=job.job_id, company=job.company)

    return {"status": "success", "job_id": job.job_id}


@router.post("/job/extract", response_model=JobExtractResponse)
async def extract_job_data(
    extract_request: JobExtractRequest,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    """
    Extract job qualifications and keywords from a job description using AI.

    This endpoint uses OpenAI to analyze the job description and extract:
    - Job qualification section text
    - Relevant keywords and skills

    The extracted data is automatically saved to the job_detail table.

    JSON body:
    - job_id: ID of the job to analyze

    Returns:
    - job_qualification: Extracted qualification section
    - keywords: List of extracted keywords
    """

    logger.info(f"Extracting job data", job_id=extract_request.job_id, user_id=user_id)

    try:
        # Verify that the job exists and belongs to user
        job = db.query(Job).filter(Job.job_id == extract_request.job_id, Job.user_id == user_id).first()
        if not job:
            logger.warning(f"Job not found for extraction", job_id=extract_request.job_id, user_id=user_id)
            raise HTTPException(status_code=404, detail="Job not found")

        # Check if job_detail already has qualifications and keywords
        check_query = text("""
            SELECT jd.job_qualification, jd.job_keyword
            FROM job j
            JOIN job_detail jd ON (j.job_id = jd.job_id)
            WHERE j.job_id = :job_id AND j.user_id = :user_id
        """)
        existing_data = db.execute(check_query, {"job_id": extract_request.job_id, "user_id": user_id}).first()

        # If both qualification and keywords exist, return cached data
        if existing_data and existing_data.job_qualification and existing_data.job_keyword:
            logger.info(f"Using cached job qualification and keywords", job_id=extract_request.job_id, user_id=user_id)
            return JobExtractResponse(
                job_qualification=existing_data.job_qualification,
                keywords=list(existing_data.job_keyword)
            )

        # Initialize AI agent with database session
        ai_agent = AiAgent(db)

        # Extract data using AI
        result = ai_agent.job_extraction(job_id=extract_request.job_id, user_id=user_id)

        logger.log_database_operation("UPDATE", "job_detail", extract_request.job_id)
        logger.info(f"Job data extracted successfully", job_id=extract_request.job_id, keyword_count=len(result['keywords']), user_id=user_id)

        # Return the response
        return JobExtractResponse(
            job_qualification=result['job_qualification'],
            keywords=result['keywords']
        )

    except HTTPException:
        # Let HTTPExceptions pass through unchanged
        raise
    except ValueError as e:
        # Handle job not found or empty job_desc errors
        logger.error(f"Validation error during extraction", job_id=extract_request.job_id, error=str(e), user_id=user_id)
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        # Handle unexpected errors
        logger.error(f"Error extracting job data", job_id=extract_request.job_id, error=str(e), user_id=user_id)
        raise HTTPException(
            status_code=500,
            detail=f"Error extracting job data: {str(e)}"
        )


@router.post("/job/detail")
async def create_or_update_job_detail(
    detail_data: JobDetailCreate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    """
    Create or update job detail information.

    This endpoint handles both insert and update operations based on whether
    a record exists in the job_detail table for the given job_id.

    JSON body:
    - job_id: ID of the job (required)
    - job_desc: Job description text
    - job_qualification: Job qualification section
    - job_keyword: List of keywords

    Returns HTTP 200 on success.
    """

    logger.info(f"Creating/updating job detail", job_id=detail_data.job_id, user_id=user_id)

    # Verify that the job exists and belongs to user
    job = db.query(Job).filter(Job.job_id == detail_data.job_id, Job.user_id == user_id).first()
    if not job:
        logger.warning(f"Job not found for job detail", job_id=detail_data.job_id, user_id=user_id)
        raise HTTPException(status_code=404, detail="Job not found")

    # Check if a detail record already exists for this job_id
    existing_detail = db.query(JobDetail).filter(
        JobDetail.job_id == detail_data.job_id
    ).first()

    if existing_detail:
        # Update existing record
        logger.debug(f"Updating existing job detail", job_id=detail_data.job_id, user_id=user_id)

        # Update only the fields that are provided (not None)
        update_data = detail_data.dict(exclude={'job_id'}, exclude_unset=True)

        for field, value in update_data.items():
            setattr(existing_detail, field, value)

        db.commit()
        db.refresh(existing_detail)

        logger.log_database_operation("UPDATE", "job_detail", existing_detail.job_id)
        logger.info(f"Job detail updated successfully", job_id=existing_detail.job_id, user_id=user_id)

        return {"status": "success", "job_id": existing_detail.job_id}

    else:
        # Insert new record
        logger.debug(f"Creating new job detail", job_id=detail_data.job_id, user_id=user_id)

        new_detail = JobDetail(
            job_id=detail_data.job_id,
            job_desc=detail_data.job_desc,
            job_qualification=detail_data.job_qualification,
            job_keyword=detail_data.job_keyword
        )

        db.add(new_detail)
        db.commit()
        db.refresh(new_detail)

        logger.log_database_operation("INSERT", "job_detail", new_detail.job_id)
        logger.info(f"Job detail created successfully", job_id=new_detail.job_id, user_id=user_id)

        return {"status": "success", "job_id": new_detail.job_id}