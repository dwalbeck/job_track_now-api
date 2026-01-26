from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import text

from ..core.database import get_db
from ..models.models import Note, Job
from ..schemas.note import Note as NoteSchema, NoteCreate, NoteUpdate
from ..utils.job_helpers import update_job_activity
from ..utils.logger import logger
from ..middleware.auth_middleware import get_current_user

router = APIRouter()


@router.get("/notes", response_model=List[NoteSchema])
async def get_notes(
    job_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get all notes, optionally filtered by job_id.
    """
    user_id = current_user.get("user_id")
    query = """
        SELECT n.*, j.company, j.job_title
        FROM note n
        JOIN job j ON (n.job_id = j.job_id)
        WHERE n.note_active = true AND n.user_id = :user_id
    """

    params = {"user_id": user_id}

    if job_id:
        query += " AND n.job_id = :job_id"
        params["job_id"] = job_id

    query += " ORDER BY n.note_created DESC"

    result = db.execute(text(query), params)

    return [
        NoteSchema(
            note_id=row.note_id,
            job_id=row.job_id,
            note_title=row.note_title,
            note_content=row.note_content,
            note_score=row.note_score,
            communication_type=row.communication_type,
            note_created=row.note_created,
            job_title=row.job_title,
            company=row.company
        )
        for row in result
    ]


async def _create_or_update_note(note_data: NoteUpdate, db: Session, user_id: int):
    """
    Internal function to create or update a note.
    """
    is_update = bool(note_data.note_id)
    action = "update" if is_update else "create"

    # Validate required fields for new notes
    if not note_data.note_id:
        if not note_data.job_id or not note_data.note_title:
            raise HTTPException(
                status_code=400,
                detail="job_id and note_title are required for new notes"
            )

    # Verify job exists and belongs to user
    if note_data.job_id:
        job = db.query(Job).filter(Job.job_id == note_data.job_id, Job.user_id == user_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

    if note_data.note_id:
        # Update existing note - ensure it belongs to user
        note = db.query(Note).filter(
            Note.note_id == note_data.note_id,
            Note.user_id == user_id
        ).first()
        if not note:
            raise HTTPException(status_code=404, detail="Note not found")

        # Update fields that are provided
        update_data = note_data.model_dump(exclude_unset=True, exclude={'note_id'})
        for field, value in update_data.items():
            setattr(note, field, value)

    else:
        # Create new note
        note_dict = note_data.model_dump(exclude={'note_id'}, exclude_unset=True)
        note_dict['user_id'] = user_id
        note = Note(**note_dict)
        db.add(note)

    db.commit()
    db.refresh(note)

    # Update job activity
    if note.job_id:
        try:
            update_job_activity(db, note.job_id)
        except Exception as e:
            logger.warning(f"Failed to update job activity", job_id=note.job_id, error=str(e))

    return {"status": "success", "note_id": note.note_id}


@router.post("/note")
async def create_or_update_note(
    note_data: NoteUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new note or update an existing one.
    """
    user_id = current_user.get("user_id")
    return await _create_or_update_note(note_data, db, user_id)


@router.post("/notes")
async def create_or_update_note_plural(
    note_data: NoteUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new note or update an existing one (plural route for compatibility).
    """
    user_id = current_user.get("user_id")
    return await _create_or_update_note(note_data, db, user_id)


@router.delete("/note/{note_id}")
async def delete_note(
    note_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Soft delete a note by setting note_active to false.
    """
    user_id = current_user.get("user_id")
    note = db.query(Note).filter(
        Note.note_id == note_id,
        Note.user_id == user_id
    ).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    note.note_active = False
    db.commit()

    return {"status": "success"}