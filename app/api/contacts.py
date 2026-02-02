from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text

from ..core.database import get_db
from ..models.models import Contact, Job, JobContact
from ..schemas.contact import Contact as ContactSchema, ContactUpdate, ContactWithLinks, ContactLinkedJob
from ..utils.logger import logger
from ..utils.job_helpers import update_job_activity
from ..middleware.auth_middleware import get_current_user

router = APIRouter()


@router.post("/contact")
async def create_or_update_contact(
    contact_data: ContactUpdate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user)
):
    """
    Create a new contact or update an existing one.
    If job_id is provided, also create/verify the job_contact link.
    """

    is_update = bool(contact_data.contact_id)
    action = "update" if is_update else "create"
    job_id = contact_data.job_id
    contact_data.user_id = user_id

    logger.info(f"Attempting to {action} contact", contact_id=contact_data.contact_id, name=f"{contact_data.first_name} {contact_data.last_name}", job_id=job_id, user_id=user_id)

    if contact_data.contact_id:
        # Update existing contact - ensure it belongs to user
        contact = db.query(Contact).filter(
            Contact.contact_id == contact_data.contact_id,
            Contact.user_id == user_id
        ).first()
        if not contact:
            logger.warning(f"Contact not found for update", contact_id=contact_data.contact_id, user_id=user_id)
            raise HTTPException(status_code=404, detail="Contact not found")

        # Update fields that are provided (exclude job_id as it's not a Contact field)
        update_data = contact_data.model_dump(exclude_unset=True, exclude={'contact_id', 'job_id'})
        for field, value in update_data.items():
            setattr(contact, field, value)

    else:
        # Create new contact (exclude job_id as it's not a Contact field)
        contact_dict = contact_data.model_dump(exclude={'contact_id', 'job_id'}, exclude_unset=True)
        contact = Contact(**contact_dict)
        db.add(contact)

    db.commit()
    db.refresh(contact)

    # Handle job_contact linking if job_id is provided
    if job_id:
        # Verify the job exists and belongs to user
        job = db.query(Job).filter(Job.job_id == job_id, Job.user_id == user_id).first()
        if not job:
            logger.warning(f"Job not found for linking", job_id=job_id, user_id=user_id)
        else:
            # Check if the link already exists
            existing_link = db.query(JobContact).filter(
                JobContact.job_id == job_id,
                JobContact.contact_id == contact.contact_id
            ).first()

            if not existing_link:
                # Create the job_contact link
                job_contact = JobContact(job_id=job_id, contact_id=contact.contact_id)
                db.add(job_contact)
                db.commit()
                logger.info(f"Created job_contact link", job_id=job_id, contact_id=contact.contact_id)
            else:
                logger.debug(f"Job_contact link already exists", job_id=job_id, contact_id=contact.contact_id)

            # Update job activity
            try:
                update_job_activity(db, job_id)
            except Exception as e:
                logger.warning(f"Failed to update job activity", job_id=job_id, error=str(e))

    logger.log_database_operation("UPDATE" if is_update else "INSERT", "contacts", contact.contact_id)
    logger.info(f"Contact {action}d successfully", contact_id=contact.contact_id)

    return {"status": "success", "contact_id": contact.contact_id}


@router.delete("/contact/{contact_id}")
async def delete_contact(
    contact_id: int,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    """
    Soft delete a contact by setting contact_active to false.
    """

    contact = db.query(Contact).filter(
        Contact.contact_id == contact_id,
        Contact.user_id == user_id
    ).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    contact.contact_active = False
    db.commit()

    return {"status": "success"}


@router.get("/contact/{contact_id}", response_model=ContactWithLinks)
async def get_contact(
    contact_id: int,
    job_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    """
    Get a single contact by ID with linked jobs.
    """
    contact = db.query(Contact).filter(
        Contact.contact_id == contact_id,
        Contact.user_id == user_id,
        Contact.contact_active == True
    ).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    # Get linked jobs (filtered by user)
    query = """
        SELECT j.job_id, j.job_title, j.company
        FROM job_contact jc
        JOIN job j ON (jc.job_id = j.job_id)
        WHERE jc.contact_id = :contact_id AND j.user_id = :user_id
    """

    if job_id:
        query += " AND j.job_id = :job_id"
        result = db.execute(text(query), {"contact_id": contact_id, "job_id": job_id, "user_id": user_id})
    else:
        result = db.execute(text(query), {"contact_id": contact_id, "user_id": user_id})

    linked_jobs = [
        ContactLinkedJob(job_id=row.job_id, job_title=row.job_title, company=row.company)
        for row in result
    ]

    # Convert contact to dict and add linked_to
    contact_dict = {
        "contact_id": contact.contact_id,
        "first_name": contact.first_name,
        "last_name": contact.last_name,
        "job_title": contact.job_title,
        "email": contact.email,
        "phone": contact.phone,
        "company": contact.company,
        "linkedin": contact.linkedin,
        "contact_note": contact.contact_note,
        "linked_to": linked_jobs
    }

    return contact_dict


@router.get("/contacts", response_model=List[ContactSchema])
async def get_contacts(
    job_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    """
    Get all contacts, optionally filtered by job_id.
    """
    logger.debug("Fetching contacts list", job_id=job_id, user_id=user_id)

    if job_id:
        # Get contacts linked to specific job
        query = """
            SELECT DISTINCT c.*
            FROM contact c
            JOIN job_contact jc ON c.contact_id = jc.contact_id
            WHERE c.contact_active = true AND c.user_id = :user_id AND jc.job_id = :job_id
            ORDER BY c.first_name, c.last_name
        """
        result = db.execute(text(query), {"job_id": job_id, "user_id": user_id})
        contacts = [
            ContactSchema(
                contact_id=row.contact_id,
                first_name=row.first_name,
                last_name=row.last_name,
                job_title=row.job_title,
                email=row.email,
                phone=row.phone,
                company=row.company,
                linkedin=row.linkedin,
                contact_note=row.contact_note
            )
            for row in result
        ]
    else:
        # Get all contacts for this user
        contacts = db.query(Contact).filter(
            Contact.contact_active == True,
            Contact.user_id == user_id
        ).order_by(
            Contact.first_name.asc(),
            Contact.last_name.asc()
        ).all()

    logger.log_database_operation("SELECT", "contacts")
    logger.debug(f"Contacts retrieved", count=len(contacts), job_id=job_id, user_id=user_id)
    return contacts