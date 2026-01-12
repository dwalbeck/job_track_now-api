from pydantic import BaseModel
from typing import Optional
from datetime import date, time
from enum import Enum


class DurationType(str, Enum):
    """Valid duration types for reminder list"""
    day = "day"
    week = "week"
    month = "month"


class ReminderCreate(BaseModel):
    """Schema for creating or updating a reminder"""
    reminder_date: date
    reminder_time: time
    reminder_message: str
    reminder_dismissed: bool = False
    job_id: Optional[int] = None
    reminder_id: Optional[int] = None


class ReminderListRequest(BaseModel):
    """Schema for listing reminders"""
    duration: DurationType = DurationType.month
    start_date: date
    job_id: Optional[int] = None


class ReminderListResponse(BaseModel):
    """Schema for reminder list item"""
    reminder_id: int
    reminder_date: date
    reminder_time: Optional[time]
    reminder_message: str
    job_id: Optional[int] = None
