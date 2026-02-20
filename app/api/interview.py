from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional
from pathlib import Path
import os
import shutil
from openai import OpenAI
from ..utils.file_helpers import create_standardized_download_file, get_tts_audio, change_filename
from ..core.database import get_db
from ..schemas.interview import InterviewQuestionRequest, InterviewAnswerRequest, TranscribeResponse, AudioRequest, InterviewAnswerResponse, InterviewReviewResponse, InterviewQuestionResponse, InterviewListResponse
from ..middleware.auth_middleware import get_current_user
from ..utils.ai_agent import AiAgent
from ..utils.logger import logger
from ..core.config import settings

router = APIRouter()



@router.post("/interview/question", status_code=status.HTTP_200_OK)
async def interview_question(
	interview_data: InterviewQuestionRequest,
	db: Session = Depends(get_db),
	user_id: int = Depends(get_current_user)
):
	"""
	This endpoint will first create a new "interview" record.  Then it will make a call to OpenAI to write a list of interview questions.
	Once it has the list, it will create a DB record for each question.  It will then cycle through each question text and create a voice audio file.

	:param interview_data: contains {job_id: int, company_id: int}
	:param db:
	:param user_id:
	:return: [
				{
					question_id: int,
					question_order: int,
					category: str
					question: str
					answer_note: str
				}
			]
	"""
	try:
		logger.debug(f"Starting /v1/interview/question endpoint", job_id=interview_data.job_id, company_id=interview_data.company_id)

		# Create the interview record entry
		query = text("INSERT INTO interview (job_id, user_id, company_id) VALUES (:job_id, :user_id, :company_id) RETURNING interview_id")
		result = db.execute(query, {"job_id": interview_data.job_id, "user_id": user_id, "company_id": interview_data.company_id})
		if not result:
			logger.error(f"Failed to create interview record for job", job_id=interview_data.job_id)
			raise HTTPException(status_code=500, detail="Failed to create interview record")

		interview_id = result.fetchone()[0]
		logger.debug(f"Successfully created interview record", interview_id=interview_id)

		# Capture user_id for the thread
		thread_user_id = user_id

		# Configure for background task
		import threading
		from ..core.database import SessionLocal
		from ..models.models import Process

		new_process = Process(
			endpoint_called="/v1/interview/question",
			running_method="interview_questions",
			running_class="AiAgent",
			user_id=thread_user_id
		)
		db.add(new_process)
		db.commit()
		db.refresh(new_process)

		process_id = new_process.process_id
		logger.debug(f"Created process record", process_id=process_id)

		def get_questions():
			# Create a new database session for the thread
			# DO NOT use the request-scoped 'db' session
			thread_db = SessionLocal()
			try:
				logger.info(f"Calling AI interview questions as background process", interview_id=interview_id, process_id=process_id)
				thread_ai_agent = AiAgent(db, thread_user_id)
				thread_ai_agent.interview_questions(interview_data.job_id, interview_data.company_id, thread_user_id, interview_id, process_id)
			finally:
				logger.info(f"Closing interview questions background thread", interview_id=interview_id, process_id=process_id)
				thread_db.close()

		# Run in separate thread to avoid blocking the event loop
		thread = threading.Thread(target=get_questions, daemon=True)
		thread.start()

		logger.info(f"/v1/interview/question process completed", interview_id=interview_id, process_id=process_id)

		return {"process_id": process_id, "interview_id": interview_id}

	except Exception as e:
		logger.error(f"Failed to create question audio files", interview_id=interview_id)
		raise HTTPException(status_code=500, detail=f"Error creating interview questions: {str(e)}")

@router.get("/interview/question/list/{interview_id}", status_code=status.HTTP_200_OK)
async def question_list(
	interview_id: int,
	db: Session = Depends(get_db),
	user_id: int = Depends(get_current_user)
):
	"""
	This endpoint is the follow-up to starting /v1/interview/question, which runs as a background process.  This will query the DB
	and return an array of questions

	:param interview_id:
	:param db:
	:param user_id:
	:return: [ { question_id, question_order, category, question } ]
	"""
	query = text("""
         SELECT q.question_id, q.question_order, q.category, q.question 
         FROM interview i JOIN question q ON (i.interview_id=q.interview_id) 
         WHERE i.interview_id = :interview_id AND i.user_id = :user_id ORDER BY q.question_order
     """)
	result = db.execute(query, {"interview_id": interview_id, "user_id": user_id}).fetchall()
	if not result:
		logger.error(f"Failed to retrieve interview questions", interview_id=interview_id)
		raise HTTPException(status_code=404, detail="Interview question not found")

	ret_data = []
	for row in result:
		quest = dict()
		quest["question_id"] = row.question_id
		quest["question_order"] = row.question_order
		quest["category"] = row.category
		quest["question"] = row.question
		ret_data.append(quest)

	return ret_data


@router.post("/interview/answer", status_code=status.HTTP_200_OK)
async def interview_answer(
	req_data: InterviewAnswerRequest,
	db: Session = Depends(get_db),
	user_id: int = Depends(get_current_user)
):
	"""
	This endpoint will submit a candidates answer to a given question and make an AI call to evaluate it

	:param req_data: {interview_id: int, question_id: int, answer: str}
	:param db: database handle
	:param user_id: current user ID from JWT
	:return:
	"""
	try:
		logger.debug(f"Starting /v1/interview/answer", interview_id=req_data.interview_id, question_id=req_data.question_id, answer=req_data.answer)
		logger.debug(f"ANSWER ******************", answer=req_data.answer)

		ai_agent = AiAgent(db, user_id)
		ai_result = ai_agent.interview_answer(req_data.interview_id, req_data.question_id, req_data.answer)
		if not ai_result:
			logger.error(f"Error - no value returned from AI call", ai_result=ai_result)
			raise HTTPException(status_code=500, detail="Error - no value returned from AI call")

		query = text("SELECT parent_question_id, question_order, category FROM question WHERE question_id = :question_id")
		result = db.execute(query, {"question_id": req_data.question_id}).fetchone()
		if not result:
			logger.error(f"Failed to retrieve question data", question_id=req_data.question_id)
			raise HTTPException(status_code=404, detail="Question record not found")

		# check if follow-up question was defined
		order = result.question_order
		sound_file = None
		question_id = 0

		if ai_result['followup_question'] and result.parent_question_id:
			logger.error(f"Ignoring AI follow-up question to a follow-up question", parent_question_id=result.parent_question_id)
			ai_result['followup_question'] = None

		if ai_result['followup_question'] and not result.parent_question_id:
			logger.debug(f"Follow-up question is defined", question_id=req_data.question_id, question=ai_result['followup_question'])

			# Need to insert a new question record
			order = result.question_order + 1

			query = text("""
				INSERT INTO question (interview_id, parent_question_id, question_order, category, question, answer_note)
				VALUES (:interview_id, :parent_question_id, :order, :category, :question, :answer_note) RETURNING question_id
			""")
			new_result = db.execute(query, {
				"interview_id": req_data.interview_id,
				"parent_question_id": req_data.question_id,
				"order": order,
				"category": result.category,
				"question": ai_result['followup_question'],
				"answer_note": ai_result['answer_note'] or "",
			})
			if not new_result:
				logger.error(f"Failed to insert new interview question", interview_id=req_data.interview_id)
				raise HTTPException(status_code=500, detail="Failed inserting new question record")

			question_id = new_result.fetchone()[0]
			logger.debug(f"Completed inserting new question", question_id=question_id, order=order)

			sound_file = get_tts_audio(question_id, req_data.interview_id, ai_result['followup_question'], False)
			if sound_file == "Error":
				logger.error(f"Failed to creating audio for question", interview_id=req_data.interview_id)
				raise HTTPException(status_code=500, detail="Failed inserting new question record")

		response_audio_file = None
		if ai_result['response_statement']:
			logger.debug(f"Creating response statement audio file", question_id=req_data.question_id, statement=ai_result['response_statement'])
			response_audio_file = get_tts_audio(req_data.question_id, req_data.interview_id, ai_result['response_statement'], True)

		logger.debug(f"Updating question record with answer metrics", question_id=req_data.question_id)
		# Now update the question record with the answer fields
		answer_score = ((int(ai_result['completeness']) + int(ai_result['correctness']) + int(ai_result['insight']) + int(ai_result['clarity']) + int(ai_result['understanding']) + int(ai_result['bonus'])) / 600) * 100
		up_query = text("""
	        UPDATE question
			    SET answer       = :answer,
			        completeness = :completeness,
			        correctness  = :correctness,
			        insight      = :insight,
		            clarity      = :clarity,
				    understanding = :understanding,
				    answer_score = :answer_score,
				    bonus        = :bonus,
				    feedback_note = :feedback_note,
				    response_statement = :response_statement,
				    response_audio_file = :response_audio_file 
		        WHERE question_id = :question_id
	        """)
		up_result = db.execute(up_query, {
			"answer": req_data.answer,
			"completeness": int(ai_result['completeness']),
			"correctness": int(ai_result['correctness']),
			"insight": int(ai_result['insight']),
			"clarity": int(ai_result['clarity']),
			"understanding": int(ai_result['understanding']),
			"answer_score": answer_score,
			"bonus": int(ai_result['bonus']),
			"feedback_note": ai_result['feedback_note'],
			"question_id": req_data.question_id,
			"response_statement": ai_result['response_statement'] or "",
			"response_audio_file": response_audio_file or ""
		})
		if not up_result:
			logger.error(f"Failed to update interview question", interview_id=req_data.interview_id, question_id=req_data.question_id)
			raise HTTPException(status_code=500, detail="Failed to update question record with answer fields")

		db.commit()
		ret = InterviewAnswerResponse(
			parent_question_id = req_data.question_id,
			question_id = question_id or None,
			question_order = order or None,
			question = ai_result.get('followup_question') or "",
			sound_file = sound_file or "",
			response_statement = ai_result.get('response_statement') or "",
			response_audio_file = response_audio_file or ""
		)
		logger.debug(f"Completed /v1/interview/answer", response=ret)
		return ret

	except Exception as e:
		logger.error(f"Failed while processing question answer", interview_id=req_data.interview_id, error=str(e))
		raise


@router.post("/interview/transcribe", response_model=TranscribeResponse)
async def interview_transcribe(
	upload_file: Optional[UploadFile] = File(None),
	db: Session = Depends(get_db),
	question_id: int = Form(...),
	user_id: int = Depends(get_current_user)
):
	"""
	This endpoint will take the attached audio file and transcribe it into text and return the translation
	:param upload_file: audio recording file
	:param db: database handle
	:param question_id: The question to which the answer audio file belongs
	:param user_id: Current user ID from JWT
	:return: {
				"text": ""
			}
	"""
	try:
		logger.debug(f"Starting /v1/interview/transcribe", filename=upload_file.filename, question_id=question_id, mimetype=upload_file.content_type)

		if not upload_file:
			logger.debug(f"No upload file included in request", question_id=question_id)
			raise HTTPException(status_code=400, detail="No file uploaded")

		# Load API key from database for this user
		settings.load_llm_settings_from_db(db, user_id)

		if not settings.openai_api_key:
			logger.error(f"OpenAI API key not configured", user_id=user_id)
			raise HTTPException(status_code=500, detail="OpenAI API key not configured")

		# Read file content and get filename for OpenAI
		file_content = await upload_file.read()
		filename = upload_file.filename or "recording.webm"

		# Determine content type
		content_type = upload_file.content_type or "audio/webm"
		mimetype = "webm"

		logger.debug(f"Transcribing audio file", filename=filename, content_type=content_type, size=len(file_content))

		client = OpenAI(api_key=settings.openai_api_key)
		transcription = client.audio.transcriptions.create(
			model=settings.stt_llm,
			file=(filename, file_content, content_type),
			response_format="json"
		)

		# get the interview ID from question record
		query = text("SELECT interview_id FROM question WHERE question_id = :question_id")
		result = db.execute(query, {"question_id": question_id}).fetchone()
		if not result:
			logger.error(f"Failed to retrieve interview ID", question_id=question_id)

		logger.debug(f"Saving answer audio file")
		audio_file = f"a{question_id}.{mimetype}"
		fullpath = Path(settings.interview_dir) / str(result.interview_id) / audio_file

		# Write file_content since we already read the file
		with fullpath.open("wb") as buffer:
			buffer.write(file_content)

		logger.debug(f"Finished /v1/interview/transcribe", file_path=fullpath, transcription=transcription.text)
		return {"text": transcription.text}

	except Exception as e:
		logger.error(f"Transcription failed", error=str(e), question_id=question_id)
		# Return empty text instead of failing - allows interview to continue
		return {"text": ""}

@router.post("/interview/question/audio", status_code=status.HTTP_200_OK)
async def question_audio(
	request: AudioRequest,
	db: Session = Depends(get_db),
	user_id: int = Depends(get_current_user)
):
	"""
	This endpoint will retrieve and return the correct audio file question
	:param request: {interview_id: int, question_id: int, statement: bool}
	:param db: database handle
	:param user_id: current user ID from JWT

	:return: {path: str, media_type: str, filename: str}
	"""
	file_name = f"{request.question_id}.mp3"
	if request.statement:
		file_name = f"{request.question_id}-s.mp3"
	file_path = os.path.join(settings.interview_dir, str(request.interview_id), file_name)
	# Create standardized download file
	tmp_path, download_name, mime_type = create_standardized_download_file(
		source_file_path=file_path,
		file_type='audio',
		db=db,
		user_id=user_id
	)

	logger.info(f"Serving question audio file", download_name=download_name)

	return FileResponse(
		path=tmp_path,
		media_type=mime_type,
		filename=download_name
	)


@router.get("/interview/list", status_code=status.HTTP_200_OK)
async def interview_list(
	db: Session = Depends(get_db),
	user_id: int = Depends(get_current_user)
):
	"""
	This endpoint will query the DB and return a list of interviews for the given user

	:param db: database handle
	:param user_id: current user
	:return: [{ interview_id: int, interview_score: int, company_name: str, job_title: str, interview_created: str }]
	"""
	try:
		query = text("""
			SELECT i.interview_score, i.interview_created, i.interview_id, c.company_name, j.job_title
			FROM interview i JOIN company c ON (i.company_id=c.company_id) JOIN job j ON (i.job_id=j.job_id)
			WHERE i.user_id = :user_id ORDER BY c.company_name, i.interview_created DESC, i.interview_id DESC
		""")
		result = db.execute(query, {"user_id": user_id}).fetchall()
		if not result:
			return []

		# Convert SQLAlchemy rows to list of dictionaries
		interviews = []
		for row in result:
			interviews.append({
				"interview_id": row.interview_id,
				"interview_score": row.interview_score,
				"interview_created": str(row.interview_created),
				"company_name": row.company_name,
				"job_title": row.job_title
			})
		return interviews
	except Exception as e:
		logger.error(f"An Error occurred while retrieving interview list", user_id=user_id, error=str(e))
		raise


@router.get("/interview/{interview_id}", status_code=status.HTTP_200_OK)
async def interview_review(
	interview_id: int,
	db: Session = Depends(get_db),
	user_id: int = Depends(get_current_user)
):
	"""
	This endpoint will review the completed interview and make a determination, as well as provide feedback
	:param interview_id: primary key for interview record
	:param db: database handle
	:param user_id: current JWT user
	:return:
	"""

	try:
		logger.debug(f"Starting /v1/interview/{interview_id} endpoint", interview_id=interview_id)

		# we first need to create the interview summary report
		query = text("""
			SELECT i.interview_score, i.summary_report, i.interview_feedback, i.hiring_decision, i.interview_created,
			    c.company_name, j.job_title,
		        q.question_id, q.parent_question_id, q.category, q.question, q.answer, q.answer_note, q.completeness,
				q.correctness, q.insight, q.clarity, q.understanding, q.answer_score, q.bonus, q.feedback_note
			FROM interview i
			    JOIN question q ON (i.interview_id=q.interview_id)
			    JOIN company c ON (i.company_id=c.company_id)
			    JOIN job j ON (i.job_id=j.job_id)
			WHERE i.interview_id = :interview_id AND i.user_id = :user_id ORDER BY q.question_order
		""")
		result = db.execute(query, {"interview_id": interview_id, "user_id": user_id}).fetchall()
		if not result:
			logger.error(f"Failed to retrieve interview questions", interview_id=interview_id)
			raise HTTPException(status_code=404, detail="Interview not found")

		interview_score = result[0].interview_score
		summary_report = result[0].summary_report
		interview_feedback = result[0].interview_feedback
		hiring_decision = result[0].hiring_decision
		interview_created = result[0].interview_created
		company_name = result[0].company_name
		job_title = result[0].job_title

		category = None

		if not summary_report:
			logger.debug(f"No summary report exists for this interview", interview_id=interview_id)
			tmp_report = ""

			for row in result:
				entry = ""
				if not category or category != row.category:
					entry += f'Category: {row.category}\n\n'
					category = row.category

				if row.parent_question_id:
					entry += 'Follow-up '

				entry += f'Question: {row.question}\nAnswer: {row.answer}\nAnswer Guidance: {row.answer_note}\nAnswer Feedback: {row.feedback_note}\n'
				entry += f'Completeness: {row.completeness}\tCorrectness: {row.correctness}\tInsight: {row.insight}\tClarity: {row.clarity}\t'
				entry += f'Understanding: {row.understanding}\tBonus: {row.bonus}\nAnswer Score: {row.answer_score}\n\n'

				tmp_report += entry

			# Now make the AI call to review the data
			logger.debug(f"Making AI call review_interview", interview_id=interview_id)
			ai_agent = AiAgent(db, user_id)
			ai_result = ai_agent.review_interview(interview_id, tmp_report)

			logger.debug(f"AI call review_interview completed", interview_id=interview_id)
			interview_score = ai_result['interview_score']
			summary_report = tmp_report
			interview_feedback = ai_result['interview_feedback']
			hiring_decision = ai_result['hiring_decision']

			# update the interview record with outcome
			up_query = text("""
				UPDATE interview
				    SET interview_score = :interview_score, interview_feedback = :interview_feedback, hiring_decision = :hiring_decision, summary_report = :summary_report 
			    WHERE interview_id = :interview_id AND user_id = :user_id
				    """)
			up_result = db.execute(up_query, {
				"interview_id": interview_id,
				"user_id": user_id,
				"interview_score": interview_score,
				"interview_feedback": interview_feedback,
				"hiring_decision": hiring_decision,
				"summary_report": summary_report
			})
			if not up_result:
				logger.error(f"Failed to update interview record", interview_id=interview_id)
				raise HTTPException(status_code=500, detail="Failed to update interview record")

			db.commit()

		logger.info(f"Interview record updated - getting question list", interview_id=interview_id)
		query = text("""
			SELECT q.question_id, q.parent_question_id, q.category, q.question, q.answer, q.answer_note, q.completeness, q.correctness,
                q.insight, q.clarity, q.understanding, q.answer_score, q.bonus, q.feedback_note
			FROM interview i JOIN question q ON (i.interview_id = q.interview_id)
			WHERE i.interview_id = :interview_id AND i.user_id = :user_id ORDER BY q.question_order
		""")
		q_result = db.execute(query, {"interview_id": interview_id, "user_id": user_id}).fetchall()
		if not q_result:
			logger.error(f"Failed to retrieve interview questions", interview_id=interview_id)
			raise HTTPException(status_code=404, detail="Interview questions not found")

		# Convert SQLAlchemy rows to list of dictionaries
		questions = []
		for row in q_result:
			questions.append({
				"question_id": row.question_id,
				"parent_question_id": row.parent_question_id,
				"category": row.category,
				"question": row.question,
				"answer": row.answer,
				"answer_note": row.answer_note,
				"completeness": row.completeness,
				"correctness": row.correctness,
				"insight": row.insight,
				"clarity": row.clarity,
				"understanding": row.understanding,
				"answer_score": row.answer_score,
				"bonus": row.bonus,
				"feedback_note": row.feedback_note
			})


		logger.info(f"Completed interview review", interview_id=interview_id)
		return InterviewReviewResponse(
			interview_score = interview_score,
			interview_feedback = interview_feedback,
			hiring_decision = hiring_decision,
			interview_created = str(interview_created) if interview_created else None,
			company_name = company_name,
			job_title = job_title,
			questions = questions
		)

	except Exception as e:
		logger.error(f"An Error occurred while reviewing interview", interview_id=interview_id, error=str(e))
		raise

