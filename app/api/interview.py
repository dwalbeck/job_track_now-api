from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional
import os
from openai import OpenAI
from ..utils.file_helpers import create_standardized_download_file
from ..core.database import get_db, SessionLocal
from ..schemas.interview import InterviewQuestionRequest, InterviewAnswerRequest, TranscribeResponse, AudioRequest, InterviewAnswerResponse, InterviewReviewResponse, InterviewQuestionResponse, InterviewListResponse
from ..middleware.auth_middleware import get_current_user
from ..utils.ai_agent import AiAgent
from ..utils.logger import logger
from ..core.config import settings

router = APIRouter()


def get_question_audio(question_id: int, interview_id: int, text_str: str, statement: bool) -> str:
	"""
	This function will query all the question for an interview and make a TTS call for each, then save the sound file
	:param interview_id: primary key for interview record
	:param question_id: the ID for the question that is targeted
	:param text_str: the question text
	:param statement: boolean marked true if a statement and false if a question
	:return: full path to audio file
	"""
	db = SessionLocal()
	#os.environ["OPENAI_API_KEY"] = settings.openai_api_key
	basepath = f'{settings.interview_dir}/{interview_id}'
	if not os.path.exists(basepath):
		os.makedirs(basepath)

	logger.debug(f"Starting process to create audio file", interview_id=interview_id, statement=statement)

	try:
		filename = str(question_id) + '.mp3'
		if statement:
			filename = str(question_id) + '-s.mp3'
		audio_file = basepath + '/' + filename

		# execute the OpenAI Text to Speech API call
		logger.debug(f"Making TTS call to OpenAI for audio file", audio_file=audio_file)
		client = OpenAI(api_key=settings.openai_api_key)

		response = client.audio.speech.create(
			model="gpt-4o-mini-tts",
			voice="alloy",
			input=text_str
		)
		response.write_to_file(audio_file)

		if not os.path.exists(audio_file):
			logger.debug(f"Error - question audio file was not created", audio_file=audio_file)

		logger.debug(f"finished generating sound file for question", question_id=question_id, audio_file=audio_file)
		return audio_file

	except Exception as e:
		logger.error(f"An Error occurred while creating question audio files", interview_id=interview_id, error=str(e))
		return "Error"
	finally:
		db.close()

def get_all_question_audio(interview_id: int, user_id: int) -> bool:
	"""
	This function will query all the question for an interview and make a TTS call for each, then save the sound file
	:param interview_id: primary key for interview record
	:param user_id: current JWT user
	:return:
	"""
	db = SessionLocal()
	#os.environ["OPENAI_API_KEY"] = settings.openai_api_key
	basepath = f'{settings.interview_dir}/{interview_id}'
	if not os.path.exists(basepath):
		os.makedirs(basepath)

	logger.debug(f"Starting process to create question audio files", interview_id=interview_id)

	try:
		query = text("""
			SELECT q.question, q.question_id 
			FROM interview i JOIN question q ON (i.interview_id=q.interview_id) 
			WHERE i.interview_id = :interview_id AND i.user_id = :user_id ORDER BY q.question_order 
		""")
		result = db.execute(query, {"interview_id": interview_id, "user_id": user_id}).fetchall()
		if not result:
			logger.error(f"Failed to retrieve interview questions", interview_id=interview_id)

		for question in result:
			logger.debug(f"running question record", question_id=question.question_id)
			filename = str(question.question_id) + '.mp3'
			question_audio_file = basepath + '/' + filename

			# execute the OpenAI Text to Speech API call
			logger.debug(f"Making TTS call to OpenAI for audio file", audio_file=question_audio_file)
			client = OpenAI(api_key=settings.openai_api_key)

			response = client.audio.speech.create(
				model="gpt-4o-mini-tts",
				voice="alloy",
				input=question.question
			)
			response.write_to_file(question_audio_file)

			if not os.path.exists(question_audio_file):
				logger.debug(f"Error - question audio file was not created", audio_file=question_audio_file)

			logger.debug(f"finished generating sound file for question", question_id=question.question_id)

		logger.debug(f"Completed creating audio files for each question", interview_id=interview_id)
		return True
	except Exception as e:
		logger.error(f"An Error occurred while creating question audio files", interview_id=interview_id, error=str(e))
		return False
	finally:
		db.close()

@router.post("/interview/question", response_model=InterviewQuestionResponse)
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

		interview_id = result.fetchone()[0]
		logger.debug(f"Successfully created interview record", interview_id=interview_id)

		ai_agent = AiAgent(db, user_id)
		response_text = ai_agent.interview_questions(interview_data.job_id, interview_data.company_id, user_id)
		if not response_text:
			logger.error(f"Error - no value returned from AI call", job_id=interview_data.job_id)
			raise HTTPException(status_code=500, detail="Error - no value returned from AI call")

		logger.debug(f"Completed AI call for question creation", first_question=response_text[0]['question'])

		order = 1
		ret_list = []
		logger.debug(f"Process each question in return list", response=response_text[0])
		for question in response_text:
			logger.debug(f"adding question to DB", order=order)

			query = text("""
				INSERT INTO question (interview_id, question_order, question, answer_note, category)
				VALUES (:interview_id, :order, :question, :answer_note, :category) RETURNING question_id
			""")
			result = db.execute(query, {
				"interview_id": interview_id,
				"order": order,
				"question": question['question'],
				"answer_note": question['answer_note'],
				"category": question['category']
			})
			if not result:
				logger.error(f"Failed to insert interview question", job_id=interview_data.job_id, query=query)

			question['question_order'] = order
			question['question_id'] = result.fetchone()[0]
			del question['answer_note']
			ret_list.append(question)
			order += 2
			logger.debug(f"successfully added question", order=order)

		db.commit()
		logger.debug(f"Starting process to create question audio files", interview_id=interview_id)
		audio = get_all_question_audio(interview_id, user_id)

		if not audio:
			logger.error(f"Failed to create question audio files", interview_id=interview_id)
			raise HTTPException(status_code=500, detail="Failed to create question audio files")

		return InterviewQuestionResponse(
			interview_id = interview_id,
			questions = ret_list
		)

	except Exception as e:
		logger.error(f"Failed to create question audio files", interview_id=interview_id)
		raise HTTPException(status_code=500, detail=f"Error creating interview questions: {str(e)}")

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
		# First let's get question details
		query = text("""
	         SELECT q.parent_question_id, q.question_order, q.question, q.answer_note, q.category, p.question AS parent_question, p.answer_note AS parent_answer_note, p.answer AS parent_answer   
	         FROM question q LEFT JOIN question p ON (q.parent_question_id=p.question_id AND q.parent_question_id IS NOT NULL) 
	         WHERE q.question_id = :question_id
	     """)
		result = db.execute(query, {"question_id": req_data.question_id}).first()
		if not result:
			logger.error(f"Failed to retrieve interview question", interview_id=req_data.interview_id)
			raise HTTPException(status_code=404, detail="Interview question not found")

		ai_agent = AiAgent(db, user_id)
		ai_result = ai_agent.interview_answer(req_data.interview_id, result.question, req_data.answer, result.answer_note, result.parent_question, result.parent_answer, result.parent_answer_note)
		if not ai_result:
			logger.error(f"Error - no value returned from AI call", interview_id=req_data.interview_id)
			raise HTTPException(status_code=500, detail="Error - no value returned from AI call")

		# check if follow-up question was defined
		order = None
		sound_file = None
		question_id = None

		if ai_result['followup_question']:
			# Need to insert a new question record
			order = result.question_order + 1

			sound_file = get_question_audio(req_data.question_id, req_data.interview_id, ai_result['followup_question'], False)
			if sound_file == "Error":
				logger.error(f"Failed to creating audio for question", interview_id=req_data.interview_id)
				raise HTTPException(status_code=500, detail="Failed inserting new question record")

			query = text("""
				INSERT INTO question (interview_id, parent_question_id, question_order, category, question, answer_note, sound_file) 
				VALUES (:interview_id, :parent_question_id, :order, :category, :question, :answer_note) RETURNING question_id
			""")
			new_result = db.execute(query, {
				"interview_id": req_data.interview_id,
				"parent_question_id": req_data.question_id,
				"order": order,
				"category": result.category,
				"question": ai_result['followup_question'],
				"answer_note": ai_result['followup_answer_note'],
				"sound_file": sound_file
			})
			if not new_result:
				logger.error(f"Failed to insert new interview question", interview_id=req_data.interview_id)
				raise HTTPException(status_code=500, detail="Failed inserting new question record")

			question_id = new_result.fetchone()[0]

		response_audio_file = None
		if ai_result['response_statement']:
			response_audio_file = get_question_audio(question_id, req_data.interview_id, ai_result['response_statement'], True)


		# Now update the question record with the answer fields
		answer_score = ((ai_result['completeness'] + ai_result['correctness'] + ai_result['insight'] + ai_result['clarity'] + ai_result['understanding'] + ai_result['bonus']) / 600) * 100
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
			"completeness": ai_result['completeness'],
			"correctness": ai_result['correctness'],
			"insight": ai_result['insight'],
			"clarity": ai_result['clarity'],
			"understanding": ai_result['understanding'],
			"answer_score": answer_score,
			"bonus": ai_result['bonus'],
			"feedback_note": ai_result['feedback_note'],
			"question_id": req_data.question_id,
			"response_statement": ai_result['response_statement'],
			"response_audio_file": response_audio_file
		})
		if not up_result:
			logger.error(f"Failed to update interview question", interview_id=req_data.interview_id, question_id=req_data.question_id)
			raise HTTPException(status_code=500, detail="Failed to update question record with answer fields")

		db.commit()
		return InterviewAnswerResponse(
			question_id = question_id or req_data.question_id,
			question_order = order,
			question = ai_result.get('followup_question'),
			sound_file = sound_file,
			response_audio_file = response_audio_file
		)

	except Exception as e:
		logger.error(f"Failed while processing question answer", interview_id=req_data.interview_id)
		raise


@router.post("/interview/transcribe", response_model=TranscribeResponse)
async def interview_transcribe(
	upload_file: Optional[UploadFile] = File(None),
	db: Session = Depends(get_db),
	question_id: int = Form(...)
):
	"""
	This endpoint will take the attached audio file and transcribe it into text and return the translation
	:param upload_file: audio recording file
	:param db: database handle
	:param question_id: The question to which the answer audio file belongs
	:return: {
				"text": ""
			}
	"""
	if not upload_file:
		raise HTTPException(status_code=400, detail="No file uploaded")

	client = OpenAI(api_key=settings.openai_api_key)
	transcription = client.audio.transcriptions.create(
		model="gpt-4o-transcribe",
		file=upload_file.file,
		response_format="json"
	)

	# update the transcript for the question answer
	#query = text("UPDATE question SET answer=answer+:transcription WHERE question_id=:question_id")
	#result = db.execute(query, {"transcription": " " + transcription.text, "question_id": question_id})
	#if not result:
	#	logger.error(f"Failed to update interview question", question_id=question_id)

	return transcription

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
		# we first need to create the interview summary report
		query = text("""
			SELECT i.interview_score, i.summary_report, i.interview_feedback, i.hiring_decision, 
		        q.question_id, q.parent_question_id, q.category, q.question, q.answer, q.answer_note, q.completeness, 
				q.correctness, q.insight, q.clarity, q.understanding, q.answer_score, q.bonus, q.feedback_note 
			FROM interview i JOIN question q ON (i.interview_id=q.interview_id) 
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

		q_data = []
		category = None

		if not summary_report:
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
				# alter the data set entry
				del row.interview_score
				del row.summary_report
				del row.interview_feedback
				del row.hiring_decision
				q_data.append(row)

			# Now make the AI call to review the data
			ai_agent = AiAgent(db, user_id)
			ai_result = ai_agent.review_interview(interview_id, tmp_report)

			interview_score = ai_result.interview_score
			summary_report = tmp_report
			interview_feedback = ai_result.interview_feedback
			hiring_decision = ai_result.hiring_decision

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

		else:
			# clean-up DB query data set for sending in response
			for row in result:
				del row.interview_score
				del row.summary_report
				del row.interview_feedback
				del row.hiring_decision
				q_data.append(row)

		logger.info(f"Completed interview review", interview_id=interview_id)
		return InterviewReviewResponse(
			interview_score = interview_score,
			interview_feedback = interview_feedback,
			hiring_decision = hiring_decision,
			questions = q_data
		)

	except Exception as e:
		logger.error(f"An Error occurred while reviewing interview", interview_id=interview_id, error=str(e))
		raise


@router.get("/interview/list", response_model=InterviewListResponse)
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
			WHERE i.user_id = :user_id ORDER BY c.company_name, i.interview_id
		""")
		result = db.execute(query, {"user_id": user_id}).fetchall()
		if not result:
			logger.error(f"Failed to retrieve interview list", user_id=user_id)
			raise HTTPException(status_code=404, detail="Failed to query interview list")

		return result
	except Exception as e:
		logger.error(f"An Error occurred while retrieving interview list", user_id=user_id, error=str(e))
		raise

