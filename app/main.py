from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .core.config import settings
from .api import jobs, contacts, calendar, notes, resume, convert, personal, letter, files, reminder, export, process, company, openai_api, tools, oauth, user
from .middleware import LoggingMiddleware, JWTAuthMiddleware
from .utils.logger import logger

app = FastAPI(
	title=settings.app_name,
	version=settings.app_version,
	debug=settings.debug
)


# Exception handlers for logging all failures
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
	"""
	Handler for request validation errors (422 errors).
	Logs validation errors in detail for debugging.
	"""
	error_details = exc.errors()
	logger.error(
		"Request validation failed",
		method=request.method,
		path=str(request.url.path),
		errors=error_details,
		body=await request.body() if request.method in ["POST", "PUT", "PATCH"] else None
	)

	return JSONResponse(
		status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
		content={
			"detail": error_details,
			"body": str(await request.body()) if request.method in ["POST", "PUT", "PATCH"] else None
		},
		headers={
			"Access-Control-Allow-Origin": "*",
			"Access-Control-Allow-Credentials": "true",
		}
	)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
	"""
	Handler for HTTP exceptions.
	Logs all HTTP errors (4xx, 5xx).
	"""
	logger.error(
		f"HTTP {exc.status_code} error",
		method=request.method,
		path=str(request.url.path),
		status_code=exc.status_code,
		detail=exc.detail
	)

	return JSONResponse(
		status_code=exc.status_code,
		content={"detail": exc.detail},
		headers={
			"Access-Control-Allow-Origin": "*",
			"Access-Control-Allow-Credentials": "true",
		}
	)


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
	"""
	Handler for unhandled exceptions.
	Logs all unexpected errors.
	"""
	logger.error(
		"Unhandled exception",
		method=request.method,
		path=str(request.url.path),
		error=str(exc),
		error_type=type(exc).__name__
	)

	return JSONResponse(
		status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
		content={"detail": "Internal server error", "error": str(exc)},
		headers={
			"Access-Control-Allow-Origin": "*",
			"Access-Control-Allow-Credentials": "true",
		}
	)


# CORS middleware (must be added before logging middleware to ensure headers are added first)
app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],  # Allow all origins
	allow_credentials=False,
	allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],  # Explicit methods
	allow_headers=["*"],  # Allow all headers
	expose_headers=["*"],  # Expose all headers
	max_age=0,  # Disable preflight caching for debugging
)

# Add logging middleware (must be added after CORS for proper request/response logging)
app.add_middleware(LoggingMiddleware)

# Add JWT authentication middleware (validates tokens on all requests except excluded paths)
# Excluded paths are defined in JWTAuthMiddleware: OAuth endpoints, health check, root, API docs
app.add_middleware(JWTAuthMiddleware)

# Include routers
# OAuth routes (no authentication required)
app.include_router(oauth.router, prefix="/v1", tags=["oauth"])

# Protected routes
app.include_router(calendar.router, prefix="/v1", tags=["calendar"])
app.include_router(company.router, prefix="/v1", tags=["company"])
app.include_router(contacts.router, prefix="/v1", tags=["contacts"])
app.include_router(convert.router, prefix="/v1", tags=["convert"])
app.include_router(export.router, prefix="/v1", tags=["export"])
app.include_router(files.router, prefix="/v1", tags=["files"])
app.include_router(jobs.router, prefix="/v1", tags=["jobs"])
app.include_router(letter.router, prefix="/v1", tags=["letter"])
app.include_router(openai_api.router, prefix="/v1", tags=["openai"])
app.include_router(notes.router, prefix="/v1", tags=["notes"])
app.include_router(personal.router, prefix="/v1", tags=["personal"])
app.include_router(process.router, prefix="/v1/process", tags=["process"])
app.include_router(reminder.router, prefix="/v1", tags=["reminder"])
app.include_router(resume.router, prefix="/v1", tags=["resume"])
app.include_router(tools.router, prefix="/v1/tools", tags=["tools"])
app.include_router(user.router, prefix="/v1", tags=["user"])

@app.get("/")
async def root():
	logger.info("Root endpoint accessed")
	return {"message": "Job Track Now API", "version": settings.app_version}


@app.get("/health")
async def health_check():
	#logger.debug("Health check endpoint accessed")
	return {"status": "healthy"}