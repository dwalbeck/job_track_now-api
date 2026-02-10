from pydantic import BaseModel
from typing import Optional, List

class InterviewQuestionRequest(BaseModel):
    job_id: int
    company_id: int

class InterviewQuestionResponse(BaseModel):
    interview_id: int
    questions: List

class InterviewAnswerRequest(BaseModel):
    interview_id: int
    question_id: int
    answer: str

class InterviewAnswerResponse(BaseModel):
    question_id: int
    question_order: int
    question: str
    sound_file: str
    response_audio_file: str


class TranscribeRequest(BaseModel):
    interview_id: int

class TranscribeResponse(BaseModel):
    text: str

class AudioRequest(BaseModel):
    interview_id: int
    question_id: int
    statement: bool

class InterviewReviewResponse(BaseModel):
    interview_score: int
    interview_feedback: str
    hiring_decision: str
    questions: List

class InterviewListResponse(BaseModel):
    interview_id: int
    interview_score: int
    interview_created: str
    company_name: str
    job_title: str
