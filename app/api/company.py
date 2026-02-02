from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
import shutil

from ..core.database import get_db, SessionLocal
from ..models.models import Company, Job, Process
from ..schemas.company import CompanyCreate, CompanyUpdate, CompanyResponse
from ..utils.logger import logger
from ..utils.ai_agent import AiAgent
from ..utils.file_helpers import set_filename
from ..middleware.auth_middleware import get_current_user
import threading

router = APIRouter()


@router.post("/company", status_code=status.HTTP_200_OK)
async def create_company(
	company_data: CompanyCreate,
	db: Session = Depends(get_db),
	user_id: str = Depends(get_current_user)
):
	"""
	Create a new company record.
	company_name is required, job_id is required.

	If a company record already exists for the given job_id, returns the existing company_id.
	"""

	logger.info(f"Attempting to create company", company_name=company_data.company_name, job_id=company_data.job_id, user_id=user_id)

	# Verify job_id is provided (now required due to NOT NULL constraint)
	if not company_data.job_id:
		logger.warning(f"Job ID is required", user_id=user_id)
		raise HTTPException(status_code=400, detail="job_id is required")

	# Verify job exists and belongs to user
	job = db.query(Job).filter(Job.job_id == company_data.job_id, Job.user_id == user_id).first()
	if not job:
		logger.warning(f"Job not found", job_id=company_data.job_id, user_id=user_id)
		raise HTTPException(status_code=404, detail=f"Job with id {company_data.job_id} not found")

	# Check if company record already exists for this job_id and user
	existing_company = db.query(Company).filter(
		Company.job_id == company_data.job_id,
		Company.user_id == user_id
	).first()
	if existing_company:
		logger.info(f"Company record already exists for job_id",
				   job_id=company_data.job_id,
				   company_id=existing_company.company_id,
				   company_name=existing_company.company_name,
				   user_id=user_id)
		return {"status": "success", "company_id": existing_company.company_id, "existed": True}

	# Create new company with user_id
	company_dict = company_data.model_dump(exclude_unset=True)
	company_dict['user_id'] = user_id
	company = Company(**company_dict)
	db.add(company)
	db.commit()
	db.refresh(company)

	logger.log_database_operation("INSERT", "company", company.company_id)
	logger.info(f"Company created successfully", company_id=company.company_id, company_name=company.company_name, user_id=user_id)

	return {"status": "success", "company_id": company.company_id, "existed": False}


@router.put("/company", status_code=status.HTTP_200_OK)
async def update_company(
	company_data: CompanyUpdate,
	db: Session = Depends(get_db),
	user_id: str = Depends(get_current_user)
):
	"""
	Update an existing company record.
	company_id is required to identify the record.

	If company_logo_url is provided, downloads the image, saves it locally,
	and sets the logo_file field.
	"""
	from ..core.config import settings
	import os
	import requests
	import mimetypes


	logger.info(f"Attempting to update company", company_id=company_data.company_id, user_id=user_id)

	# Find the company - ensure it belongs to user
	company = db.query(Company).filter(
		Company.company_id == company_data.company_id,
		Company.user_id == user_id
	).first()
	if not company:
		logger.warning(f"Company not found for update", company_id=company_data.company_id, user_id=user_id)
		raise HTTPException(status_code=404, detail=f"Company with id {company_data.company_id} not found")

	# Verify job exists and belongs to user if job_id is provided
	if company_data.job_id:
		job = db.query(Job).filter(Job.job_id == company_data.job_id, Job.user_id == user_id).first()
		if not job:
			logger.warning(f"Job not found", job_id=company_data.job_id, user_id=user_id)
			raise HTTPException(status_code=404, detail=f"Job with id {company_data.job_id} not found")

	# Handle company_logo_url if provided
	if company_data.company_logo_url:
		try:
			logger.info(f"Downloading logo from URL", url=company_data.company_logo_url)

			# Download the image
			response = requests.get(company_data.company_logo_url, timeout=10, stream=True)
			response.raise_for_status()

			# Determine file extension from content-type
			content_type = response.headers.get('content-type', '')
			extension = mimetypes.guess_extension(content_type)
			if not extension:
				# Fallback to URL extension
				extension = os.path.splitext(company_data.company_logo_url)[1]
			if not extension:
				extension = '.png'  # Default fallback

			# Create filename from company name
			safe_name = company_data.company_name.lower().replace(' ', '_')
			safe_name = ''.join(c for c in safe_name if c.isalnum() or c == '_')
			filename = f"{safe_name}{extension}"

			# Ensure logo directory exists
			os.makedirs(settings.logo_dir, exist_ok=True)

			# Save the file
			filepath = os.path.join(settings.logo_dir, filename)
			with open(filepath, 'wb') as f:
				for chunk in response.iter_content(chunk_size=8192):
					f.write(chunk)

			# Set logo_file field
			company.logo_file = filename
			logger.info(f"Logo saved successfully", filename=filename)

		except Exception as e:
			logger.error(f"Failed to download logo", error=str(e), url=company_data.company_logo_url)
			# Don't fail the update if logo download fails

	# Update fields that are provided (excluding company_id and company_logo_url)
	update_data = company_data.model_dump(exclude_unset=True, exclude={'company_id', 'company_logo_url'})
	for field, value in update_data.items():
		setattr(company, field, value)

	db.commit()
	db.refresh(company)

	logger.log_database_operation("UPDATE", "company", company.company_id)
	logger.info(f"Company updated successfully", company_id=company.company_id, company_name=company.company_name)

	return {"status": "success", "company_id": company.company_id}


@router.get("/company/list")
async def get_company_list(
	db: Session = Depends(get_db),
	user_id: str = Depends(get_current_user)
):
	"""
	Retrieve list of all company reports.

	Returns companies that have report_html content, ordered by company_name.
	"""

	logger.info("Fetching company list", user_id=user_id)

	companies = db.query(Company).filter(Company.report_html.isnot(None), Company.report_html != '', Company.user_id == user_id).order_by(Company.company_name.asc()).all()

	logger.log_database_operation("SELECT", "company", "list")
	logger.info(f"Retrieved company list", count=len(companies))

	# Convert to list of dicts with all fields
	result = []
	for company in companies:
		result.append({
			"company_id": company.company_id,
			"company_name": company.company_name or "",
			"website_url": company.website_url or "",
			"hq_city": company.hq_city or "",
			"hq_state": company.hq_state or "",
			"industry": company.industry or "",
			"logo_file": company.logo_file or "",
			"linkedin_url": company.linkedin_url or "",
			"job_id": company.job_id or "",
			"report_html": company.report_html or "",
			"report_created": company.report_created.isoformat() if company.report_created else ""
		})

	return result


@router.get("/company/{company_id}", response_model=CompanyResponse)
async def get_company(
	company_id: int,
	db: Session = Depends(get_db),
	user_id: str = Depends(get_current_user)
):
	"""
	Retrieve a specific company record by company_id.
	"""

	logger.info(f"Fetching company", company_id=company_id, user_id=user_id)

	company = db.query(Company).filter(
		Company.company_id == company_id,
		Company.user_id == user_id
	).first()
	if not company:
		logger.warning(f"Company not found", company_id=company_id, user_id=user_id)
		raise HTTPException(status_code=404, detail=f"Company with id {company_id} not found")

	logger.log_database_operation("SELECT", "company", company_id)
	logger.info(f"Company retrieved successfully", company_id=company_id, company_name=company.company_name,
			   has_report=bool(company.report_html), report_length=len(company.report_html) if company.report_html else 0,
			   report_preview=company.report_html[:100] if company.report_html else "", user_id=user_id)

	return company


@router.get("/company/job/{job_id}")
async def get_company_by_job(
	job_id: int,
	db: Session = Depends(get_db),
	user_id: str = Depends(get_current_user)
):
	"""
	Retrieve company data associated with a specific job_id.

	Returns job.company field along with company record if it exists.
	"""
	from sqlalchemy import text


	logger.info(f"Fetching company by job_id", job_id=job_id, user_id=user_id)

	# Execute query to get job.company and company fields - filter by user_id
	query = text("""
		SELECT j.company, c.company_id, c.company_name, c.website_url, c.hq_city,
			   c.hq_state, c.industry, c.logo_file, c.linkedin_url, c.job_id, c.report_html
		FROM job j
		LEFT JOIN company c ON (j.job_id = c.job_id AND c.user_id = :user_id)
		WHERE j.job_id = :job_id AND j.user_id = :user_id
	""")

	result = db.execute(query, {"job_id": job_id, "user_id": user_id}).fetchone()

	if not result:
		logger.warning(f"Job not found", job_id=job_id, user_id=user_id)
		raise HTTPException(status_code=404, detail=f"Job with id {job_id} not found")

	logger.log_database_operation("SELECT", "company", job_id)

	# Build response
	response = {
		"company": result[0] if result[0] else "",
		"company_id": result[1] if result[1] else None,
		"company_name": result[2] if result[2] else "",
		"website_url": result[3] if result[3] else "",
		"hq_city": result[4] if result[4] else "",
		"hq_state": result[5] if result[5] else "",
		"industry": result[6] if result[6] else "",
		"logo_file": result[7] if result[7] else "",
		"linkedin_url": result[8] if result[8] else "",
		"job_id": result[9] if result[9] else "",
		"report_html": result[10] if result[10] else ""
	}

	logger.info(f"Company by job retrieved successfully", job_id=job_id,
				has_company_record=result[1] is not None)

	return response


@router.get("/company/search/{company_id}")
async def search_company(
	company_id: int,
	db: Session = Depends(get_db),
	user_id: str = Depends(get_current_user)
):
	"""
	Search for company information using AI to identify and verify company details.

	Returns a list of potential company matches with:
	- company_name
	- website_url
	- location_city
	- location_state
	- industry
	- match_score
	- company_logo_url
	"""

	logger.info(f"Starting company search", company_id=company_id, user_id=user_id)

	# Verify company exists and belongs to user
	company = db.query(Company).filter(
		Company.company_id == company_id,
		Company.user_id == user_id
	).first()
	if not company:
		logger.warning(f"Company not found for search", company_id=company_id, user_id=user_id)
		raise HTTPException(status_code=404, detail=f"Company with id {company_id} not found")



	try:
		# Initialize AI agent and perform company search
		ai_agent = AiAgent(db)
		search_results = ai_agent.company_search(company_id)

		logger.info(f"Company search completed", company_id=company_id, results_count=len(search_results))

		for result in search_results:
			logger.debug(f"Match entry values", logo_url=result.get("company_logo_url"), company_name=result.get("company_name"))

		return search_results

	except ValueError as e:
		logger.error(f"Company search failed", company_id=company_id, error=str(e))
		raise HTTPException(status_code=400, detail=str(e))
	except Exception as e:
		logger.error(f"Unexpected error during company search", company_id=company_id, error=str(e))
		raise HTTPException(status_code=500, detail=f"Internal server error during company search: {str(e)}")


@router.get("/company/research/{company_id}", status_code=status.HTTP_202_ACCEPTED)
async def research_company(
	company_id: int,
	db: Session = Depends(get_db),
	user_id: str = Depends(get_current_user)
):
	"""
	Initiate company research process using AI.

	Returns 202 Accepted with process_id immediately, then runs AI research in background.

	The background process will:
	1. Retrieve company data with related job and resume information
	2. Generate comprehensive company research report using AI
	3. Update company record with report HTML
	4. Mark process as completed

	Returns:
		202 status with process_id for polling
	"""

	logger.info(f"Initiating company research", company_id=company_id, user_id=user_id)

	# Verify company exists and belongs to user
	company = db.query(Company).filter(Company.company_id == company_id, Company.user_id == user_id).first()
	if not company:
		logger.warning(f"Company not found for research", company_id=company_id, user_id=user_id)
		raise HTTPException(status_code=404, detail=f"Company with id {company_id} not found")

	# Create process record
	process = Process(
		endpoint_called='/v1/company/research',
		running_method='company_research_process',
		running_class='AiAgent'
	)
	db.add(process)
	db.commit()
	db.refresh(process)

	process_id = process.process_id
	logger.info(f"Created process record", company_id=company_id, process_id=process_id)

	# Start background task for AI research in a separate thread
	# IMPORTANT: The thread must NOT use the request-scoped database session
	# to avoid keeping the HTTP connection open
	def run_research():
		# Create a new database session for the thread
		# DO NOT use the request-scoped 'db' session
		thread_db = SessionLocal()
		try:
			thread_ai_agent = AiAgent(thread_db)
			thread_ai_agent.company_research_process(company_id, process_id)
		finally:
			thread_db.close()

	# Run in separate thread to avoid blocking the event loop
	thread = threading.Thread(target=run_research, daemon=True)
	thread.start()

	logger.info(f"Started background company research process", company_id=company_id, process_id=process_id)

	return {"process_id": process_id}


@router.delete("/company/{company_id}", status_code=status.HTTP_200_OK)
async def delete_company(
	company_id: int,
	db: Session = Depends(get_db),
	user_id: str = Depends(get_current_user)
):
	"""
	Delete a company record.
	"""

	logger.info(f"Attempting to delete company", company_id=company_id, user_id=user_id)

	company = db.query(Company).filter(
		Company.company_id == company_id,
		Company.user_id == user_id
	).first()
	if not company:
		logger.warning(f"Company not found for deletion", company_id=company_id, user_id=user_id)
		raise HTTPException(status_code=404, detail=f"Company with id {company_id} not found")

	# Delete the company record
	db.delete(company)
	db.commit()

	logger.log_database_operation("DELETE", "company", company_id)
	logger.info(f"Company deleted successfully", company_id=company_id, user_id=user_id)

	return {"status": "success", "message": "Company deleted successfully"}


@router.get("/company/download/{company_id}")
async def download_company_report(
	company_id: int,
	db: Session = Depends(get_db),
	user_id: int = Depends(get_current_user)
):
	"""
	Download company report as DOCX file.

	Converts report_html to DOCX format and saves to REPORT_DIR.
	Returns filename for download.
	"""
	from ..core.config import settings
	from ..utils.conversion import Conversion
	import os

	logger.info(f"Downloading company report", company_id=company_id, user_id=user_id)

	company = db.query(Company).filter(Company.company_id == company_id, Company.user_id == user_id).first()
	if not company:
		logger.warning(f"Company not found for download", company_id=company_id, user_id=user_id)
		raise HTTPException(status_code=404, detail=f"Company with id {company_id} not found")

	if not company.report_html or company.report_html.strip() == "":
		logger.warning(f"No report HTML found for company", company_id=company_id)
		raise HTTPException(status_code=404, detail="No report found for this company")

	try:
		import tempfile
		from pathlib import Path

		logger.info(f"Processing company report download", company_id=company_id, company_name=company.company_name)

		filename = set_filename(company.__getattribute__('company_name'), 'company_report', 'docx')
		logger.info(f"Generated filename", filename=filename)

		# Ensure directory exists
		os.makedirs(settings.report_dir, exist_ok=True)
		logger.info(f"Report directory ensured", report_dir=settings.report_dir)

		# Create temporary HTML file
		with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as temp_html:
			temp_html.write(company.report_html)
			temp_html_path = temp_html.name

		logger.info(f"Created temporary HTML file", temp_path=temp_html_path)

		# Output path for DOCX
		output_path = os.path.join(settings.report_dir, filename)

		# Convert HTML to DOCX using user settings
		success = Conversion.convert_file('html', 'docx', temp_html_path, output_path, user_id)

		# Clean up temp file
		try:
			os.unlink(temp_html_path)
		except:
			logger.error(f"An Error happened on download_company_report", company_id=company_id)
			pass

		if not success:
			logger.error(f"Conversion failed")
			raise HTTPException(status_code=500, detail=f"Failed to convert report to DOCX")

		# Verify file exists at target location
		if not os.path.exists(output_path):
			logger.error(f"Report file was not created at target", expected_path=str(output_path))
			raise HTTPException(status_code=500, detail=f"Report file not found: {filename}")

		logger.info(f"Company report converted to DOCX", company_id=company_id, filename=filename, path=str(output_path),
				   file_exists=os.path.exists(output_path), file_size=os.path.getsize(output_path) if os.path.exists(output_path) else 0)

		return {"file_name": filename}

	except Exception as e:
		logger.error(f"Error converting company report to DOCX", company_id=company_id, error=str(e))
		raise HTTPException(status_code=500, detail=f"Failed to generate report: {str(e)}")
