import os
import re
import shutil
import difflib
from pathlib import Path
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime

from ..core.database import get_db
from ..core.config import settings
from ..models.models import Resume, Job, FileFormat, ResumeDetail
from ..schemas.resume import (
	Resume as ResumeSchema,
	ResumeUpdate,
	ResumeDetailCreate,
	ResumeDetail as ResumeDetailSchema,
	ResumeBaseline,
	ResumeBaselineList,
	ResumeJob,
	ResumeCloneRequest,
	ResumeExtractRequest,
	ResumeExtractResponse,
	ResumeRewriteRequest,
	ResumeRewriteResponse,
	ResumeFullRequest,
	ResumeFullResponse
)
from ..utils.ai_agent import AiAgent
from ..utils.conversion import Conversion
from ..utils.job_helpers import update_job_activity
from ..utils.logger import logger
from ..middleware.auth_middleware import get_current_user


router = APIRouter()


def _convert_to_markdown(file_name: str, file_format: str) -> str:
	"""
	Convert a resume file to markdown based on its format.

	Args:
		file_name: Name of the file to convert
		file_format: Format of the file (pdf, docx, odt, md)

	Returns:
		Markdown content as string

	Raises:
		Exception: If conversion fails
	"""
	if file_format == 'md':
		# Read markdown file directly
		file_path = Path(settings.resume_dir) / file_name
		with open(file_path, 'r', encoding='utf-8') as f:
			return f.read()
	elif file_format == 'pdf':
		return Conversion.pdfToMd(file_name)
	elif file_format == 'docx':
		return Conversion.docxToMd(file_name)
	elif file_format == 'odt':
		return Conversion.odtToMd(file_name)
	else:
		raise ValueError(f"Unsupported file format: {file_format}")


def clean_filename_part(text: str) -> str:
	"""
	Clean text for use in filename: lowercase, replace spaces with underscores.
	"""
	# Remove special characters except spaces and hyphens
	cleaned = re.sub(r'[^\w\s-]', '', text).strip()
	# Replace spaces and hyphens with underscores
	cleaned = re.sub(r'[-\s]+', '_', cleaned)
	# Convert to lowercase
	return cleaned.lower()


def generate_text_diff(original_text: str, rewritten_text: str) -> List[str]:
	"""
	Generate a unified diff between original and rewritten text.

	Args:
		original_text: Original markdown text
		rewritten_text: Rewritten markdown text

	Returns:
		List of diff lines (without file headers)
	"""
	# Split texts into lines
	original_lines = original_text.splitlines(keepends=True)
	rewritten_lines = rewritten_text.splitlines(keepends=True)

	# Generate unified diff
	diff = difflib.unified_diff(
		original_lines,
		rewritten_lines,
		fromfile='baseline',
		tofile='optimized',
		lineterm=''
	)

	# Skip the first two lines (file headers) and collect the rest
	diff_lines = list(diff)
	if len(diff_lines) > 2:
		return diff_lines[2:]  # Skip --- baseline and +++ optimized headers
	return []


def calculate_keyword_score(keywords: list, text: str) -> int:
	"""
	Calculate the percentage of keywords found in text using regex matching.

	Args:
		keywords: List of keywords to search for
		text: Text to search in

	Returns:
		Percentage score (0-100)
	"""
	if not keywords or not text:
		return 0

	matched_count = 0
	for keyword in keywords:
		# Case-insensitive regex search for whole keyword
		pattern = re.compile(r'\b' + re.escape(keyword) + r'\b', re.IGNORECASE)
		if pattern.search(text):
			matched_count += 1

	total_count = len(keywords)
	if total_count > 0:
		return int((matched_count / total_count) * 100)

	return 0


def get_file_extension_from_filename(filename: str) -> Optional[str]:
	"""
	Extract the file extension from a filename.
	Returns the extension without the dot (e.g., 'pdf', 'docx').
	"""
	if not filename:
		return None
	parts = filename.rsplit('.', 1)
	if len(parts) > 1:
		ext = parts[1].lower()
		# Map common extensions to FileFormat enum values
		return ext
	return None


def validate_file_format(extension: str) -> str:
	"""
	Validate that the file extension is a valid FileFormat enum value.
	"""
	valid_formats = [e.value for e in FileFormat]
	if extension not in valid_formats:
		raise HTTPException(
			status_code=400,
			detail=f"Invalid file format '{extension}'. Allowed formats: {', '.join(valid_formats)}"
		)
	return extension

def make_unique_resume_title(base_title: str, db: Session, user_id: int) -> str:
	"""
	Ensure resume title is unique by appending an incrementing number if needed.

	Args:
		base_title: The desired resume title
		db: Database session
		user_id: The user's ID

	Returns:
		Unique resume title that doesn't exist in the database for this user
	"""
	if not base_title:
		return base_title

	# Check if base title already exists for this user
	existing = db.query(Resume).filter(
		Resume.resume_title == base_title,
		Resume.user_id == user_id
	).first()

	if not existing:
		return base_title

	# Try incrementing numbers until we find a unique title
	counter = 1
	while True:
		new_title = f"{base_title} ({counter})"
		existing = db.query(Resume).filter(
			Resume.resume_title == new_title,
			Resume.user_id == user_id
		).first()

		if not existing:
			return new_title

		counter += 1

		# Safety check to prevent infinite loop
		if counter > 1000:
			raise ValueError(f"Could not generate unique resume title after {counter} attempts")


def make_unique_filename(base_filename: str, db: Session, user_id: int) -> str:
	"""
	Ensure filename is unique by adding timestamp or incrementing number if needed.

	Args:
		base_filename: The desired filename (e.g., "resume.pdf")
		db: Database session
		user_id: The user's ID

	Returns:
		Unique filename that doesn't exist in the database for this user
	"""
	# Check if base filename already exists for this user
	existing = db.query(Resume).filter(
		Resume.file_name == base_filename,
		Resume.user_id == user_id
	).first()

	if not existing:
		return base_filename

	# Split into base and extension
	parts = base_filename.rsplit('.', 1)
	if len(parts) == 2:
		base_name, extension = parts
	else:
		base_name = base_filename
		extension = ""

	# Try adding date
	from datetime import datetime
	date_stamp = datetime.utcnow().strftime('%Y_%m_%d')
	timestamped_name = f"{base_name}_{date_stamp}.{extension}" if extension else f"{base_name}_{date_stamp}"

	existing = db.query(Resume).filter(
		Resume.file_name == timestamped_name,
		Resume.user_id == user_id
	).first()
	if not existing:
		return timestamped_name

	# If date also exists (unlikely), add incrementing number
	counter = 1
	while True:
		numbered_name = f"{base_name}_{date_stamp}_{counter}.{extension}" if extension else f"{base_name}_{date_stamp}_{counter}"
		existing = db.query(Resume).filter(
			Resume.file_name == numbered_name,
			Resume.user_id == user_id
		).first()
		if not existing:
			return numbered_name
		counter += 1


@router.get("/resume/baseline")
async def get_baseline_resumes(
	db: Session = Depends(get_db),
	current_user: dict = Depends(get_current_user)
):
	"""
	Get all baseline resumes.

	Returns a list of baseline resumes ordered by is_default, resume_updated, and resume_created.
	"""
	user_id = current_user.get("user_id")
	query = text("""
		SELECT r.resume_id, r.resume_title, r.resume_updated, r.is_default,
			   rd.keyword_count, rd.focus_count
		FROM resume r
		LEFT JOIN resume_detail rd ON (r.resume_id = rd.resume_id)
		WHERE r.is_baseline = true AND r.is_active = true AND r.user_id = :user_id
		ORDER BY r.is_default DESC, r.resume_updated DESC, r.resume_created DESC
	""")

	result = db.execute(query, {"user_id": user_id})

	return [
		ResumeBaseline(
			resume_id=row.resume_id,
			resume_title=row.resume_title,
			resume_updated=row.resume_updated,
			is_default=row.is_default,
			keyword_count=row.keyword_count,
			focus_count=row.focus_count
		)
		for row in result
	]


@router.get("/resume/baseline/list")
async def get_baseline_resume_list(
	db: Session = Depends(get_db),
	current_user: dict = Depends(get_current_user)
):
	"""
	Get a simple list of baseline resumes for dropdown/selection purposes.

	Returns only resume_id, resume_title, and is_default fields,
	ordered by is_default (descending) then resume_title (ascending).
	"""
	user_id = current_user.get("user_id")
	query = text("""
		SELECT resume_id, resume_title, is_default
		FROM resume
		WHERE is_baseline = true AND is_active = true AND user_id = :user_id
		ORDER BY resume_created DESC
	""")

	result = db.execute(query, {"user_id": user_id})

	return [
		ResumeBaselineList(
			resume_id=row.resume_id,
			resume_title=row.resume_title,
			is_default=row.is_default
		)
		for row in result
	]


@router.get("/resume/job", response_model=List[ResumeJob])
async def get_job_resumes(
	db: Session = Depends(get_db),
	current_user: dict = Depends(get_current_user)
):
	"""
	Get all job-specific resumes.

	Returns a list of resumes associated with jobs, including company, job title,
	keyword/focus counts, and scores from resume_detail if available.
	"""
	user_id = current_user.get("user_id")
	query = text("""
		SELECT j.company, j.job_title, j.job_id, rd.keyword_count, rd.focus_count,
			   rd.baseline_score, rd.rewrite_score,
			   r.resume_id, r.resume_updated, r.baseline_resume_id
		FROM resume r
		JOIN job j ON (r.job_id = j.job_id)
		LEFT JOIN resume_detail rd ON (r.resume_id = rd.resume_id)
		WHERE r.is_baseline = false AND r.is_active = true AND r.user_id = :user_id
		ORDER BY r.resume_updated DESC, r.resume_created DESC
	""")

	result = db.execute(query, {"user_id": user_id})

	resumes = [
		ResumeJob(
			resume_id=row.resume_id,
			resume_updated=row.resume_updated,
			company=row.company,
			job_title=row.job_title,
			keyword_count=row.keyword_count,
			focus_count=row.focus_count,
			baseline_score=row.baseline_score,
			rewrite_score=row.rewrite_score,
			job_id=row.job_id,
			baseline_resume_id=row.baseline_resume_id
		)
		for row in result
	]

	# Debug logging
	if resumes:
		logger.debug(f"First resume baseline_resume_id: {resumes[0].baseline_resume_id}")
		logger.debug(f"First resume dict: {resumes[0].model_dump()}")

	return resumes


@router.get("/resume/{resume_id}")
async def get_resume(
	resume_id: int,
	db: Session = Depends(get_db),
	current_user: dict = Depends(get_current_user)
):
	"""
	Get a single resume by ID.

	Returns all fields from the resume table for the specified resume_id.
	"""
	user_id = current_user.get("user_id")
	resume = db.query(Resume).filter(
		Resume.resume_id == resume_id,
		Resume.user_id == user_id
	).first()

	if not resume:
		raise HTTPException(status_code=404, detail="Resume not found")

	return ResumeSchema(
		resume_id=resume.resume_id,
		resume_title=resume.resume_title,
		file_name=resume.file_name,
		is_baseline=resume.is_baseline,
		is_default=resume.is_default,
		is_active=resume.is_active,
		baseline_resume_id=resume.baseline_resume_id,
		job_id=resume.job_id,
		original_format=resume.original_format,
		resume_created=resume.resume_created,
		resume_updated=resume.resume_updated
	)


@router.get("/resume/detail/{resume_id}")
async def get_resume_detail(
	resume_id: int,
	db: Session = Depends(get_db),
	current_user: dict = Depends(get_current_user)
):
	"""
	Get resume detail by resume ID.

	Returns all fields from the resume_detail table for the specified resume_id.
	"""
	user_id = current_user.get("user_id")
	# First verify the resume belongs to the user
	resume = db.query(Resume).filter(
		Resume.resume_id == resume_id,
		Resume.user_id == user_id
	).first()

	if not resume:
		raise HTTPException(status_code=404, detail="Resume not found")

	detail = db.query(ResumeDetail).filter(ResumeDetail.resume_id == resume_id).first()

	if not detail:
		raise HTTPException(status_code=404, detail="Resume detail not found")

	return ResumeDetailSchema(
		resume_id=detail.resume_id,
		resume_markdown=detail.resume_markdown,
		resume_md_rewrite=detail.resume_md_rewrite,
		resume_html=detail.resume_html,
		resume_html_rewrite=detail.resume_html_rewrite,
		position_title=detail.position_title,
		title_line_no=detail.title_line_no,
		keyword_count=detail.keyword_count,
		resume_keyword=detail.resume_keyword,
		keyword_final=detail.keyword_final,
		focus_count=detail.focus_count,
		focus_final=detail.focus_final,
		baseline_score=detail.baseline_score,
		rewrite_score=detail.rewrite_score,
		suggestion=detail.suggestion
	)


@router.post("/resume")
async def create_or_update_resume(
	upload_file: Optional[UploadFile] = File(None),
	resume_title: str = Form(...),
	file_name: Optional[str] = Form(None),
	is_baseline: bool = Form(False),
	is_default: bool = Form(False),
	baseline_resume_id: Optional[int] = Form(None),
	job_id: Optional[int] = Form(None),
	resume_id: Optional[int] = Form(None),
	db: Session = Depends(get_db),
	current_user: dict = Depends(get_current_user)
):
	"""
	Create a new resume or update an existing one.

	Form data:
	- upload_file: The resume file (required for new resumes, optional for updates)
	- resume_title: Title of the resume
	- file_name: Optional custom filename
	- is_baseline: Whether this is a baseline resume
	- is_default: Whether this is the default resume
	- baseline_resume_id: ID of the baseline resume (if job-specific)
	- job_id: ID of the job this resume is for (mutually exclusive with is_baseline=true)
	- resume_id: ID of resume to update (omit for insert)
	"""

	user_id = current_user.get("user_id")
	is_update = bool(resume_id)
	logger.info("starting POST resume", resume_title=resume_title, user_id=user_id)

	# Determine original_format from upload_file if present
	original_format = None
	if upload_file and upload_file.filename:
		extension = get_file_extension_from_filename(upload_file.filename)
		if extension:
			original_format = validate_file_format(extension)

	# For new resumes, original_format is required
	if not is_update and not original_format:
		raise HTTPException(
			status_code=400,
			detail="upload_file with valid extension is required for new resumes"
		)

	# Handle is_baseline logic based on job_id
	if job_id:
		is_baseline = False
	else:
		is_baseline = True

	# Verify job exists and belongs to user if job_id is provided
	if job_id:
		job = db.query(Job).filter(Job.job_id == job_id, Job.user_id == user_id).first()
		if not job:
			raise HTTPException(status_code=404, detail="Job not found")

	# Calculate file_name if not provided
	calculated_file_name = file_name
	if not calculated_file_name and original_format:
		if not job_id:
			# Use resume_title for baseline resumes
			calculated_file_name = f"{clean_filename_part(resume_title)}.{original_format}"
		else:
			# Use company-job_title for job-specific resumes
			job = db.query(Job).filter(Job.job_id == job_id, Job.user_id == user_id).first()
			if job:
				company_part = clean_filename_part(job.company) if job.company else "unknown"
				job_title_part = clean_filename_part(job.job_title) if job.job_title else "unknown"
				calculated_file_name = f"{company_part}-{job_title_part}.{original_format}"

	# Ensure filename is unique (only for new resumes)
	if not is_update and calculated_file_name:
		calculated_file_name = make_unique_filename(calculated_file_name, db, user_id)

	if is_update:
		# Update existing resume - ensure it belongs to user
		resume = db.query(Resume).filter(
			Resume.resume_id == resume_id,
			Resume.user_id == user_id
		).first()
		if not resume:
			raise HTTPException(status_code=404, detail="Resume not found")

		# If setting this resume as default, first unset all other defaults for this user
		if is_default:
			db.query(Resume).filter(
				Resume.resume_id != resume_id,
				Resume.user_id == user_id
			).update(
				{"is_default": False},
				synchronize_session=False
			)

		# Update fields
		resume.resume_title = resume_title
		resume.is_baseline = is_baseline
		resume.is_default = is_default

		if baseline_resume_id is not None:
			resume.baseline_resume_id = baseline_resume_id

		if job_id is not None:
			resume.job_id = job_id

		if original_format:
			resume.original_format = original_format

		if calculated_file_name:
			resume.file_name = calculated_file_name

		# Set resume_updated timestamp
		resume.resume_updated = datetime.utcnow()

		# Save uploaded file if present
		if upload_file and upload_file.filename:
			# Create directory path
			base_path = Path(settings.resume_dir)
			base_path.mkdir(parents=True, exist_ok=True)

			file_path = base_path / calculated_file_name

			# Write file
			with open(file_path, "wb") as f:
				content = await upload_file.read()
				f.write(content)

			'''
			# Convert to markdown and create/update resume_detail
			try:
				markdown_content = _convert_to_markdown(calculated_file_name, original_format)

				# Check if resume_detail exists
				existing_detail = db.query(ResumeDetail).filter(
					ResumeDetail.resume_id == resume.resume_id
				).first()

				if existing_detail:
					# Update existing detail
					existing_detail.resume_markdown = markdown_content
				else:
					# Create new detail
					new_detail = ResumeDetail(
						resume_id=resume.resume_id,
						resume_markdown=markdown_content
					)
					db.add(new_detail)
			except Exception as e:
				logger.error(f"Error converting resume to markdown", resume_id=resume.resume_id, error=str(e))
				raise HTTPException(
					status_code=500,
					detail=f"Error processing resume: Failed to convert to Markdown: {str(e)}"
				)
			'''

	else:
		# Create new resume
		# Ensure resume_title is unique for this user
		unique_resume_title = make_unique_resume_title(resume_title, db, user_id) if resume_title else resume_title

		new_resume = Resume(
			user_id=user_id,
			resume_title=unique_resume_title,
			file_name=calculated_file_name,
			original_format=original_format,
			is_baseline=is_baseline,
			is_default=is_default,
			baseline_resume_id=baseline_resume_id,
			job_id=job_id
		)

		db.add(new_resume)
		db.flush()  # Get the resume_id before saving file

		# Save uploaded file
		if upload_file and upload_file.filename:
			# Create directory path
			base_path = Path(settings.resume_dir)
			base_path.mkdir(parents=True, exist_ok=True)

			file_path = base_path / calculated_file_name

			# Write file
			with open(file_path, "wb") as f:
				content = await upload_file.read()
				f.write(content)

			'''
			# Convert to markdown and create resume_detail
			try:
				markdown_content = _convert_to_markdown(calculated_file_name, original_format)

				# Create new detail record
				new_detail = ResumeDetail(
					resume_id=new_resume.resume_id,
					resume_markdown=markdown_content
				)
				db.add(new_detail)
			except Exception as e:
				logger.error(f"Error converting resume to markdown", resume_id=new_resume.resume_id, error=str(e))
				raise HTTPException(
					status_code=500,
					detail=f"Error processing resume: Failed to convert to Markdown: {str(e)}"
				)
			'''

		resume = new_resume

	db.commit()
	db.refresh(resume)

	# Update job activity if job_id is provided
	if job_id:
		try:
			update_job_activity(db, job_id)
		except Exception as e:
			logger.warning(f"Failed to update job activity", job_id=job_id, error=str(e))

	return {"status": "success", "resume_id": resume.resume_id}


@router.put("/resume")
async def update_resume_json(
	resume_data: ResumeUpdate,
	db: Session = Depends(get_db),
	current_user: dict = Depends(get_current_user)
):
	"""
	Update an existing resume using JSON payload.

	This endpoint accepts JSON and is used for simple resume metadata updates
	without file uploads.
	"""
	user_id = current_user.get("user_id")
	if not resume_data.resume_id:
		raise HTTPException(status_code=400, detail="resume_id is required for updates")

	logger.info("Updating resume via PUT", resume_id=resume_data.resume_id, user_id=user_id)

	# Check if resume exists and belongs to user
	resume_query = text("SELECT resume_id FROM resume WHERE resume_id = :resume_id AND user_id = :user_id")
	existing = db.execute(resume_query, {"resume_id": resume_data.resume_id, "user_id": user_id}).first()

	if not existing:
		raise HTTPException(status_code=404, detail=f"Resume {resume_data.resume_id} not found")

	# Build update query dynamically based on provided fields
	update_fields = []
	params = {"resume_id": resume_data.resume_id}

	if resume_data.resume_title is not None:
		update_fields.append("resume_title = :resume_title")
		params["resume_title"] = resume_data.resume_title

	if resume_data.file_name is not None:
		update_fields.append("file_name = :file_name")
		params["file_name"] = resume_data.file_name

	if resume_data.is_baseline is not None:
		update_fields.append("is_baseline = :is_baseline")
		params["is_baseline"] = resume_data.is_baseline

	if resume_data.is_default is not None:
		update_fields.append("is_default = :is_default")
		params["is_default"] = resume_data.is_default

	if resume_data.is_active is not None:
		update_fields.append("is_active = :is_active")
		params["is_active"] = resume_data.is_active

	if resume_data.baseline_resume_id is not None:
		update_fields.append("baseline_resume_id = :baseline_resume_id")
		params["baseline_resume_id"] = resume_data.baseline_resume_id

	if resume_data.job_id is not None:
		update_fields.append("job_id = :job_id")
		params["job_id"] = resume_data.job_id

	if update_fields:
		update_fields.append("resume_updated = NOW()")
		params["user_id"] = user_id
		update_query = text(f"""
			UPDATE resume
			SET {', '.join(update_fields)}
			WHERE resume_id = :resume_id AND user_id = :user_id
		""")
		db.execute(update_query, params)
		db.commit()

	# Update job activity if job_id is in the data
	if resume_data.job_id:
		try:
			update_job_activity(db, resume_data.job_id)
		except Exception as e:
			logger.warning(f"Failed to update job activity", job_id=resume_data.job_id, error=str(e))

	logger.info("Resume updated successfully", resume_id=resume_data.resume_id)
	return {"status": "success", "resume_id": resume_data.resume_id}


@router.post("/resume/detail")
async def create_or_update_resume_detail(
	detail_data: ResumeDetailCreate,
	db: Session = Depends(get_db),
	current_user: dict = Depends(get_current_user)
):
	"""
	Create or update resume detail information.

	This endpoint handles both insert and update operations based on whether
	a record exists in the resume_detail table for the given resume_id.

	JSON body:
	- resume_id: ID of the resume (required)
	- resume_markdown: Markdown version of resume content
	- resume_html: HTML version of resume content
	- position_title: Target position title
	- keyword_count: Number of keywords applied
	- resume_keyword: List of keywords applied
	- focus_count: Number of focus areas applied
	"""
	user_id = current_user.get("user_id")

	# Verify that the resume exists and belongs to user
	resume = db.query(Resume).filter(
		Resume.resume_id == detail_data.resume_id,
		Resume.user_id == user_id
	).first()
	if not resume:
		raise HTTPException(status_code=404, detail="Resume not found")

	# Check if a detail record already exists for this resume_id
	existing_detail = db.query(ResumeDetail).filter(
		ResumeDetail.resume_id == detail_data.resume_id
	).first()

	if existing_detail:
		# Update existing record
		# Update only the fields that are provided (not None)
		update_data = detail_data.dict(exclude={'resume_id'}, exclude_unset=True)

		for field, value in update_data.items():
			setattr(existing_detail, field, value)

		db.commit()
		db.refresh(existing_detail)

		return {"status": "success", "resume_id": existing_detail.resume_id}

	else:
		# Insert new record
		new_detail = ResumeDetail(
			resume_id=detail_data.resume_id,
			resume_markdown=detail_data.resume_markdown,
			resume_html=detail_data.resume_html,
			position_title=detail_data.position_title,
			keyword_count=detail_data.keyword_count,
			resume_keyword=detail_data.resume_keyword,
			focus_count=detail_data.focus_count
		)

		db.add(new_detail)
		db.commit()
		db.refresh(new_detail)

		return {"status": "success", "resume_id": new_detail.resume_id}


@router.delete("/resume")
async def delete_resume(
	resume_id: int,
	db: Session = Depends(get_db),
	current_user: dict = Depends(get_current_user)
):
	"""
	Soft delete a resume record by setting is_active to false.

	This marks the resume as inactive without removing it from the database.
	The physical file is preserved.

	Query parameters:
	- resume_id: ID of the resume to delete
	"""
	user_id = current_user.get("user_id")

	# Fetch the resume - ensure it belongs to user
	resume = db.query(Resume).filter(
		Resume.resume_id == resume_id,
		Resume.user_id == user_id
	).first()

	if not resume:
		raise HTTPException(status_code=404, detail="Resume not found")

	# Soft delete: set is_active to false
	resume.is_active = False
	resume.resume_updated = datetime.utcnow()

	db.commit()

	return {"status": "success", "message": "Resume deleted"}


@router.post("/resume/clone")
async def clone_resume(
	clone_request: ResumeCloneRequest,
	db: Session = Depends(get_db),
	current_user: dict = Depends(get_current_user)
):
	"""
	Clone an existing resume record and its associated file.

	Creates a near-duplicate of the specified resume with unique file_name and resume_title.
	If a resume_detail record exists for the original, it will also be cloned.

	JSON body:
	- resume_id: ID of the resume to clone
	"""
	user_id = current_user.get("user_id")

	# Fetch the original resume - ensure it belongs to user
	original_resume = db.query(Resume).filter(
		Resume.resume_id == clone_request.resume_id,
		Resume.user_id == user_id
	).first()

	if not original_resume:
		raise HTTPException(status_code=404, detail="Resume not found")

	# Extract base filename and extension
	original_file_name = original_resume.file_name
	if not original_file_name:
		raise HTTPException(status_code=400, detail="Original resume has no file_name")

	# Split filename into base and extension
	parts = original_file_name.rsplit('.', 1)
	if len(parts) == 2:
		base_name, extension = parts
	else:
		base_name = original_file_name
		extension = ""

	# Check if a simple -copy already exists for this user
	test_file_name = f"{base_name}-copy.{extension}" if extension else f"{base_name}-copy"

	existing = db.query(Resume).filter(
		Resume.file_name == test_file_name,
		Resume.user_id == user_id
	).first()

	if existing:
		# Need to find the highest numbered copy for this user
		# Use regex to find all copies with numbers
		pattern = f"{re.escape(base_name)}-copy\\d*"

		query = text("""
			SELECT file_name FROM resume
			WHERE file_name ~ :pattern AND user_id = :user_id
			ORDER BY file_name DESC
			LIMIT 1
		""")

		result = db.execute(query, {"pattern": pattern, "user_id": user_id}).first()

		if result:
			# Extract the number from the highest match
			highest_file_name = result[0]
			# Pattern to extract number after -copy
			match = re.search(r'-copy(\d+)', highest_file_name)
			if match:
				next_num = int(match.group(1)) + 1
			else:
				# Existing is -copy without number, so start at 1
				next_num = 1

			new_file_name = f"{base_name}-copy{next_num}.{extension}" if extension else f"{base_name}-copy{next_num}"
		else:
			# Shouldn't happen, but fallback to -copy1
			new_file_name = f"{base_name}-copy1.{extension}" if extension else f"{base_name}-copy1"
	else:
		# Simple -copy is available
		new_file_name = test_file_name

	# Determine suffix for resume_title (use same logic as file_name)
	if original_resume.resume_title:
		if "-copy1" in new_file_name or "-copy2" in new_file_name or "-copy" in new_file_name:
			# Extract the suffix used for file_name
			if "-copy" in new_file_name:
				match = re.search(r'-copy(\d*)', new_file_name)
				if match.group(1):
					# Has number
					suffix = f"-copy{match.group(1)}"
				else:
					# Just -copy
					suffix = "-copy"
				new_resume_title = f"{original_resume.resume_title}{suffix}"
			else:
				new_resume_title = f"{original_resume.resume_title}-copy"
		else:
			new_resume_title = f"{original_resume.resume_title}-copy"
	else:
		new_resume_title = None

	# Ensure resume_title is unique for this user
	unique_resume_title = make_unique_resume_title(new_resume_title, db, user_id) if new_resume_title else new_resume_title

	# Create new resume record
	new_resume = Resume(
		user_id=user_id,
		baseline_resume_id=original_resume.baseline_resume_id,
		job_id=original_resume.job_id,
		original_format=original_resume.original_format,
		resume_title=unique_resume_title,
		file_name=new_file_name,
		is_baseline=original_resume.is_baseline,
		is_default=False,  # Never copy is_default=true
		is_active=original_resume.is_active
	)

	db.add(new_resume)
	db.flush()  # Get the new resume_id

	# Copy the physical file if it exists
	base_path = Path(settings.resume_dir)
	base_path.mkdir(parents=True, exist_ok=True)

	original_file_path = base_path / original_file_name
	new_file_path = base_path / new_file_name

	if original_file_path.exists():
		shutil.copy2(original_file_path, new_file_path)

	# Check if resume_detail exists for original
	original_detail = db.query(ResumeDetail).filter(
		ResumeDetail.resume_id == clone_request.resume_id
	).first()

	if original_detail:
		# Clone the resume_detail record
		new_detail = ResumeDetail(
			resume_id=new_resume.resume_id,
			resume_markdown=original_detail.resume_markdown,
			resume_md_rewrite=original_detail.resume_md_rewrite,
			resume_html=original_detail.resume_html,
			resume_html_rewrite=original_detail.resume_html_rewrite,
			position_title=original_detail.position_title,
			title_line_no=original_detail.title_line_no,
			keyword_count=original_detail.keyword_count,
			resume_keyword=original_detail.resume_keyword,
			keyword_final=original_detail.keyword_final,
			focus_count=original_detail.focus_count,
			focus_final=original_detail.focus_final,
			baseline_score=original_detail.baseline_score,
			rewrite_score=original_detail.rewrite_score,
			suggestion=original_detail.suggestion
		)

		db.add(new_detail)

	db.commit()
	db.refresh(new_resume)

	# Return the new resume record
	return ResumeSchema(
		resume_id=new_resume.resume_id,
		baseline_resume_id=new_resume.baseline_resume_id,
		job_id=new_resume.job_id,
		original_format=new_resume.original_format,
		resume_title=new_resume.resume_title,
		file_name=new_resume.file_name,
		is_baseline=new_resume.is_baseline,
		is_default=new_resume.is_default,
		is_active=new_resume.is_active,
		resume_created=new_resume.resume_created,
		resume_updated=new_resume.resume_updated
	)


@router.post("/resume/extract", response_model=ResumeExtractResponse)
async def extract_resume_data(
	extract_request: ResumeExtractRequest,
	db: Session = Depends(get_db),
	current_user: dict = Depends(get_current_user)
):
	"""
	Extract job title and suggestions from a resume using AI.

	This endpoint uses OpenAI to analyze the resume content and extract:
	- Primary job title
	- Suggestions for improvement

	JSON body:
	- resume_id: ID of the resume to analyze

	Returns:
	- job_title: Object containing job_title string and line_number
	- suggestions: List of improvement suggestions
	"""
	user_id = current_user.get("user_id")

	# Verify the resume belongs to user
	resume = db.query(Resume).filter(
		Resume.resume_id == extract_request.resume_id,
		Resume.user_id == user_id
	).first()
	if not resume:
		raise HTTPException(status_code=404, detail="Resume not found")

	try:
		# Initialize AI agent with database session
		ai_agent = AiAgent(db)

		# Extract data using AI
		result = ai_agent.extract_data(
			resume_id=extract_request.resume_id,
			user_id=user_id
		)

		# Convert the result to response model
		return ResumeExtractResponse(
			job_title=result['job_title'],
			suggestions=result['suggestions']
		)

	except ValueError as e:
		# Handle resume not found or AI parsing errors
		raise HTTPException(status_code=404, detail=str(e))
	except Exception as e:
		# Handle unexpected errors
		raise HTTPException(
			status_code=500,
			detail=f"Error extracting resume data: {str(e)}"
		)

@router.post("/resume/full", response_model=ResumeFullResponse)
async def resume_full(
	request: ResumeFullRequest,
	db: Session = Depends(get_db),
	current_user: dict = Depends(get_current_user)
):
	"""
	Used to create the initial 'resume' and 'resume_detail' records populated with baseline resume

	:param request: baseline_resume_id  the baseline resume to use as the starting template
					job_id              the job posting associated with the resume to create
					keyword_final       finalized keyword selection from job posting
					focus_final         finalized focus keyword list from job posting
	:param db:
	:return: resume_id
	"""
	user_id = current_user.get("user_id")
	logger.info(f"Creating resume for job posting", job_id=request.job_id, baseline_resume_id=request.baseline_resume_id, user_id=user_id)

	try:
		# Step 0: Check for pre-existing resume associated with job posting (ensure user ownership)
		query = text("""
			SELECT j.resume_id, rd.keyword_final, rd.focus_final
			FROM job j JOIN resume_detail rd ON (j.resume_id=rd.resume_id)
			WHERE j.job_id = :job_id AND j.user_id = :user_id
		""")
		check_result = db.execute(query, {"job_id": request.job_id, "user_id": user_id}).first()

		if check_result:
			logger.debug(f"Resume has already been created for this job posting", resume_id=check_result.resume_id)

			# Check for keyword differences
			# Compare keyword_final and focus_final arrays
			existing_keywords = check_result.keyword_final or []
			existing_focus = check_result.focus_final or []
			new_keywords = request.keyword_final or []
			new_focus = request.focus_final or []

			# Check if arrays are identical
			if set(existing_keywords) == set(new_keywords) and set(existing_focus) == set(new_focus):
				# Return cached results
				logger.info(f"Keywords are unchanged - returning resume_id", resume_id=check_result.resume_id)
				return ResumeFullResponse(
					resume_id=check_result.resume_id
				)

			# Need to update resume_detail record with changed keywords
			update_query = text("""
                UPDATE resume_detail
                SET focus_count         = :focus_count,
                    keyword_count       = :keyword_count,
                    keyword_final       = :keyword_final,
                    focus_final         = :focus_final
                WHERE resume_id = :resume_id
            """)

			db.execute(update_query, {
				"resume_id": check_result.resume_id,
				"focus_count": len(request.focus_final),
				"keyword_count": len(request.keyword_final),
				"keyword_final": request.keyword_final,
				"focus_final": request.focus_final
			})
			db.commit()

			logger.log_database_operation("UPDATE", "resume_detail", check_result.resume_id)
			logger.info(f"Updated existing resume successfully", resume_id=check_result.resume_id)

			return ResumeFullResponse(
				resume_id=check_result.resume_id
			)

		# Step 1: Retrieve baseline resume data and verify it's a baseline resume (user ownership)
		query = text("""
			SELECT r.original_format, r.is_baseline, rd.resume_markdown, rd.resume_html, rd.position_title
			FROM resume r
			JOIN resume_detail rd ON (r.resume_id = rd.resume_id)
			WHERE r.resume_id = :resume_id AND r.user_id = :user_id
		""")
		resume_result = db.execute(query, {"resume_id": request.baseline_resume_id, "user_id": user_id}).first()

		if not resume_result:
			logger.warning(f"Resume not found", resume_id=request.baseline_resume_id, user_id=user_id)
			raise HTTPException(status_code=404, detail="Resume not found")

		# Verify is_baseline is true
		if not resume_result.is_baseline:
			logger.error(f"Resume is not a baseline resume", resume_id=request.baseline_resume_id)
			raise HTTPException(status_code=400, detail="Resume must be a baseline resume")

		logger.debug(f"Retrieved baseline resume", baseline_resume_id=request.baseline_resume_id)

		# Step 2: Retrieve job data (user ownership)
		job_query = text("""
			SELECT j.company, j.job_title, jd.job_desc, jd.job_qualification, jd.job_keyword
			FROM job j
			JOIN job_detail jd ON (j.job_id = jd.job_id)
			WHERE j.job_id = :job_id AND j.user_id = :user_id
		""")
		job_result = db.execute(job_query, {"job_id": request.job_id, "user_id": user_id}).first()

		if not job_result:
			logger.warning(f"Job not found", job_id=request.job_id, user_id=user_id)
			raise HTTPException(status_code=404, detail="Job not found")

		if not job_result.job_desc:
			logger.error(f"Job description is empty", job_id=request.job_id)
			raise HTTPException(status_code=400, detail="Job description is required")

		logger.debug(f"Retrieved job data", job_id=request.job_id)

		# Step 3: Create the resume record
		base_resume_title = f"{job_result.company} - {job_result.job_title}"
		unique_resume_title = make_unique_resume_title(base_resume_title, db, user_id)
		file_name = Conversion._set_file(job_result.company, job_result.job_title, 'html')
		baseline_score = calculate_keyword_score(job_result.job_keyword, resume_result.resume_markdown)

		new_resume = Resume(
			user_id=user_id,
			baseline_resume_id=request.baseline_resume_id,
			job_id=request.job_id,
			original_format=resume_result.original_format,
			resume_title=unique_resume_title,
			file_name=file_name,
			is_baseline=False,
			is_default=False,
			is_active=True
		)
		db.add(new_resume)
		db.flush()  # Get the new resume_id

		logger.log_database_operation("INSERT", "resume", new_resume.resume_id)
		logger.debug(f"Created new resume record", new_resume_id=new_resume.resume_id)

		# Step 4: Insert resume_detail record
		new_detail = ResumeDetail(
			resume_id=new_resume.resume_id,
			resume_markdown=resume_result.resume_markdown,
			resume_html=resume_result.resume_html,
			position_title=resume_result.position_title,
			keyword_count=len(request.keyword_final),
			focus_count=len(request.focus_final),
			resume_keyword=job_result.job_keyword,
			baseline_score=baseline_score,
			keyword_final=request.keyword_final,
			focus_final=request.focus_final,
		)
		db.add(new_detail)
		db.commit()

		logger.log_database_operation("INSERT", "resume_detail", new_resume.resume_id)
		logger.debug(f"Resume detail record created", resume_id=new_resume.resume_id)

		# Write HTML content to disk
		if new_resume.file_name and resume_result.resume_html:
			try:
				# Write HTML file to resume directory
				from pathlib import Path
				resume_dir = Path(settings.resume_dir)
				resume_dir.mkdir(parents=True, exist_ok=True)

				html_file_path = resume_dir / new_resume.file_name
				with open(html_file_path, 'w', encoding='utf-8') as f:
					f.write(resume_result.resume_html)

				logger.debug(f"Initial HTML file written to disk", file_path=str(html_file_path))
			except Exception as e:
				# Log error but don't fail the request - HTML is already in database
				logger.warning(f"Failed to write initial HTML file to disk", error=str(e), file_name=new_resume.file_name)
		else:
			logger.warning(f"No file_name or HTML content available, HTML not written to disk", resume_id=new_resume.resume_id)

		# Step 5: Update job record to associate the new resume (ensure user ownership)
		job_update_query = text("""
            UPDATE job SET resume_id = :resume_id WHERE job_id = :job_id AND user_id = :user_id
        """)
		db.execute(job_update_query, {
			"resume_id": new_resume.resume_id,
			"job_id": request.job_id,
			"user_id": user_id
		})
		db.commit()

		logger.log_database_operation("UPDATE", "job", request.job_id)
		logger.info(f"Resume full completed successfully", new_resume_id=new_resume.resume_id, job_id=request.job_id,
		            baseline_score=baseline_score)

		return ResumeFullResponse(
			resume_id=new_resume.resume_id
		)

	except HTTPException:
		# Re-raise HTTP exceptions
		raise

	except Exception as e:
		# Handle unexpected errors
		raise HTTPException(
			status_code=500,
			detail=f"Error creating resume records: {str(e)}"
		)

@router.get("/resume/rewrite/{job_id}", response_model=ResumeRewriteResponse)
async def get_rewrite_data(
	job_id: int,
	db: Session = Depends(get_db),
	current_user: dict = Depends(get_current_user)
):
	"""
	Retrieve the resume rewrite data for a given job.

	This endpoint returns the resume data after the rewrite process has completed.
	It should be called after polling indicates the process is complete.

	Args:
		job_id: ID of the job
		db: Database session

	Returns:
		ResumeRewriteResponse with resume data including HTML, suggestions, and scores
	"""
	user_id = current_user.get("user_id")
	try:
		logger.debug(f"Start resume/rewrite data retrieval", job_id=job_id, user_id=user_id)

		query = text("""
			SELECT rd.resume_id, rd.resume_html, rd.resume_html_rewrite, rd.suggestion,
			       rd.baseline_score, rd.rewrite_score
			FROM job j
			LEFT JOIN resume_detail rd ON (j.resume_id = rd.resume_id)
			WHERE j.job_id = :job_id AND j.user_id = :user_id
		""")
		result = db.execute(query, {"job_id": job_id, "user_id": user_id}).first()

		if not result:
			logger.warning(f"Job resume not found", job_id=job_id, user_id=user_id)
			raise HTTPException(status_code=404, detail="Job resume not found")

		logger.info(f"Resume rewrite data retrieved successfully", job_id=job_id, resume_id=result.resume_id)

		return ResumeRewriteResponse(
			resume_id=result.resume_id,
			resume_html=result.resume_html or "",
			resume_html_rewrite=result.resume_html_rewrite or "",
			suggestion=result.suggestion or [],
			baseline_score=result.baseline_score or 0,
			rewrite_score=result.rewrite_score or 0
		)
	except HTTPException:
		raise
	except Exception as e:
		logger.error(f"Error retrieving resume rewrite data", job_id=job_id, error=str(e))
		raise HTTPException(status_code=500, detail=f"Error retrieving resume data: {str(e)}")

@router.post("/resume/rewrite", status_code=status.HTTP_202_ACCEPTED)
async def rewrite_resume(
	request: ResumeRewriteRequest,
	background_tasks: BackgroundTasks,
	db: Session = Depends(get_db),
	current_user: dict = Depends(get_current_user)
):
	"""
	Rewrite resume using baseline resume for a specific job using AI.

	This endpoint performs the following operations:
	1. Create process record entry to DB
	2. Start background process resume_rewrite_process
	3. Return 202 with process_id

	The rewrite process runs asynchronously. Use the /v1/process/poll endpoint
	to check the status, then call GET /v1/resume/rewrite/{job_id} to retrieve results.

	Args:
		request: ResumeRewriteRequest with job_id
		background_tasks: FastAPI background tasks
		db: Database session

	Returns:
		202 Accepted with process_id
	"""
	user_id = current_user.get("user_id")
	try:
		logger.info(f"Initiating resume rewrite", job_id=request.job_id, user_id=user_id)

		# Verify the job exists, belongs to user, and has a resume
		verify_query = text("""
			SELECT j.resume_id
			FROM job j
			WHERE j.job_id = :job_id AND j.user_id = :user_id
		""")
		job_result = db.execute(verify_query, {"job_id": request.job_id, "user_id": user_id}).first()

		if not job_result:
			logger.warning(f"Job not found", job_id=request.job_id, user_id=user_id)
			raise HTTPException(status_code=404, detail="Job not found")

		if not job_result.resume_id:
			logger.warning(f"Job has no resume associated", job_id=request.job_id, user_id=user_id)
			raise HTTPException(status_code=400, detail="Job has no resume associated")

		# Create process record using ORM to get the auto-generated process_id
		from ..models.models import Process
		new_process = Process(
			endpoint_called="/v1/resume/rewrite",
			running_method="resume_rewrite_process",
			running_class="AiAgent"
		)
		db.add(new_process)
		db.commit()
		db.refresh(new_process)

		process_id = new_process.process_id
		logger.debug(f"Created process record", process_id=process_id)

		# Start background task for AI rewrite in a separate thread
		# This prevents blocking the event loop during the long-running OpenAI API call
		# IMPORTANT: The thread must NOT use the request-scoped database session
		# to avoid keeping the HTTP connection open
		import threading
		from ..core.database import SessionLocal

		# Capture user_id for the thread
		thread_user_id = user_id

		def run_rewrite():
			# Create a new database session for the thread
			# DO NOT use the request-scoped 'db' session
			thread_db = SessionLocal()
			try:
				thread_ai_agent = AiAgent(thread_db)
				thread_ai_agent.resume_rewrite_process(request.job_id, process_id, thread_user_id)
			finally:
				thread_db.close()

		# Run in separate thread to avoid blocking the event loop
		thread = threading.Thread(target=run_rewrite, daemon=True)
		thread.start()

		logger.info(f"Resume rewrite process started", job_id=request.job_id, process_id=process_id)

		return {"process_id": process_id}

	except HTTPException:
		raise
	except Exception as e:
		logger.error(f"Error initiating resume rewrite", job_id=request.job_id, error=str(e))
		raise HTTPException(status_code=500, detail=f"Error initiating resume rewrite: {str(e)}")



