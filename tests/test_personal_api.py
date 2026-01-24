import pytest
from sqlalchemy import text


class TestGetPersonalInfo:
    """Test suite for GET /v1/personal endpoint."""

    def test_get_personal_info_existing_record(self, client, test_db):
        """Test retrieving existing personal information."""
        response = client.get("/v1/personal")

        assert response.status_code == 200
        data = response.json()

        # Check default test data from conftest.py
        assert data['first_name'] == 'Test'
        assert data['last_name'] == 'User'
        assert data['docx2html'] == 'docx-parser-converter'
        assert data['odt2html'] == 'pandoc'
        assert data['pdf2html'] == 'markitdown'
        assert data['html2docx'] == 'html4docx'
        assert data['html2odt'] == 'pandoc'
        assert data['html2pdf'] == 'weasyprint'

    def test_get_personal_info_no_record(self, client, test_db):
        """Test retrieving personal info when no user exists."""
        # Delete the test user and related data
        test_db.execute(text("DELETE FROM user_setting"))
        test_db.execute(text("DELETE FROM user_detail"))
        test_db.execute(text("DELETE FROM user_address"))
        test_db.execute(text("DELETE FROM users"))
        test_db.commit()

        response = client.get("/v1/personal")

        assert response.status_code == 200
        data = response.json()

        # Should return empty strings and defaults
        assert data['first_name'] == ''
        assert data['last_name'] == ''
        assert data['email'] == ''
        assert data['phone'] == ''
        assert data['no_response_week'] == 6
        assert data['resume_extract_llm'] == 'gpt-4.1-mini'
        assert data['job_extract_llm'] == 'gpt-4.1-mini'
        assert data['rewrite_llm'] == 'gpt-4.1-mini'
        assert data['cover_llm'] == 'gpt-4.1-mini'
        assert data['company_llm'] == 'gpt-4.1-mini'

    def test_get_personal_info_with_all_fields(self, client, test_db):
        """Test retrieving personal info with all fields populated."""
        # Get the test user ID
        user_result = test_db.execute(text("SELECT user_id FROM users WHERE login = 'testuser'")).first()
        user_id = user_result.user_id

        # Update user details
        test_db.execute(text("""
            UPDATE user_detail
            SET phone = '5551234567',
                linkedin_url = 'https://linkedin.com/in/testuser',
                github_url = 'https://github.com/testuser',
                website_url = 'https://testuser.com',
                portfolio_url = 'https://portfolio.testuser.com'
            WHERE user_id = :user_id
        """), {"user_id": user_id})

        # Create address and link to user
        test_db.execute(text("""
            INSERT INTO address (address_1, address_2, city, state, zip, country)
            VALUES ('123 Main St', 'Apt 4', 'Test City', 'CA', '12345', 'USA')
            ON CONFLICT (address_1, address_2, city, state, zip) DO NOTHING
        """))
        addr_result = test_db.execute(text("""
            SELECT address_id FROM address WHERE address_1 = '123 Main St'
        """)).first()
        test_db.execute(text("""
            INSERT INTO user_address (user_id, address_id, is_default, address_type)
            VALUES (:user_id, :address_id, true, 'home')
            ON CONFLICT (user_id, address_id) DO UPDATE SET is_default = true
        """), {"user_id": user_id, "address_id": addr_result.address_id})

        # Update settings
        test_db.execute(text("""
            UPDATE user_setting
            SET no_response_week = 6,
                resume_extract_llm = 'gpt-4o',
                job_extract_llm = 'gpt-4o',
                rewrite_llm = 'gpt-4o',
                cover_llm = 'gpt-4o',
                company_llm = 'gpt-4o',
                openai_api_key = 'sk-test123',
                tinymce_api_key = 'tinymce-test',
                convertapi_key = 'convert-test'
            WHERE user_id = :user_id
        """), {"user_id": user_id})
        test_db.commit()

        response = client.get("/v1/personal")

        assert response.status_code == 200
        data = response.json()

        assert data['phone'] == '5551234567'
        assert data['linkedin_url'] == 'https://linkedin.com/in/testuser'
        assert data['github_url'] == 'https://github.com/testuser'
        assert data['website_url'] == 'https://testuser.com'
        assert data['portfolio_url'] == 'https://portfolio.testuser.com'
        assert data['address_1'] == '123 Main St'
        assert data['address_2'] == 'Apt 4'
        assert data['city'] == 'Test City'
        assert data['state'] == 'CA'
        assert data['zip'] == '12345'
        assert data['country'] == 'USA'
        assert data['no_response_week'] == 6
        assert data['resume_extract_llm'] == 'gpt-4o'
        assert data['job_extract_llm'] == 'gpt-4o'
        assert data['rewrite_llm'] == 'gpt-4o'
        assert data['cover_llm'] == 'gpt-4o'
        assert data['company_llm'] == 'gpt-4o'
        assert data['openai_api_key'] == 'sk-test123'
        assert data['tinymce_api_key'] == 'tinymce-test'
        assert data['convertapi_key'] == 'convert-test'


class TestSavePersonalInfo:
    """Test suite for POST /v1/personal endpoint."""

    def test_save_personal_info_create_new(self, client, test_db):
        """Test creating new user information."""
        # Delete existing users and related data
        test_db.execute(text("DELETE FROM user_setting"))
        test_db.execute(text("DELETE FROM user_detail"))
        test_db.execute(text("DELETE FROM user_address"))
        test_db.execute(text("DELETE FROM users"))
        test_db.commit()

        personal_data = {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john.doe@example.com",
            "phone": "5551234567",
            "linkedin_url": "https://linkedin.com/in/johndoe",
            "github_url": "https://github.com/johndoe",
            "website_url": "",
            "portfolio_url": "",
            "address_1": "456 Oak Ave",
            "address_2": "",
            "city": "San Francisco",
            "state": "CA",
            "zip": "94105",
            "country": "USA",
            "no_response_week": 5,
            "resume_extract_llm": "gpt-4o-mini",
            "job_extract_llm": "gpt-4o-mini",
            "rewrite_llm": "gpt-4o-mini",
            "cover_llm": "gpt-4o-mini",
            "company_llm": "gpt-4o-mini",
            "openai_api_key": "sk-new-key",
            "tinymce_api_key": "tinymce-new",
            "convertapi_key": "convert-new",
            "docx2html": "mammoth",
            "odt2html": "pandoc",
            "pdf2html": "markitdown",
            "html2docx": "html4docx",
            "html2odt": "pandoc",
            "html2pdf": "weasyprint"
        }

        response = client.post("/v1/personal", json=personal_data)

        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "success"
        assert "user_id" in result

        # Verify data was saved
        user_result = test_db.execute(text("SELECT * FROM users")).first()
        assert user_result.first_name == "John"
        assert user_result.last_name == "Doe"
        assert user_result.email == "john.doe@example.com"

        detail_result = test_db.execute(text("SELECT * FROM user_detail")).first()
        assert detail_result.phone == "(555) 123-4567"  # Should be formatted

        settings_result = test_db.execute(text("SELECT * FROM user_setting")).first()
        assert settings_result.no_response_week == 5

    def test_save_personal_info_update_existing(self, client, test_db):
        """Test updating existing user information."""
        personal_data = {
            "first_name": "Jane",
            "last_name": "Smith",
            "email": "jane.smith@example.com",
            "phone": "4155551234",
            "linkedin_url": "https://linkedin.com/in/janesmith",
            "github_url": "",
            "website_url": "",
            "portfolio_url": "",
            "address_1": "789 Pine St",
            "address_2": "Suite 200",
            "city": "Oakland",
            "state": "CA",
            "zip": "94612",
            "country": "USA",
            "no_response_week": 3,
            "resume_extract_llm": "gpt-4o",
            "job_extract_llm": "gpt-4o",
            "rewrite_llm": "gpt-4o",
            "cover_llm": "gpt-4o",
            "company_llm": "gpt-4o",
            "openai_api_key": "sk-updated",
            "tinymce_api_key": "tinymce-updated",
            "convertapi_key": "convert-updated",
            "docx2html": "docx-parser-converter",
            "odt2html": "pandoc",
            "pdf2html": "markitdown",
            "html2docx": "python-docx",
            "html2odt": "pandoc",
            "html2pdf": "weasyprint"
        }

        response = client.post("/v1/personal", json=personal_data)

        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "success"

        # Verify data was updated
        user_result = test_db.execute(text("SELECT * FROM users")).first()
        assert user_result.first_name == "Jane"
        assert user_result.last_name == "Smith"
        assert user_result.email == "jane.smith@example.com"

        detail_result = test_db.execute(text("SELECT * FROM user_detail")).first()
        assert detail_result.phone == "(415) 555-1234"  # Should be formatted

        settings_result = test_db.execute(text("SELECT * FROM user_setting")).first()
        assert settings_result.no_response_week == 3
        assert settings_result.html2docx == "python-docx"

    def test_save_personal_info_phone_formatting(self, client, test_db):
        """Test phone number formatting."""
        test_cases = [
            ("5551234567", "(555) 123-4567"),
            ("(555) 123-4567", "(555) 123-4567"),
            ("555-123-4567", "(555) 123-4567"),
            ("555.123.4567", "(555) 123-4567"),
            ("15551234567", "+1 (555) 123-4567"),  # With country code
        ]

        for input_phone, expected_phone in test_cases:
            personal_data = {
                "first_name": "Test",
                "last_name": "User",
                "email": "test@example.com",
                "phone": input_phone,
                "linkedin_url": "",
                "github_url": "",
                "website_url": "",
                "portfolio_url": "",
                "address_1": "",
                "address_2": "",
                "city": "",
                "state": "",
                "zip": "",
                "country": "",
                "no_response_week": 4,
                "resume_extract_llm": "gpt-4.1-mini",
                "job_extract_llm": "gpt-4.1-mini",
                "rewrite_llm": "gpt-4.1-mini",
                "cover_llm": "gpt-4.1-mini",
                "company_llm": "gpt-4.1-mini",
                "openai_api_key": "",
                "tinymce_api_key": "",
                "convertapi_key": "",
                "docx2html": "docx-parser-converter",
                "odt2html": "pandoc",
                "pdf2html": "markitdown",
                "html2docx": "html4docx",
                "html2odt": "pandoc",
                "html2pdf": "weasyprint"
            }

            response = client.post("/v1/personal", json=personal_data)
            assert response.status_code == 200

            # Verify phone was formatted correctly
            result = test_db.execute(text("SELECT phone FROM user_detail")).first()
            assert result.phone == expected_phone

    def test_save_personal_info_empty_phone(self, client, test_db):
        """Test saving with empty phone number."""
        personal_data = {
            "first_name": "Test",
            "last_name": "User",
            "email": "test@example.com",
            "phone": "",
            "linkedin_url": "",
            "github_url": "",
            "website_url": "",
            "portfolio_url": "",
            "address_1": "",
            "address_2": "",
            "city": "",
            "state": "",
            "zip": "",
            "country": "",
            "no_response_week": 4,
            "resume_extract_llm": "gpt-4.1-mini",
            "job_extract_llm": "gpt-4.1-mini",
            "rewrite_llm": "gpt-4.1-mini",
            "cover_llm": "gpt-4.1-mini",
            "company_llm": "gpt-4.1-mini",
            "openai_api_key": "",
            "tinymce_api_key": "",
            "convertapi_key": "",
            "docx2html": "docx-parser-converter",
            "odt2html": "pandoc",
            "pdf2html": "markitdown",
            "html2docx": "html4docx",
            "html2odt": "pandoc",
            "html2pdf": "weasyprint"
        }

        response = client.post("/v1/personal", json=personal_data)

        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "success"

    def test_save_personal_info_minimal_fields(self, client, test_db):
        """Test saving with only required fields."""
        # Delete existing users and related data
        test_db.execute(text("DELETE FROM user_setting"))
        test_db.execute(text("DELETE FROM user_detail"))
        test_db.execute(text("DELETE FROM user_address"))
        test_db.execute(text("DELETE FROM users"))
        test_db.commit()

        personal_data = {
            "first_name": "Min",
            "last_name": "User",
            "email": "",
            "phone": "",
            "linkedin_url": "",
            "github_url": "",
            "website_url": "",
            "portfolio_url": "",
            "address_1": "",
            "address_2": "",
            "city": "",
            "state": "",
            "zip": "",
            "country": "",
            "no_response_week": 4,
            "resume_extract_llm": "gpt-4.1-mini",
            "job_extract_llm": "gpt-4.1-mini",
            "rewrite_llm": "gpt-4.1-mini",
            "cover_llm": "gpt-4.1-mini",
            "company_llm": "gpt-4.1-mini",
            "openai_api_key": "",
            "tinymce_api_key": "",
            "convertapi_key": "",
            "docx2html": "docx-parser-converter",
            "odt2html": "pandoc",
            "pdf2html": "markitdown",
            "html2docx": "html4docx",
            "html2odt": "pandoc",
            "html2pdf": "weasyprint"
        }

        response = client.post("/v1/personal", json=personal_data)

        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "success"

        # Verify data was saved
        user_result = test_db.execute(text("SELECT * FROM users")).first()
        assert user_result.first_name == "Min"
        assert user_result.last_name == "User"
