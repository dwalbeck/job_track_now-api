from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import text

from ..core.database import get_db
from ..schemas.tools import ToolsPitchResponse, ToolsPitchRequest, ToolsRewriteRequest, ToolsRewriteResponse
from ..utils.ai_agent import AiAgent
from ..utils.logger import logger
from ..middleware.auth_middleware import get_current_user

router = APIRouter()

@router.post("/pitch", response_model=ToolsPitchResponse)
async def elevator_pitch(
		request: ToolsPitchRequest,
		db: Session = Depends(get_db),
		current_user: dict = Depends(get_current_user)
):
	"""
	This endpoint will write an elevator pitch.  It will first query the DB for the resume and job desc (if job_id is present). Then it
	will make a call to the AI class to execute a call to OpenAI API.  It then relays the response back to the frontend.

	:param request: ToolsPitchRequest with optional job_id
	:param db: Database session
	:param current_user: Current authenticated user
	:return: ToolsPitchResponse with pitch
	"""
	user_id = current_user.get("user_id")
	logger.debug(f"Starting endpoint /v1/tools/pitch", job_id=request.job_id, user_id=user_id)

	try:
		resume = None
		job_desc = None

		if request.job_id:
			logger.debug(f"Query DB with Job", job_id=request.job_id, user_id=user_id)
			query = text("""
				SELECT jd.job_desc, rd.resume_html_rewrite
		        FROM job j
		        JOIN job_detail jd ON (j.job_id=jd.job_id)
		        LEFT JOIN resume_detail rd ON (j.resume_id=rd.resume_id)
		        WHERE j.job_id=:job_id AND j.user_id=:user_id
			""")
			result = db.execute(query, {"job_id": request.job_id, "user_id": user_id}).fetchone()

			if not result:
				logger.warning(f"Job and resume not found", job_id=request.job_id, user_id=user_id)
				raise HTTPException(status_code=404, detail="Job and Resume not found")

			job_desc = result[0]
			resume = result[1]

		else:
			logger.debug(f"Query DB for baseline resume", user_id=user_id)
			query = text("""
				SELECT rd.resume_markdown
			    FROM resume r
			    JOIN resume_detail rd ON (r.resume_id=rd.resume_id)
			    WHERE r.is_baseline=true AND r.is_default=true AND r.user_id=:user_id
			""")
			result = db.execute(query, {"user_id": user_id}).fetchone()

			if not result:
				logger.warning(f"Baseline resume not found", user_id=user_id)
				raise HTTPException(status_code=404, detail="Baseline resume not found")

			resume = result[0]

		# Initialize AI agent with database session
		ai_agent = AiAgent(db)

		logger.debug(f"Calling AI agent elevator_pitch", job_id=request.job_id, user_id=user_id)
		# Generate elevator pitch using AI
		result = ai_agent.elevator_pitch(
			resume=resume,
			job_desc=job_desc if job_desc else ""
		)

		logger.debug(f"Completed and returning results", user_id=user_id)
		return ToolsPitchResponse(
			pitch=result['pitch']
		)

	except HTTPException:
		# Re-raise HTTP exceptions
		raise
	except Exception as e:
		logger.error(f"Error generating elevator pitch: {str(e)}", user_id=user_id)
		raise HTTPException(status_code=500, detail=f"Error generating elevator pitch: {str(e)}")

@router.post("/rewrite", response_model=ToolsRewriteResponse)
async def rewrite_text(
		request: ToolsRewriteRequest,
		db: Session = Depends(get_db),
		current_user: dict = Depends(get_current_user)
):
	"""
	This endpoint will rewrite a text blob using AI to improve clarity, grammar, and professionalism.

	:param request: ToolsRewriteRequest with text_blob
	:param db: Database session
	:param current_user: Current authenticated user
	:return: ToolsRewriteResponse with original, new text, and explanation
	"""
	user_id = current_user.get("user_id")
	logger.debug(f"Starting endpoint /v1/tools/rewrite", user_id=user_id)

	try:
		# Initialize AI agent with database session
		ai_agent = AiAgent(db)

		logger.debug(f"Calling AI agent rewrite_blob", user_id=user_id)
		# Rewrite text using AI
		result = ai_agent.rewrite_blob(
			text_blob=request.text_blob
		)

		logger.debug(f"Completed and returning results", user_id=user_id)
		return ToolsRewriteResponse(
			original_text_blob=request.text_blob,
			new_text_blob=result['new_text_blob'],
			explanation=result['explanation']
		)

	except Exception as e:
		logger.error(f"Error rewriting text: {str(e)}", user_id=user_id)
		raise HTTPException(status_code=500, detail=f"Error rewriting text: {str(e)}")