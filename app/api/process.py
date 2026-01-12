from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from ..core.database import get_db
from ..utils.logger import logger
from ..models.models import Process
from ..schemas.process import ProcessBase, PollResponse

router = APIRouter()


class PollRequest(BaseModel):
    process_id: int


@router.get("/poll/{process_id}", response_model=PollResponse)
async def poll_status(process_id: int, db: Session = Depends(get_db)):
    """
    Get the current state of a process based on the process_id

    Args:
        request: PollRequest with process_id
        db: Database session

    Returns:
        PollResponse with process_state: string (running, complete, confirmed, failed)
    """

    process = db.query(Process).filter(Process.process_id == process_id).first()
    if not process:
        logger.warning(f"Process not found", process_id=process_id)
        raise HTTPException(status_code=404, detail="Process not found")

    # Determine process state based on column values
    # Priority: failed > confirmed > complete > running
    if process.failed:
        process_state = "failed"
    elif process.confirmed:
        process_state = "confirmed"
    elif process.completed is not None:
        process_state = "complete"
    else:
        process_state = "running"

    # If process just completed, mark as confirmed for next poll
    if process_state == "complete" and not process.confirmed:
        process.confirmed = True
        db.commit()

    return PollResponse(process_state=process_state)









