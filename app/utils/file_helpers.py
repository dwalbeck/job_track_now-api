import os
import re
import shutil
import mimetypes
from sqlalchemy.orm import Session
from sqlalchemy import text
from openai import OpenAI
from .logger import logger
from .user_helper import get_user_name
from ..models.models import Resume
from ..core.database import get_db, SessionLocal
from ..core.config import settings


def change_filename(orig: str, filename: str) -> str:
    parts = orig.rsplit('.', 1)
    ret_file = f"{filename}.{parts[0]}"
    return ret_file


def change_file_extension(filename: str, middle: str, extension: str) -> str:
    parts = filename.rsplit('.', 1)
    file = parts[0]
    if middle:
        file = file + middle
    file = file + '.' + extension
    return file


def set_filename(company: str, title: str, mimetype: str) -> str:
    """
    This will create a filename using the values from the company name and job title

    :param company: Company name
    :param title: Job position title
    :param mimetype: File format as the file extension to use
    :return: filename with extension
    """

    file_tmp = company.strip() + '-' + title.strip()
    # Replace spaces with underscores first
    file_tmp = file_tmp.replace(' ', '_')
    # Remove any non-alphanumeric characters except underscores and hyphens
    file_tmp = re.sub(r'[^a-zA-Z0-9_\-\.]', '', file_tmp)
    filename = file_tmp + '.' + mimetype
    return filename.lower()

def make_unique_resume_filename(base_filename: str, db: Session, user_id: int) -> str:
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
    date_stamp = datetime.utcnow().strftime('%Y%m%d')
    timestamped_name = f"{base_name}-{date_stamp}.{extension}" if extension else f"{base_name}_{date_stamp}"

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


def get_file_extension(file_path: str) -> str:
    """
    Get the file extension from a file path.

    Args:
        file_path: Path to the file

    Returns:
        File extension including the dot (e.g., '.pdf', '.docx')
    """
    return os.path.splitext(file_path)[1]


def get_mime_type(file_path: str) -> str:
    """
    Get the MIME type for a file based on its extension.

    Args:
        file_path: Path to the file

    Returns:
        MIME type string (e.g., 'application/pdf')
    """
    mime_type, _ = mimetypes.guess_type(file_path)
    return mime_type or 'application/octet-stream'


def create_standardized_download_file(
    source_file_path: str,
    file_type: str,
    db: Session,
    user_id: int
) -> tuple[str, str, str]:
    """
    Copy a file to /tmp with standardized naming for download.

    Args:
        source_file_path: Original file path
        file_type: Either 'resume' or 'cover_letter'
        db: Database session
        user_id: The user's ID (required)

    Returns:
        Tuple of (tmp_file_path, download_filename, mime_type)

    Raises:
        ValueError: If user_id is not provided
    """
    if not user_id:
        raise ValueError("user_id is required")

    # Get user's name
    full_name = get_user_name(db, user_id)
    logger.debug(f"In file_helpers.py:", full_name=full_name)
    name_part = f"{full_name}".lower().replace(" ", "_")
    extension = get_file_extension(source_file_path)

    # Create download filename
    if file_type == 'resume':
        download_filename = f"resume-{name_part}{extension}"
    elif file_type == 'cover_letter':
        extension = '.docx'
        download_filename = f"cover_letter-{name_part}{extension}"
    elif file_type == 'audio':
        # combine interview_id and question_id for name of file
        path_part = source_file_path.split('/')
        download_filename = f"{path_part[-2]}-{path_part[-1]}"
    else:
        download_filename = f"{file_type}-{name_part}{extension}"

    # Create temp file path
    tmp_file_path = os.path.join('/tmp', download_filename)

    # Copy file to tmp
    try:
        shutil.copy2(source_file_path, tmp_file_path)
        logger.info(f"Created standardized download file",
                   source=source_file_path,
                   temp=tmp_file_path,
                   download_name=download_filename)
    except Exception as e:
        logger.error(f"Error copying file to tmp",
                    source=source_file_path,
                    error=str(e))
        raise

    # Get MIME type
    mime_type = get_mime_type(source_file_path)

    return (tmp_file_path, download_filename, mime_type)

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
            logger.error(f"Failed to retrieve interview questions", interview_id=interview_id, user_id=user_id, query=query)
            return False

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

def get_tts_audio(question_id: int, interview_id: int, text_str: str, statement: bool) -> str:
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


