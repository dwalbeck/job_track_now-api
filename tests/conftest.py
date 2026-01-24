import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.core.database import get_db
import tempfile
import os
from pathlib import Path


# Test database URL - use PostgreSQL to match production
# Note: This requires a test PostgreSQL database to be available
TEST_DATABASE_URL = "postgresql://apiuser:change_me@psql.jobtracknow.com:5432/jobtracker_test"


@pytest.fixture(scope="session")
def test_engine():
    """Create a test database engine."""
    # For PostgreSQL, we don't need check_same_thread
    engine = create_engine(TEST_DATABASE_URL)

    # Create test database tables if they don't exist
    from app.models.models import Base
    Base.metadata.create_all(bind=engine)

    yield engine

    # Cleanup
    engine.dispose()


@pytest.fixture(scope="function")
def test_db(test_engine):
    """Create a fresh database session for each test."""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    # Create a session
    session = TestingSessionLocal()

    # Clean all tables before each test in correct order (respecting foreign keys)
    try:
        session.execute(text("TRUNCATE TABLE communication, document, note, calendar, job_contact, contact, cover_letter, resume_detail, job_detail, resume, job, process, personal, company, user_setting, user_address, user_detail, address RESTART IDENTITY CASCADE"))
        # Don't truncate users - just delete non-test users
        session.execute(text("DELETE FROM users WHERE login != 'testuser'"))
        session.commit()
    except Exception as e:
        session.rollback()
        # Tables might not exist yet, ignore errors
        pass

    # Insert test user (use INSERT ... ON CONFLICT to handle duplicates)
    session.execute(text("""
        INSERT INTO users (first_name, last_name, login, passwd, email, is_admin)
        VALUES ('Test', 'User', 'testuser', 'testpass', 'test@example.com', false)
        ON CONFLICT DO NOTHING
    """))
    session.commit()

    # Get the test user's ID
    user_result = session.execute(text("SELECT user_id FROM users WHERE login = 'testuser'")).first()
    test_user_id = user_result.user_id if user_result else 1

    # Insert test user settings
    session.execute(text("""
        INSERT INTO user_setting (user_id, no_response_week,
                            default_llm, resume_extract_llm, job_extract_llm, rewrite_llm, cover_llm, company_llm, tools_llm,
                            docx2html, odt2html, pdf2html,
                            html2docx, html2odt, html2pdf)
        VALUES (:user_id, 6,
                'gpt-4.1-mini', 'gpt-4.1-mini', 'gpt-4.1-mini', 'gpt-4.1-mini', 'gpt-4.1-mini', 'gpt-4.1-mini', 'gpt-4.1-mini',
                'docx-parser-converter', 'pandoc', 'markitdown',
                'html4docx', 'pandoc', 'weasyprint')
        ON CONFLICT (user_id) DO NOTHING
    """), {"user_id": test_user_id})

    # Insert test user detail
    session.execute(text("""
        INSERT INTO user_detail (user_id, phone, linkedin_url, github_url, website_url, portfolio_url)
        VALUES (:user_id, '(555) 123-4567', NULL, NULL, NULL, NULL)
        ON CONFLICT (user_id) DO NOTHING
    """), {"user_id": test_user_id})
    session.commit()

    yield session

    # Cleanup
    session.rollback()
    session.close()


@pytest.fixture(scope="function")
def client(test_db):
    """Create a test client with database override."""
    def override_get_db():
        try:
            yield test_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_files(temp_dir):
    """Create sample test files."""
    files = {}

    # Create a simple text file
    txt_file = temp_dir / "test.txt"
    txt_file.write_text("This is a test document.")
    files['txt'] = str(txt_file)

    # Create a simple markdown file
    md_file = temp_dir / "test.md"
    md_file.write_text("# Test Document\n\nThis is a test.")
    files['md'] = str(md_file)

    # Create a simple HTML file
    html_file = temp_dir / "test.html"
    html_file.write_text("""<!DOCTYPE html>
<html>
<head><title>Test</title></head>
<body><h1>Test Document</h1><p>This is a test.</p></body>
</html>""")
    files['html'] = str(html_file)

    return files
