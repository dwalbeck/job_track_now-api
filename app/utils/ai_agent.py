import os
import json
import sys
import time
from fastapi import HTTPException, BackgroundTasks
from pathlib import Path
from openai import OpenAI
from sqlalchemy.orm import Session
from sqlalchemy import text, Boolean
from typing import List
from starlette.responses import JSONResponse
from sympy.categories import Object

from ..core.config import settings
from ..core.database import SessionLocal
from ..utils.logger import logger
from ..utils.conversion import Conversion


class AiAgent:
	"""
	AI Agent class for handling resume analysis and processing using OpenAI API.
	"""

	def __init__(self, db: Session, user_id: int = None):
		"""
		Initialize the AI Agent with database session.

		Args:
			db: SQLAlchemy database session
			user_id: Current user's ID for loading user-specific settings
		"""
		self.db = db

		# Load LLM settings and API keys from database for this user
		# This updates the global settings object with user-specific values
		if user_id:
			settings.load_llm_settings_from_db(db, user_id)

		# Set instance variables from settings (now includes user's DB values if loaded)
		self.api_key = settings.openai_api_key
		self.project = settings.openai_project

		# Set LLM models from config (these can be different for each AI operation)
		self.default_llm = settings.default_llm
		self.resume_extract_llm = settings.resume_extract_llm
		self.job_extract_llm = settings.job_extract_llm
		self.rewrite_llm = settings.rewrite_llm
		self.cover_llm = settings.cover_llm
		self.company_llm = settings.company_llm
		self.tools_llm = settings.tools_llm
		self.culture_llm = settings.culture_llm
		self.question_llm = settings.question_llm

		# Initialize OpenAI client with timeout
		client_kwargs = {
			"api_key": self.api_key,
			"timeout": 600.0,  # 10 minute timeout for API requests (resume rewrite can be very large)
			"max_retries": 0   # Don't retry - fail fast to avoid long waits
		}
		if self.project:
			client_kwargs["project"] = self.project

		self.client = OpenAI(**client_kwargs)

		# Path to prompt templates
		self.prompts_dir = Path(__file__).parent / 'prompts'

	def _load_prompt(self, prompt_name: str) -> str:
		"""
		Load a prompt template from the prompts directory.

		Args:
			prompt_name: Name of the prompt file (without extension)

		Returns:
			Prompt template as string
		"""
		prompt_path = self.prompts_dir / f"{prompt_name}.txt"

		if not prompt_path.exists():
			raise FileNotFoundError(f"Prompt template not found: {prompt_name}")

		with open(prompt_path, 'r') as f:
			return f.read()

	def _parse_json_response(self, response_text: str, required_keys: list = None) -> dict:
		"""
		Robustly parse JSON from AI response, handling common issues like:
		- Unescaped newlines in string values
		- Markdown code blocks wrapping JSON
		- Nested objects with special characters

		Args:
			response_text: Raw response text from AI
			required_keys: List of keys that must be present in parsed result

		Returns:
			Parsed JSON dictionary

		Raises:
			ValueError: If parsing fails after all attempts
		"""
		import re

		# Helper to attempt JSON parsing with error info
		def try_parse(text, description=""):
			try:
				return json.loads(text)
			except json.JSONDecodeError as e:
				logger.debug(f"JSON parse attempt failed ({description})", error=str(e))
				return None

		# Attempt 1: Direct parsing
		result = try_parse(response_text, "direct")
		if result:
			return result

		# Attempt 2: Extract from HTML code blocks using balanced brace matching
		# First, find the code block
		code_block_match = re.search(r'```(?:json)?\s*(\{.+)', response_text, re.DOTALL)
		if code_block_match:
			# Extract from the opening brace and find the matching closing brace
			json_start = code_block_match.group(1)
			# Find the closing ``` and take content before it
			end_match = re.search(r'\}\s*```', json_start)
			if end_match:
				json_text = json_start[:end_match.end()-3].strip()
				result = try_parse(json_text, "markdown block")
				if result:
					return result

		# Attempt 3: Find JSON object using balanced brace matching
		# Find the first { and match to its closing }
		first_brace = response_text.find('{')
		if first_brace != -1:
			brace_count = 0
			in_string = False
			escape_next = False
			last_brace = -1

			for i, char in enumerate(response_text[first_brace:], first_brace):
				if escape_next:
					escape_next = False
					continue
				if char == '\\':
					escape_next = True
					continue
				if char == '"' and not escape_next:
					in_string = not in_string
					continue
				if not in_string:
					if char == '{':
						brace_count += 1
					elif char == '}':
						brace_count -= 1
						if brace_count == 0:
							last_brace = i
							break

			if last_brace != -1:
				json_text = response_text[first_brace:last_brace + 1]
				result = try_parse(json_text, "balanced braces")
				if result:
					return result

				# Attempt 4: Try to repair common JSON issues in the extracted text
				# Fix unescaped newlines inside strings
				repaired = self._repair_json_string(json_text)
				result = try_parse(repaired, "repaired JSON")
				if result:
					return result

		# All attempts failed
		preview = response_text[:500] if len(response_text) > 500 else response_text
		raise ValueError(f"Failed to parse AI response as JSON after all attempts. Response preview: {preview}")

	def _repair_json_string(self, json_text: str) -> str:
		"""
		Attempt to repair common JSON issues, particularly unescaped newlines in strings.

		Args:
			json_text: Potentially malformed JSON string

		Returns:
			Repaired JSON string
		"""
		# This is a heuristic repair - try to escape newlines that appear inside strings
		result = []
		in_string = False
		escape_next = False
		i = 0

		while i < len(json_text):
			char = json_text[i]

			if escape_next:
				result.append(char)
				escape_next = False
				i += 1
				continue

			if char == '\\':
				result.append(char)
				escape_next = True
				i += 1
				continue

			if char == '"':
				result.append(char)
				in_string = not in_string
				i += 1
				continue

			if in_string and char == '\n':
				# Replace unescaped newline with escaped version
				result.append('\\n')
				i += 1
				continue

			if in_string and char == '\r':
				# Skip carriage returns or escape them
				if i + 1 < len(json_text) and json_text[i + 1] == '\n':
					result.append('\\n')
					i += 2
					continue
				else:
					result.append('\\r')
					i += 1
					continue

			if in_string and char == '\t':
				# Escape tabs
				result.append('\\t')
				i += 1
				continue

			result.append(char)
			i += 1

		return ''.join(result)

	def get_html(self, resume_id: int) -> str:
		"""
		Retrieve the HTML content of a resume from the DB

		Args:
			resume_id: ID of the resume to retrieve

		Returns:
			original HTML content of the resume
		"""
		query = text("SELECT resume_html FROM resume_detail WHERE resume_id = :resume_id")
		result = self.db.execute(query, {"resume_id": resume_id}).first()

		if not result:
			raise ValueError(f"Resume not found for resume_id: {resume_id}")

		return result[0]

	def get_markdown(self, resume_id: int) -> str:
		"""
		Retrieve the markdown content of a resume from the database.

		Args:
			resume_id: ID of the resume to retrieve

		Returns:
			Markdown content of the resume

		Raises:
			ValueError: If resume not found
		"""
		query = text("SELECT resume_markdown FROM resume_detail WHERE resume_id = :resume_id")
		result = self.db.execute(query, {"resume_id": resume_id}).first()

		if not result:
			raise ValueError(f"Resume not found for resume_id: {resume_id}")

		return result[0]

	def extract_data(self, resume_id: int) -> dict:
		"""
		Extract job title, keywords, and suggestions from a resume using AI.

		Args:
			resume_id: ID of the resume to analyze
			bad_list: List of job titles to exclude from selection

		Returns:
			Dictionary containing:
				- job_title: dict with job_title and line_number
				- suggestions: list of improvement suggestions
		"""

		# Get the HTML resume
		resume_html = self.get_html(resume_id)

		# Load the prompt template
		prompt_template = self._load_prompt('extract_data')

		# Format the prompt with variables using replace to avoid issues with curly braces
		prompt = prompt_template.replace('{resume_html}', resume_html)

		logger.debug('LLM model used for extracting resume data', llm=self.resume_extract_llm)
		# Make API call to OpenAI
		response = self.client.chat.completions.create(
			model=self.resume_extract_llm,
			messages=[
				{"role": "system", "content": "Expert resume writer and analyst. You analyze resumes and provide structured data in JSON format."},
				{"role": "user", "content": prompt}
			]
		)

		# Extract the response content
		response_text = response.choices[0].message.content

		# Parse JSON response
		try:
			# Try to parse the response as JSON
			result = json.loads(response_text)

			# Validate the structure
			if not all(key in result for key in ['job_title', 'suggestions']):
				raise ValueError("Response missing required keys")

			return result

		except json.JSONDecodeError as e:
			# If JSON parsing fails, try to extract JSON from markdown code blocks
			import re
			json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
			if json_match:
				try:
					result = json.loads(json_match.group(1))
					return result
				except json.JSONDecodeError:
					pass

			raise ValueError(f"Failed to parse AI response as JSON: {str(e)}")

	def job_extraction(self, job_id: int, user_id: int) -> dict:
		"""
		Extract job qualifications and keywords from a job description using AI.

		Args:
			job_id: ID of the job to analyze

		Returns:
			Dictionary containing:
				- job_qualification: extracted qualification section text
				- keywords: list of extracted keywords

		Raises:
			ValueError: If job not found or job_desc is empty
		"""
		# First verify the job exists
		job_query = text("SELECT job_id FROM job WHERE job_id = :job_id AND job_active = true AND user_id = :user_id")
		job_result = self.db.execute(job_query, {"job_id": job_id, "user_id": user_id}).first()

		if not job_result:
			raise ValueError(f"Job not found or inactive for job_id: {job_id}")

		# Get the job description from job_detail table
		query = text("SELECT job_desc FROM job_detail WHERE job_id = :job_id")
		result = self.db.execute(query, {"job_id": job_id}).first()

		if not result:
			raise ValueError(f"No job description found. Please edit the job and add a job description before using resume optimization.")

		job_desc = result[0]
		if not job_desc:
			raise ValueError(f"Job description is empty. Please edit the job and add a job description before using resume optimization.")

		# Load the prompt template
		prompt_template = self._load_prompt('job_extract')

		# Format the prompt with the job description
		# Use replace instead of format to avoid issues with curly braces in the template
		prompt = prompt_template.replace('{job_desc}', job_desc)

		# Make API call to OpenAI
		try:
			response = self.client.chat.completions.create(
				model=self.job_extract_llm,
				messages=[
					{"role": "system", "content": "Expert job analyst. You analyze job descriptions and extract qualifications and keywords in JSON format."},
					{"role": "user", "content": prompt}
				]
			)

			# Extract the response content
			response_text = response.choices[0].message.content

			if not response_text:
				raise ValueError("OpenAI returned empty response")

			# Debug: print the raw response
			print(f"DEBUG: Raw OpenAI response: {repr(response_text[:500])}", file=sys.stderr, flush=True)

		except Exception as e:
			raise ValueError(f"OpenAI API call failed: {str(e)}")

		# Parse JSON response
		try:
			# Remove any leading/trailing whitespace and try to parse as JSON
			response_text = response_text.strip()
			print(f"DEBUG: After strip: {repr(response_text[:500])}", file=sys.stderr, flush=True)
			result = json.loads(response_text)
			print(f"DEBUG: Successfully parsed JSON", file=sys.stderr, flush=True)

			# Validate the structure
			if not all(key in result for key in ['job_qualification', 'keywords']):
				missing_keys = [key for key in ['job_qualification', 'keywords'] if key not in result]
				raise ValueError(f"Response missing required keys: {missing_keys}. Response was: {response_text[:500]}")

			# Update the job_detail record with extracted data
			# Convert keywords list to PostgreSQL array format
			keywords = result.get('keywords', [])

			update_query = text("""
				UPDATE job_detail
				SET job_qualification = :job_qualification,
					job_keyword = :job_keyword
				WHERE job_id = :job_id
			""")

			self.db.execute(update_query, {
				"job_id": job_id,
				"job_qualification": result.get('job_qualification', ''),
				"job_keyword": keywords
			})
			self.db.commit()

			return result

		except json.JSONDecodeError as e:
			# If JSON parsing fails, try to extract JSON from markdown code blocks
			import re

			# Print debug info for troubleshooting
			print(f"DEBUG: JSON parsing failed. Response text: {response_text[:1000]}", file=sys.stderr, flush=True)

			# Try multiple regex patterns to extract JSON
			json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
			if not json_match:
				# Try without code blocks, just find JSON object
				json_match = re.search(r'(\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\})', response_text, re.DOTALL)
			if json_match:
				try:
					result = json.loads(json_match.group(1))

					# Validate structure in markdown block too
					if not all(key in result for key in ['job_qualification', 'keywords']):
						missing_keys = [key for key in ['job_qualification', 'keywords'] if key not in result]
						raise ValueError(f"Response missing required keys: {missing_keys}")

					# Update the job_detail record
					# Convert keywords list to PostgreSQL array format
					keywords = result.get('keywords', [])

					update_query = text("""
						UPDATE job_detail
						SET job_qualification = :job_qualification,
							job_keyword = :job_keyword
						WHERE job_id = :job_id
					""")

					self.db.execute(update_query, {
						"job_id": job_id,
						"job_qualification": result.get('job_qualification', ''),
						"job_keyword": keywords
					})
					self.db.commit()

					return result
				except (json.JSONDecodeError, KeyError) as e:
					raise ValueError(f"Failed to parse JSON from markdown block: {str(e)}")

			raise ValueError(f"Failed to parse AI response as JSON. Original error: {type(e).__name__}: {str(e)}. Full response: {response_text}")

	def company_search(self, company_id: int) -> list:
		"""
		Search for company information using AI to identify and verify company details.

		Args:
			company_id: ID of the company to search for

		Returns:
			List of potential company matches with logo files saved locally

		Raises:
			ValueError: If company not found
		"""
		import base64
		db = SessionLocal()

		# Retrieve company record from database
		company_query = text("""
			SELECT c.company_name, c.linkedin_url, c.website_url, c.hq_city, c.hq_state, c.job_id, jd.job_desc 
			FROM company c LEFT JOIN job_detail jd ON (c.job_id=jd.job_id) 
			WHERE c.company_id = :company_id
		""")
		company_result = self.db.execute(company_query, {"company_id": company_id}).first()

		if not company_result:
			raise ValueError(f"Company not found for company_id: {company_id}")

		company_name = company_result.company_name or ""
		linkedin_url = company_result.linkedin_url or ""
		website_url = company_result.website_url or ""
		location_city = company_result.hq_city or ""
		location_state = company_result.hq_state or ""
		job_desc = company_result.job_desc or ""

		# Load the prompt template
		prompt_template = self._load_prompt('identify_company')

		# Format the prompt with company information
		prompt = prompt_template.replace('{company_name}', company_name)
		prompt = prompt.replace('{linkedin_url}', linkedin_url)
		prompt = prompt.replace('{company_website}', website_url)
		prompt = prompt.replace('{location_city}', location_city)
		prompt = prompt.replace('{location_state}', location_state)
		prompt = prompt.replace('{job_desc}', job_desc)

		# Make API call to OpenAI
		try:
			response = self.client.chat.completions.create(
				model=self.company_llm,
				messages=[
					{"role": "system", "content": "Expert company researcher. You identify and verify company information, returning results in JSON format."},
					{"role": "user", "content": prompt}
				]
			)

			# Extract the response content
			response_text = response.choices[0].message.content.strip()
			logger.debug(f"AI company search response received", company_id=company_id, response_length=len(response_text))

			# Parse JSON response
			# Remove markdown code blocks if present
			import re
			json_match = re.search(r'```(?:json)?\s*(\[.*?\])\s*```', response_text, re.DOTALL)
			if json_match:
				response_text = json_match.group(1)

			result = json.loads(response_text)

			# Validate that result is a list
			if not isinstance(result, list):
				raise ValueError(f"Expected list response, got {type(result)}")

			for company_match in result:
				logger.debug(f"Match entry values", logo_url=company_match.get("company_logo_url"), company_name=company_match.get("company_name"), logo_element2=company_match.get("logo_element2"))

			return result

		except json.JSONDecodeError as e:
			logger.error(f"Failed to parse AI company search response as JSON", error=str(e), response=response_text[:500])
			raise ValueError(f"Failed to parse AI response as JSON: {str(e)}")
		except Exception as e:
			logger.error(f"Error during company search", company_id=company_id, error=str(e))
			raise

	def resume_rewrite(
		self,
		resume_html: str,
		job_desc: str,
		keyword_final: list,
		focus_final: list,
		job_title: str,
		position_title: str
	) -> dict:
		"""
		Rewrite a resume based on job description and keywords using AI.

		Args:
			resume_html: Original HTML resume content
			job_desc: Job description text
			keyword_final: List of final keywords to incorporate
			focus_final: List of focus areas to emphasize
			job_title: Target job title
			position_title: Current position title in resume

		Returns:
			Dictionary containing:
				- resume_html_rewrite: rewritten HTML resume

		Raises:
			ValueError: If AI response parsing fails
		"""
		# Load the prompt template
		prompt_template = self._load_prompt('resume_rewrite')

		# Format lists for the prompt
		keyword_final_str = "\n".join([f"- {kw}" for kw in keyword_final]) if keyword_final else "None"
		focus_final_str = "\n".join([f"- {focus}" for focus in focus_final]) if focus_final else "None"

		# Format the prompt with variables using replace to avoid issues with curly braces
		# Handle None values by converting to empty string
		prompt = prompt_template.replace('{resume_html}', resume_html or '')
		prompt = prompt.replace('{job_desc}', job_desc or '')
		prompt = prompt.replace('{keyword_final}', keyword_final_str)
		prompt = prompt.replace('{focus_final}', focus_final_str)
		prompt = prompt.replace('{job_title}', job_title or '')
		prompt = prompt.replace('{position_title}', position_title or '')

		# Log prompt size for debugging
		prompt_size = len(prompt)
		logger.debug(f"Resume rewrite prompt analysis",
					prompt_size=prompt_size,
					resume_size=len(resume_html or ''),
					job_desc_size=len(job_desc or ''),
					keywords_count=len(keyword_final),
					focus_count=len(focus_final))

		# Make API call to OpenAI with timing
		start_time = time.time()
		logger.debug(f"Starting OpenAI resume rewrite call", timestamp=start_time)

		try:
			logger.debug(f"Starting resume/rewrite AI call", llm=self.rewrite_llm)
			response = self.client.chat.completions.create(
				model=self.rewrite_llm,
				messages=[
					{"role": "system", "content": "Expert resume writer and career consultant. You rewrite resumes to optimize for specific job opportunities while maintaining authenticity and providing structured output in JSON format."},
					{"role": "user", "content": prompt}
				]
			)

			end_time = time.time()
			elapsed = end_time - start_time
			logger.info(f"OpenAI resume rewrite completed", elapsed_seconds=f"{elapsed:.2f}")

			# Log full OpenAI response details
			logger.debug(f"OpenAI Response ID: {response.id}")
			logger.debug(f"OpenAI Response Model: {response.model}")
			logger.debug(f"OpenAI Response Created: {response.created}")
			logger.debug(f"OpenAI Response Object: {response.object}")
			logger.debug(f"OpenAI Response Choices Count: {len(response.choices)}")
			if response.choices:
				logger.debug(f"OpenAI Response First Choice Finish Reason: {response.choices[0].finish_reason}")
				logger.debug(f"OpenAI Response First Choice Message Role: {response.choices[0].message.role}")
			if hasattr(response, 'usage') and response.usage:
				logger.debug(f"OpenAI Response Usage - Prompt Tokens: {response.usage.prompt_tokens}")
				logger.debug(f"OpenAI Response Usage - Completion Tokens: {response.usage.completion_tokens}")
				logger.debug(f"OpenAI Response Usage - Total Tokens: {response.usage.total_tokens}")
			if hasattr(response, 'system_fingerprint') and response.system_fingerprint:
				logger.debug(f"OpenAI Response System Fingerprint: {response.system_fingerprint}")

		except Exception as e:
			end_time = time.time()
			elapsed = end_time - start_time
			logger.error(f"OpenAI resume rewrite failed", elapsed_seconds=f"{elapsed:.2f}", error=str(e))
			raise

		# Extract the response content
		response_text = response.choices[0].message.content
		logger.debug(f"Resume rewrite response received", response_size=len(response_text))

		# Parse JSON response using robust helper
		try:
			required_keys = ['resume_html_rewrite']
			result = self._parse_json_response(response_text, required_keys)

			# Validate the structure
			if not all(key in result for key in required_keys):
				missing_keys = [key for key in required_keys if key not in result]
				logger.error(f"Response missing required keys", missing_keys=missing_keys, available_keys=list(result.keys()))
				raise ValueError(f"Response missing required keys: {missing_keys}. Available keys: {list(result.keys())}")

			# Set suggestion to empty list (feature disabled for now)
			result['suggestion'] = []

			return result

		except ValueError as e:
			# Log and re-raise with context
			logger.error(f"Failed to parse resume rewrite response", error=str(e), response_preview=response_text)
			raise

	def html_styling_diff(
		self,
		resume_markdown: str,
		resume_html_rewrite: str
	) -> dict:
		"""
		Convert markdown resume to HTML using the styling from an HTML rewrite,
		and generate a diff of text content changes.

		Args:
			resume_markdown: Original markdown resume content
			resume_html_rewrite: HTML rewritten resume to use for styling reference

		Returns:
			Dictionary containing:
				- new_html_file: HTML version of markdown with same styling as rewrite
				- text_changes: list of text differences between documents

		Raises:
			ValueError: If AI response parsing fails
		"""
		# Load the prompt template
		prompt_template = self._load_prompt('html_and_diff')

		# Format the prompt with variables using replace to avoid issues with curly braces
		prompt = prompt_template.replace('{resume_markdown}', resume_markdown or '')
		prompt = prompt.replace('{resume_html_rewrite}', resume_html_rewrite or '')

		# Make API call to OpenAI
		response = self.client.chat.completions.create(
			model=self.default_llm,
			messages=[
				{"role": "system", "content": "Expert HTML developer and diff analyzer. You convert markdown to HTML matching existing styling and identify text content differences in structured JSON format."},
				{"role": "user", "content": prompt}
			]
		)

		# Extract the response content
		response_text = response.choices[0].message.content

		# Debug: print the raw response
		print(f"DEBUG html_styling_diff: Raw OpenAI response length: {len(response_text)}", file=sys.stderr, flush=True)
		print(f"DEBUG html_styling_diff: First 500 chars: {repr(response_text[:500])}", file=sys.stderr, flush=True)

		# Parse JSON response
		try:
			# Try to parse the response as JSON with strict=False to handle invalid escapes
			result = json.loads(response_text, strict=False)

			# Validate the structure
			if not all(key in result for key in ['new_html_file', 'text_changes']):
				raise ValueError("Response missing required keys")

			return result

		except json.JSONDecodeError as e:
			# If JSON parsing fails, try to extract JSON from markdown code blocks
			import re
			print(f"DEBUG html_styling_diff: JSON parsing failed, trying markdown extraction", file=sys.stderr, flush=True)

			json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
			if json_match:
				try:
					extracted_json = json_match.group(1)
					print(f"DEBUG html_styling_diff: Extracted JSON length: {len(extracted_json)}", file=sys.stderr, flush=True)
					result = json.loads(extracted_json, strict=False)

					# Validate structure
					if not all(key in result for key in ['new_html_file', 'text_changes']):
						raise ValueError("Response missing required keys")

					return result
				except json.JSONDecodeError as e2:
					print(f"DEBUG html_styling_diff: Markdown extraction also failed: {str(e2)}", file=sys.stderr, flush=True)
					pass

			# Print more debug info
			print(f"DEBUG html_styling_diff: Full response:\n{response_text[:2000]}", file=sys.stderr, flush=True)
			raise ValueError(f"Failed to parse AI response as JSON: {str(e)}")

	def write_cover_letter(self, letter_tone: str, letter_length: str, instruction: str,
						  job_desc: str, company: str, job_title: str, resume_md_rewrite: str,
						  first_name: str, last_name: str, city: str, state: str,
						  email: str, phone: str) -> dict:
		"""
		Generate a cover letter using AI based on job details and resume.

		Args:
			letter_tone: Tone of the cover letter (professional, casual, enthusiastic, informational)
			letter_length: Length of the cover letter (short, medium, long)
			instruction: Additional instructions for cover letter generation
			job_desc: Job description text
			company: Company name
			job_title: Job position title
			resume_md_rewrite: Resume markdown content
			first_name: Applicant's first name
			last_name: Applicant's last name
			city: Applicant's city
			state: Applicant's state
			email: Applicant's email address
			phone: Applicant's phone number

		Returns:
			Dictionary containing:
				- letter_content: Generated cover letter in markdown format

		Raises:
			ValueError: If AI response cannot be parsed
		"""
		# Load the prompt template
		prompt_template = self._load_prompt('cover_letter')

		# Format the prompt with all variables
		prompt = prompt_template.replace('{letter_tone}', letter_tone)
		prompt = prompt.replace('{letter_length}', letter_length)
		prompt = prompt.replace('{instruction}', instruction or '')
		prompt = prompt.replace('{job_desc}', job_desc or '')
		prompt = prompt.replace('{company}', company or '')
		prompt = prompt.replace('{job_title}', job_title or '')
		prompt = prompt.replace('{resume_md_rewrite}', resume_md_rewrite or '')
		prompt = prompt.replace('{first_name}', first_name or '')
		prompt = prompt.replace('{last_name}', last_name or '')
		prompt = prompt.replace('{city}', city or '')
		prompt = prompt.replace('{state}', state or '')
		prompt = prompt.replace('{phone}', phone or '')
		prompt = prompt.replace('{email}', email or '')

		print(f"DEBUG write_cover_letter: Generating cover letter for {company} - {job_title}", file=sys.stderr, flush=True)

		# Make API call to OpenAI
		response = self.client.chat.completions.create(
			model=self.cover_llm,
			messages=[
				{"role": "system", "content": "You are a professional job finding coach that specializes in writing cover letters. You write personalized, compelling cover letters that highlight the candidate's strengths and match with the job requirements."},
				{"role": "user", "content": prompt}
			]
		)

		# Extract the response content
		response_text = response.choices[0].message.content

		print(f"DEBUG write_cover_letter: Received response from AI", file=sys.stderr, flush=True)

		# Parse JSON response
		try:
			# Try to parse the response as JSON
			result = json.loads(response_text)

			# Validate required key
			if 'letter_content' not in result:
				print(f"DEBUG write_cover_letter: Response missing 'letter_content' key. Available keys: {list(result.keys())}", file=sys.stderr, flush=True)
				raise ValueError(f"Response missing required key: 'letter_content'. Available keys: {list(result.keys())}")

			print(f"DEBUG write_cover_letter: Successfully parsed response", file=sys.stderr, flush=True)
			return result

		except json.JSONDecodeError as e:
			print(f"DEBUG write_cover_letter: JSON decode failed: {str(e)}", file=sys.stderr, flush=True)
			# If JSON parsing fails, try to extract JSON from markdown code blocks
			import re
			json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
			if json_match:
				try:
					result = json.loads(json_match.group(1))
					if 'letter_content' in result:
						print(f"DEBUG write_cover_letter: Successfully extracted from markdown", file=sys.stderr, flush=True)
						return result
				except json.JSONDecodeError as e2:
					print(f"DEBUG write_cover_letter: Markdown extraction also failed: {str(e2)}", file=sys.stderr, flush=True)
					pass

			# Print debug info
			print(f"DEBUG write_cover_letter: Full response:\n{response_text[:2000]}", file=sys.stderr, flush=True)
			raise ValueError(f"Failed to parse AI response as JSON: {str(e)}")

	def resume_rewrite_process(self, job_id: int, process_id: int, user_id: int) -> None:
		"""
		Background process to rewrite resume using AI.

		This method runs as a background task and performs the following operations:
		1. Retrieves the baseline resume and job details
		2. Uses AI to rewrite the resume based on job requirements
		3. Calculate and set other resume_detail data based on rewrite
		4. Update the resume_detail record with new values
		5. Generate suggestions for the resume
		6. Mark process as completed or failed

		Args:
			job_id: ID of the target job
			process_id: The primary key for the process DB record
		"""
		# Create a new database session for this background task
		db = SessionLocal()

		try:
			logger.info(f"Starting background process AI Agent resume rewrite process", job_id=job_id, process_id=process_id)

			# Step 1: Retrieve baseline resume data and verify it exists
			query = text("""
				SELECT jd.job_desc, jd.job_keyword, j.job_title, j.resume_id, rd.resume_html, rd.keyword_final,
					rd.focus_final, rd.position_title, rd.title_line_no, rd.baseline_score
				FROM job j
					JOIN job_detail jd ON (j.job_id = jd.job_id)
					JOIN resume_detail rd ON (j.resume_id = rd.resume_id)
				WHERE j.job_id = :job_id AND j.user_id = :user_id
			""")
			result = db.execute(query, {"job_id": job_id, "user_id": user_id}).first()

			if not result:
				logger.error(f"Job posting resume not found", job_id=job_id, process_id=process_id)
				self._mark_process_failed(db, process_id, "Job posting resume not found")
				return

			if not result.job_desc:
				logger.error(f"Job description is empty", job_id=job_id, process_id=process_id)
				self._mark_process_failed(db, process_id, "Job description is required")
				return
			logger.debug(f"Retrieved Job and Resume data successfully", resume_id=result.resume_id)

			# Step 2: Call AI to rewrite the resume
			logger.debug(f"Call AI Agent for resume rewrite")
			rewrite_result = self.resume_rewrite(
				resume_html=result.resume_html,
				job_desc=result.job_desc,
				keyword_final=result.keyword_final,
				focus_final=result.focus_final,
				job_title=result.job_title,
				position_title=result.position_title
			)

			logger.debug(f"AI rewrite completed", job_id=job_id, process_id=process_id)

			# Step 3: Calculate new rewrite_score using keyword matching
			# Import here to avoid circular dependency
			from ..api.resume import calculate_keyword_score
			rewrite_score = calculate_keyword_score(result.job_keyword, rewrite_result['resume_html_rewrite'])
			logger.debug(f"Calculated new rewrite_score", rewrite_score=rewrite_score, process_id=process_id)

			# Step 4: Update the existing resume_detail record with updated values
			update_query = text("""
				UPDATE resume_detail
				SET resume_html_rewrite = :resume_html_rewrite,
					rewrite_score       = :rewrite_score
				WHERE resume_id = :resume_id
			""")

			db.execute(update_query, {
				"resume_id": result.resume_id,
				"resume_html_rewrite": rewrite_result['resume_html_rewrite'],
				"rewrite_score": rewrite_score
			})
			db.commit()

			logger.log_database_operation("UPDATE", "resume_detail", result.resume_id)
			logger.debug(f"Updated resume_detail with HTML rewrite/score", resume_id=result.resume_id,
						rewrite_score=rewrite_score, process_id=process_id)

			# Step 5: Write HTML content to disk
			file_name_query = text("SELECT file_name FROM resume WHERE resume_id = :resume_id AND user_id = :user_id")
			file_name_result = db.execute(file_name_query, {"resume_id": result.resume_id, "user_id": user_id}).first()

			if file_name_result and file_name_result.file_name:
				try:
					resume_dir = Path(settings.resume_dir)
					resume_dir.mkdir(parents=True, exist_ok=True)

					html_file_path = resume_dir / file_name_result.file_name
					with open(html_file_path, 'w', encoding='utf-8') as f:
						f.write(rewrite_result['resume_html_rewrite'])

					logger.debug(f"HTML file written to disk", file_path=str(html_file_path), process_id=process_id)
				except Exception as e:
					# Log error but don't fail - HTML is already in database
					logger.warning(f"Failed to write HTML file to disk", error=str(e),
								   file_name=file_name_result.file_name, process_id=process_id)
			else:
				logger.warning(f"No file_name found for resume, HTML not written to disk",
							   resume_id=result.resume_id, process_id=process_id)

			# Step 6: Generate suggestions (synchronously since we're already in background)
			try:
				logger.debug(f"Generating resume suggestions", resume_id=result.resume_id, process_id=process_id)
				self.resume_suggestion(rewrite_result['resume_html_rewrite'], result.resume_id)
				logger.debug(f"Resume suggestions generated", resume_id=result.resume_id, process_id=process_id)
			except Exception as e:
				# Log error but don't fail the whole process
				logger.warning(f"Failed to generate suggestions", error=str(e), resume_id=result.resume_id, process_id=process_id)

			# Step 7: Mark process as completed
			update_process_query = text("UPDATE process SET completed = CURRENT_TIMESTAMP WHERE process_id = :process_id")
			db.execute(update_process_query, {"process_id": process_id})
			db.commit()

			logger.info(f"Resume rewrite process completed successfully", job_id=job_id, process_id=process_id)

		except Exception as e:
			logger.error(f"Error in resume rewrite process", job_id=job_id, process_id=process_id, error=str(e))
			self._mark_process_failed(db, process_id, str(e))

		finally:
			db.close()

	def _mark_process_failed(self, db: Session, process_id: int, error_message: str) -> None:
		"""Mark a process as failed in the database."""
		try:
			update_query = text("""
				UPDATE process
				SET failed = true,
					completed = CURRENT_TIMESTAMP
				WHERE process_id = :process_id
			""")
			db.execute(update_query, {"process_id": process_id})
			db.commit()
			logger.error(f"Process marked as failed", process_id=process_id, error=error_message)
		except Exception as e:
			logger.error(f"Failed to mark process as failed", process_id=process_id, error=str(e))
			db.rollback()

	def resume_suggestion(self, resume_html: str, resume_id: int) -> None:
		"""
		Generate improvement suggestions for a resume using AI and update the database.
		This method is designed to run in the background after the resume rewrite response.

		Args:
			resume_html: The HTML content of the resume to analyze
			resume_id: The resume_id to update with suggestions

		Returns:
			None (updates database directly)
		"""
		# Create a new database session for background task
		# (the request session is closed by the time this runs)
		db = SessionLocal()
		try:
			# Load the prompt template
			prompt_template = self._load_prompt('suggestion')

			# Format the prompt with the resume markdown
			prompt = prompt_template.replace('{resume_html}', resume_html)

			# Make API call to OpenAI
			response = self.client.chat.completions.create(
				model=self.default_llm,
				messages=[
					{"role": "system", "content": "Expert resume coach. You analyze resumes and provide actionable improvement suggestions in JSON format."},
					{"role": "user", "content": prompt}
				]
			)

			# Extract the response content
			response_text = response.choices[0].message.content

			if not response_text:
				print(f"ERROR resume_suggestion: OpenAI returned empty response for resume_id {resume_id}", file=sys.stderr, flush=True)
				return

			# Parse JSON response (expecting an array of strings)
			try:
				response_text = response_text.strip()
				suggestions = json.loads(response_text)

				# Validate it's a list
				if not isinstance(suggestions, list):
					print(f"ERROR resume_suggestion: Response is not a list for resume_id {resume_id}", file=sys.stderr, flush=True)
					return

				# Update the resume_detail record with suggestions
				update_query = text("""
					UPDATE resume_detail
					SET suggestion = :suggestion
					WHERE resume_id = :resume_id
				""")

				db.execute(update_query, {
					"resume_id": resume_id,
					"suggestion": suggestions
				})
				db.commit()

				print(f"DEBUG resume_suggestion: Successfully updated {len(suggestions)} suggestions for resume_id {resume_id}", file=sys.stderr, flush=True)

			except json.JSONDecodeError as e:
				# Try to extract JSON from markdown code blocks
				import re
				json_match = re.search(r'```(?:json)?\s*(\[.*?\])\s*```', response_text, re.DOTALL)
				if not json_match:
					# Try without code blocks
					json_match = re.search(r'(\[.*?\])', response_text, re.DOTALL)

				if json_match:
					try:
						suggestions = json.loads(json_match.group(1))
						if isinstance(suggestions, list):
							# Update database
							update_query = text("""
								UPDATE resume_detail
								SET suggestion = :suggestion
								WHERE resume_id = :resume_id
							""")

							db.execute(update_query, {
								"resume_id": resume_id,
								"suggestion": suggestions
							})
							db.commit()

							print(f"DEBUG resume_suggestion: Successfully updated {len(suggestions)} suggestions (from markdown) for resume_id {resume_id}", file=sys.stderr, flush=True)
							return
					except json.JSONDecodeError:
						pass

				print(f"ERROR resume_suggestion: Failed to parse AI response for resume_id {resume_id}: {str(e)}", file=sys.stderr, flush=True)
				print(f"ERROR resume_suggestion: Response text: {response_text[:1000]}", file=sys.stderr, flush=True)

		except Exception as e:
			# Catch all exceptions to prevent background task from crashing
			print(f"ERROR resume_suggestion: Unexpected error for resume_id {resume_id}: {str(e)}", file=sys.stderr, flush=True)
		finally:
			db.close()

	def company_research_process(self, company_id: int, process_id: int) -> None:
		"""
		Background process to research company using AI and generate comprehensive report.

		This method runs as a background task and performs the following operations:
		1. Retrieves company data along with related job and resume information
		2. Uses AI to generate a comprehensive company research report
		3. Updates the company record with the report HTML
		4. Marks process as completed or failed

		Args:
			company_id: ID of the company to research
			process_id: The primary key for the process DB record
		"""
		# Create a new database session for this background task
		# DO NOT use the request-scoped session - it keeps HTTP connection open
		db = SessionLocal()

		try:
			logger.info(f"Starting background company research process", company_id=company_id, process_id=process_id)

			# Retrieve company data with related job and resume information
			query = text("""
				SELECT c.company_name, c.website_url, c.linkedin_url, c.logo_file, jd.job_desc, rd.resume_html_rewrite
				FROM company c
					LEFT JOIN job j ON (c.job_id = j.job_id)
					LEFT JOIN job_detail jd ON (j.job_id = jd.job_id)
					LEFT JOIN resume_detail rd ON (j.resume_id = rd.resume_id)
				WHERE c.company_id = :company_id
			""")
			result = db.execute(query, {"company_id": company_id}).first()


			if not result:
				logger.error(f"Company not found", company_id=company_id, process_id=process_id)
				self._mark_process_failed(db, process_id, "Company not found")
				return



			company_name = result.company_name or ""
			website_url = result.website_url or ""
			linkedin_url = result.linkedin_url or ""
			job_desc = result.job_desc or ""
			resume_html_rewrite = result.resume_html_rewrite or ""
			logo_url = ""
			job_desc = result.job_desc or ""
			if result.logo_file:
				logo_url = settings.backend_url + "/logo/" + result.logo_file

			logger.debug(f"Retrieved company data", company_id=company_id, company_name=company_name)

			# Load the prompt template
			prompt_template = self._load_prompt('company_research')

			# Format the prompt with company information
			prompt = prompt_template.replace('{company_name}', company_name)
			prompt = prompt.replace('{linkedin_url}', linkedin_url)
			prompt = prompt.replace('{website_url}', website_url)
			prompt = prompt.replace('{logo_url}', logo_url)
			prompt = prompt.replace('{job_desc}', job_desc)
			prompt = prompt.replace('{resume_html_rewrite}', resume_html_rewrite)

			logger.info(f"Calling OpenAI for company research", company_id=company_id)

			# Make API call to OpenAI
			response = self.client.chat.completions.create(
				model=self.company_llm,
				messages=[
					{"role": "system", "content": "Expert company researcher and career coach. You create comprehensive company research report in HTML format to help job candidates prepare for interviews."},
					{"role": "user", "content": prompt}
				]
			)

			# Extract the response content
			response_text = response.choices[0].message.content.strip()
			logger.debug(f"AI company research response received", company_id=company_id, response_length=len(response_text))
			logger.debug(f"Response preview (first 500 chars)", preview=response_text[:500])

			# Check if response is HTML directly
			if response_text.strip().startswith('<'):
				logger.info(f"Response appears to be HTML directly, using as-is")
				report_html = response_text
				# Skip JSON parsing and save HTML directly
				update_query = text("""
					UPDATE company
					SET report_html = :report_html,
						report_created = CURRENT_TIMESTAMP
					WHERE company_id = :company_id
				""")
				db.execute(update_query, {
					"company_id": company_id,
					"report_html": report_html
				})
				db.commit()

				logger.info(f"Company report generated and saved", company_id=company_id, report_length=len(report_html))

				# Mark process as completed
				complete_query = text("""
					UPDATE process
					SET completed = CURRENT_TIMESTAMP
					WHERE process_id = :process_id
				""")
				db.execute(complete_query, {"process_id": process_id})
				db.commit()

				logger.info(f"Company research process completed successfully", company_id=company_id, process_id=process_id)
				return

			# Parse JSON response
			# Remove markdown code blocks if present
			import re
			json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
			if json_match:
				logger.debug(f"Found JSON in markdown code block")
				response_text = json_match.group(1)
			else:
				logger.debug(f"No JSON markdown block found, attempting to parse as JSON")

			result_data = json.loads(response_text)

			# Extract report HTML
			report_html = result_data.get('report', '')

			if not report_html:
				logger.error(f"No report content in AI response", company_id=company_id, process_id=process_id)
				self._mark_process_failed(db, process_id, "No report content generated")
				return

			# Update company record with report HTML and report_created timestamp
			update_query = text("""
				UPDATE company
				SET report_html = :report_html,
					report_created = CURRENT_TIMESTAMP
				WHERE company_id = :company_id
			""")
			db.execute(update_query, {
				"company_id": company_id,
				"report_html": report_html
			})
			db.commit()

			logger.info(f"Company report generated and saved", company_id=company_id, report_length=len(report_html))

			# Mark process as completed
			complete_query = text("""
				UPDATE process
				SET completed = CURRENT_TIMESTAMP
				WHERE process_id = :process_id
			""")
			db.execute(complete_query, {"process_id": process_id})
			db.commit()

			logger.info(f"Company research process completed successfully", company_id=company_id, process_id=process_id)

		except json.JSONDecodeError as e:
			logger.error(f"Failed to parse AI company research response", company_id=company_id, process_id=process_id, error=str(e))
			self._mark_process_failed(db, process_id, f"Failed to parse AI response: {str(e)}")
		except Exception as e:
			logger.error(f"Error during company research process", company_id=company_id, process_id=process_id, error=str(e))
			self._mark_process_failed(db, process_id, str(e))
		finally:
			db.close()


	def elevator_pitch(self, resume: str, job_desc: str) -> str:
		"""
		Write and elevator pitch based on resume and job description

		:param resume: str
		:param job_desc: str
		:return: pitch: str
		"""

		# Load the prompt template
		prompt_template = self._load_prompt('elevator_pitch')

		# Format the prompt with company information
		prompt = prompt_template.replace('{resume_html_rewrite}', resume)
		prompt = prompt.replace('{job_desc}', job_desc)

		logger.debug(f"Calling OpenAI for elevator pitch")

		# Make API call to OpenAI
		response = self.client.chat.completions.create(
			model=self.tools_llm,
			messages=[
				{"role": "system",
				 "content": "Expert resume coach. You use the job description and resume content to write a purpose built elevator pitch"},
				{"role": "user", "content": prompt}
			]
		)

		# Extract the response content and parse as JSON
		response_text = response.choices[0].message.content
		result = json.loads(response_text)

		return result

	def rewrite_blob(self, text_blob: str) -> dict:
		"""
		Rewrite a text blob to improve clarity, grammar, and professionalism.

		:param text_blob: str - The text to be rewritten
		:return: dict with new_text_blob and explanation
		"""

		# Load the prompt template
		prompt_template = self._load_prompt('rewrite_text_blob')

		# Format the prompt with the text blob
		prompt = prompt_template.replace('{text_blob}', text_blob)

		logger.debug(f"Calling OpenAI for text rewrite")

		# Make API call to OpenAI
		response = self.client.chat.completions.create(
			model=self.tools_llm,
			messages=[
				{"role": "system",
				 "content": "Expert writer and editor. You rewrite text to improve clarity, grammar, and professionalism while maintaining the original meaning."},
				{"role": "user", "content": prompt}
			]
		)

		# Extract the response content and parse as JSON
		response_text = response.choices[0].message.content
		result = json.loads(response_text)

		return result

	def company_culture_report(self, company_id: int, company_name: str, website_url: str, linkedin_url: str) -> str:
		"""
		Research company using AI and generate a report on the company culture

		This method runs the following operations:
		1. Uses AI to generate a company culture report
		2. Updates the company record with the culture report markdown
		3. Marks process as completed or failed

		Args:
			company_id: ID of the company to research
			company_name: Name of the company
			website_url: URL of the company's website
			linkedin_url: URL of the company's LinkedIn profile
		"""
		# Create a new database session for this background task
		db = SessionLocal()

		try:
			logger.info(f"Starting company culture report process", company_id=company_id)

			# Load the prompt template
			prompt_template = self._load_prompt('culture_report')

			# Format the prompt with company information
			prompt = prompt_template.replace('{company_name}', company_name)
			prompt = prompt.replace('{linkedin_url}', linkedin_url or "")
			prompt = prompt.replace('{website_url}', website_url or "")

			logger.info(f"Calling OpenAI for company culture report", company_id=company_id)

			# Make API call to OpenAI
			response = self.client.chat.completions.create(
				model=self.culture_llm,
				messages=[
					{"role": "system", "content": "Expert company researcher and career coach. You create comprehensive reports on company culture and guiding principals which is formatted using Markdown."},
					{"role": "user", "content": prompt}
				]
			)

			# Extract the response content
			response_text = response.choices[0].message.content.strip()
			result = json.loads(response_text)
			if not result or not result.get('culture_report'):
				logger.error(f"Empty value for culture report", company_id=company_id)
				raise ValueError("Failed to populate culture report from AI call")

			logger.info(f"Company culture report process completed successfully", company_id=company_id)
			return result.get('culture_report', '')

		except Exception as e:
			logger.error(f"Error during company culture report process", company_id=company_id, error=str(e))
			return "Error"
		finally:
			db.close()

	def interview_questions(self, job_id: int, company_id: int, user_id: int) -> List[{str, str}]:
		"""
		This method makes the AI call to create a question list for use with an interview.

		:param job_id: The job associated with this interview
		:param company_id:
		:param user_id:
		:return:
		"""
		try:
			logger.debug(f"Starting AIAgent call for interview questions", company_id=company_id, job_id=job_id, user_id=user_id)

			db = SessionLocal()

			# Retrieve the data to feed to the OpenAI call
			query = text("""
				SELECT jd.job_desc, c.culture_report, rd.resume_md_rewrite 
				FROM job j JOIN job_detail jd ON (j.job_id=jd.job_id) JOIN company c ON (jd.job_id=c.job_id) JOIN resume_detail rd ON (j.resume_id=rd.resume_id) 
				WHERE j.job_id = :job_id AND j.user_id = :user_id
				""")
			result = db.execute(query, {"job_id": job_id, "user_id": user_id}).first()
			if not result:
				logger.error(f"Failed retrieving data for prompt call", company_id=company_id)
				raise ValueError("Failed retrieving data for prompt call")

			if not result.job_desc or not result.culture_report or not result.resume_md_rewrite:
				logger.error(f"Missing at least one of: job_desc, culture_report, resume_md_rewrite", job_id=job_id)
				raise ValueError("Failed retrieving data for questions call prompt")

			# Load the prompt template
			prompt_template = self._load_prompt('interview_questions')

			# Format the prompt with company information
			prompt = prompt_template.replace('{job_desc}', result.job_desc)
			prompt = prompt.replace('{culture_report}', result.culture_report)
			prompt = prompt.replace('{resume_md_rewrite}', result.resume_md_rewrite)

			logger.info(f"Calling OpenAI for interview question generation", company_id=company_id)

			# Make API call to OpenAI
			response = self.client.chat.completions.create(
				model=self.question_llm,
				messages=[
					{"role": "system",
					 "content": "Hiring manager for company. You write interview questions to use for an upcoming interview."},
					{"role": "user", "content": prompt}
				],
				response_format={"type": "json_object"}
			)

			# Extract the response content
			response_text = response.choices[0].message.content.strip()
			logger.debug(f"Raw AI response for interview questions", response_length=len(response_text), response_preview=response_text[:500])

			if not response_text:
				raise ValueError("Empty response from OpenAI for interview questions")

			result = json.loads(response_text)
			return result['questions']
		except Exception as e:
			logger.error(f"Error during AIAgent call for interview questions process", company_id=company_id, job_id=job_id, error=str(e))
			raise


	def interview_answer(self, interview_id: int, question: str, answer: str, answer_note: str, p_question: str, p_answer: str, p_answer_note: str) -> {str, str}:
		"""
		This method makes an AI call that will process an answer to a question and score it

		:param interview_id: The primary key for the interview record
		:param question: The text for the question asked
		:param answer: The text for the answer given
		:param answer_note: Guidance on handling the answer
		:param p_question: The parent question
		:param p_answer: the parent question answer
		:param p_answer_note: the parent question answer note
		:return:
		"""
		db = SessionLocal()

		followup = None
		followup_answer = None
		followup_answer_note = None

		# check if parent question was passed
		if p_question:
			followup = question
			followup_answer = answer
			followup_answer_note = answer_note
			question = p_question
			answer = p_answer
			answer_note = p_answer_note


		# Retrieve the data to feed to the OpenAI call
		query = text("""
			SELECT jd.job_desc, c.culture_report, rd.resume_md_rewrite 
			FROM interview i 
			    JOIN job j ON (i.job_id=j.job_id) 
                JOIN job_detail jd ON (i.job_id=jd.job_id) 
                JOIN company c ON (i.company_id=c.company_id) 
                JOIN resume_detail rd ON (j.resume_id=rd.resume_id) 
			WHERE i.interview_id = :interview_id
			""")
		result = db.execute(query, {"interview_id": interview_id}).first()
		if not result:
			logger.error(f"Failed retrieving data for interview questions process", interview_id=interview_id)
			return None

		# Load the prompt template
		prompt_template = self._load_prompt('interview_answer')

		# Format the prompt with company information
		prompt = prompt_template.replace('{job_desc}', result.job_desc)
		prompt = prompt.replace('{culture_report}', result.culture_report)
		prompt = prompt.replace('{resume_md_rewrite}', result.resume_md_rewrite)
		prompt = prompt.replace('{question}', question)
		prompt = prompt.replace('{answer}', answer)
		prompt = prompt.replace('{answer_note}', answer_note)
		prompt = prompt.replace('{followup}', followup)
		prompt = prompt.replace('{followup_answer}', followup_answer)
		prompt = prompt.replace('{followup_answer_note}', followup_answer_note)

		logger.info(f"Calling OpenAI for interview question answer evaluation", interview_id=interview_id)

		# Make API call to OpenAI
		response = self.client.chat.completions.create(
			model=self.question_llm,
			messages=[
				{"role": "system",
				 "content": "Hiring manager for company. You evaluate an answer to a interview question and provide scoring and feedback."},
				{"role": "user", "content": prompt}
			],
			response_format={"type": "json_object"}
		)

		# Extract the response content
		response_text = response.choices[0].message.content.strip()
		ai_result = json.loads(response_text)

		logger.info(f"Completed the AI call to create questions", response=ai_result[:500])

		return ai_result

	def review_interview(self, interview_id: int, summary_report: str) -> {str, str}:
		logger.info(f"Starting AI call to give interview assessment", interview_id=interview_id)

		db = SessionLocal()
		# Retrieve the data to feed to the OpenAI call
		query = text("""
             SELECT jd.job_desc, c.culture_report, rd.resume_md_rewrite
             FROM interview i
                  JOIN job j ON (i.job_id = j.job_id)
                  JOIN job_detail jd ON (j.job_id = jd.job_id)
                  JOIN company c ON (i.company_id = c.company_id)
                  JOIN resume_detail rd ON (j.resume_id = rd.resume_id)
             WHERE i.interview_id = :interview_id
         """)
		result = db.execute(query, {"interview_id": interview_id}).first()
		if not result:
			logger.error(f"Failed retrieving data for interview review assessment", interview_id=interview_id)
			return None

		# Load the prompt template
		prompt_template = self._load_prompt('interview_review')

		# Format the prompt with company information
		prompt = prompt_template.replace('{job_desc}', result.job_desc)
		prompt = prompt.replace('{culture_report}', result.culture_report)
		prompt = prompt.replace('{resume_md_rewrite}', result.resume_md_rewrite)
		prompt = prompt.replace('{summary_report}', summary_report)

		logger.info(f"Calling OpenAI for interview question answer evaluation", interview_id=interview_id)

		# Make API call to OpenAI
		response = self.client.chat.completions.create(
			model=self.question_llm,
			messages=[
				{"role": "system",
				 "content": "Hiring manager for technology company. Review candidate interview notes and provide scoring and feedback."},
				{"role": "user", "content": prompt}
			],
			response_format={"type": "json_object"}
		)

		# Extract the response content
		response_text = response.choices[0].message.content.strip()
		ai_result = json.loads(response_text)

		return ai_result





