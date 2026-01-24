from typing import List, Union
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
	# Pydantic v2 configuration
	model_config = SettingsConfigDict(
		env_file=".env",
		env_file_encoding='utf-8',
		case_sensitive=False,
		extra='ignore'  # Allow extra fields from .env without raising errors
	)

	# Application Configuration
	app_name: str = "Job Track Now"
	app_version: str = "1.0.0"
	debug: bool = False

	# Database configuration
	database_url: str
	postgres_host: str
	postgres_user: str
	postgres_password: str
	postgres_db: str
	postgres_port: int = 5432

	# File storage configuration
	base_job_file_path: str
	resume_dir: str
	cover_letter_dir: str
	export_dir: str
	logo_dir: str
	report_dir: str

	backend_url: str

	# Logging configuration
	log_level: str = "INFO"
	log_file: str = "app.log"

	# CORS - Handle both string and list formats
	allowed_origins: Union[List[str], str] = "*"

	# AI Configuration
	openai_api_key: str = ""
	openai_project: str = ""

	# LLM Settings from database (defaults)
	default_llm: str = "gpt-4.1-mini"
	resume_extract_llm: str = "gpt-5.2"
	job_extract_llm: str = "gpt-4.1-mini"
	rewrite_llm: str = "gpt-4.1-mini"
	cover_llm: str = "gpt-4.1-mini"
	company_llm: str = "gpt-4.1-mini"
	tools_llm: str = "gpt-4.1-mini"

	def get_allowed_origins(self) -> List[str]:
		if isinstance(self.allowed_origins, str):
			# Handle string format from environment variable
			import json
			try:
				return json.loads(self.allowed_origins)
			except json.JSONDecodeError:
				# Fallback to single origin
				return [self.allowed_origins]
		return self.allowed_origins

	def load_llm_settings_from_db(self, db, user_id: int = None):
		"""
		Load LLM settings and API keys from the user_setting table in the database.
		Updates the settings object with the database values if they exist.

		Args:
			db: Database session
			user_id: The user's ID. If None, uses the first user found.
		"""
		from sqlalchemy import text
		try:
			if not user_id:
				# Get first user if no user_id provided
				user_query = text("SELECT user_id FROM users ORDER BY user_id LIMIT 1")
				user_result = db.execute(user_query).first()
				if user_result:
					user_id = user_result.user_id
				else:
					return  # No users, use defaults

			query = text("""
				SELECT default_llm, job_extract_llm, rewrite_llm, cover_llm, resume_extract_llm, company_llm, tools_llm, openai_api_key
				FROM user_setting
				WHERE user_id = :user_id
			""")
			result = db.execute(query, {"user_id": user_id}).first()

			if result:
				if result.default_llm:
					self.default_llm = result.default_llm
				if result.job_extract_llm:
					self.job_extract_llm = result.job_extract_llm
				if result.rewrite_llm:
					self.rewrite_llm = result.rewrite_llm
				if result.cover_llm:
					self.cover_llm = result.cover_llm
				if result.resume_extract_llm:
					self.resume_extract_llm = result.resume_extract_llm
				if result.company_llm:
					self.company_llm = result.company_llm
				if result.tools_llm:
					self.tools_llm = result.tools_llm
				if result.openai_api_key:
					self.openai_api_key = result.openai_api_key
		except Exception:
			# If there's an error querying the DB, use defaults
			pass


settings = Settings()
