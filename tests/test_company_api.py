import pytest
from sqlalchemy import text


class TestCreateCompany:
    """Test suite for POST /v1/company endpoint."""

    def test_create_company_minimal(self, client, test_db):
        """Test creating a company with only required field (company_name)."""
        company_data = {
            "company_name": "Tech Corp"
        }

        response = client.post("/v1/company", json=company_data)

        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'success'
        assert 'company_id' in data

        # Verify company was created
        company = test_db.execute(text(f"SELECT * FROM company WHERE company_id = {data['company_id']}")).first()
        assert company.company_name == "Tech Corp"
        assert company.website_url is None
        assert company.hq_city is None

    def test_create_company_full(self, client, test_db):
        """Test creating a company with all fields."""
        company_data = {
            "company_name": "Acme Inc",
            "website_url": "https://acme.com",
            "hq_city": "San Francisco",
            "hq_state": "CA",
            "industry": "Technology",
            "linkedin_url": "https://linkedin.com/company/acme"
        }

        response = client.post("/v1/company", json=company_data)

        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'success'

        # Verify company was created with all fields
        company = test_db.execute(text(f"SELECT * FROM company WHERE company_id = {data['company_id']}")).first()
        assert company.company_name == "Acme Inc"
        assert company.website_url == "https://acme.com"
        assert company.hq_city == "San Francisco"
        assert company.hq_state == "CA"
        assert company.industry == "Technology"
        assert company.linkedin_url == "https://linkedin.com/company/acme"

    def test_create_company_with_job_id(self, client, test_db):
        """Test creating a company linked to a job."""
        # Create test job
        test_db.execute(text("""
            INSERT INTO job (job_id, company, job_title, job_status, job_active, job_directory)
            VALUES (1, 'Test Co', 'Engineer', 'applied', true, 'test_co_engineer')
        """))
        test_db.commit()

        company_data = {
            "company_name": "Test Co",
            "website_url": "https://testco.com",
            "job_id": 1
        }

        response = client.post("/v1/company", json=company_data)

        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'success'

        # Verify company was created with job link
        company = test_db.execute(text(f"SELECT * FROM company WHERE company_id = {data['company_id']}")).first()
        assert company.job_id == 1
        assert company.company_name == "Test Co"

    def test_create_company_with_invalid_job_id(self, client, test_db):
        """Test creating a company with non-existent job_id fails."""
        company_data = {
            "company_name": "Invalid Job Co",
            "job_id": 999
        }

        response = client.post("/v1/company", json=company_data)

        assert response.status_code == 404
        assert "Job with id 999 not found" in response.json()['detail']

    def test_create_company_missing_required_field(self, client, test_db):
        """Test creating company without company_name fails."""
        company_data = {
            "website_url": "https://example.com"
        }

        response = client.post("/v1/company", json=company_data)

        assert response.status_code == 422  # Validation error


class TestUpdateCompany:
    """Test suite for PUT /v1/company endpoint."""

    def test_update_company_basic(self, client, test_db):
        """Test updating basic company fields."""
        # Create initial company
        test_db.execute(text("""
            INSERT INTO company (company_id, company_name, website_url, hq_city)
            VALUES (1, 'Old Name', 'https://old.com', 'Old City')
        """))
        test_db.commit()

        update_data = {
            "company_id": 1,
            "company_name": "New Name",
            "website_url": "https://new.com",
            "hq_city": "New City"
        }

        response = client.put("/v1/company", json=update_data)

        assert response.status_code == 200
        assert response.json()['status'] == 'success'

        # Verify company was updated
        company = test_db.execute(text("SELECT * FROM company WHERE company_id = 1")).first()
        assert company.company_name == "New Name"
        assert company.website_url == "https://new.com"
        assert company.hq_city == "New City"

    def test_update_company_partial(self, client, test_db):
        """Test updating only some fields."""
        # Create initial company
        test_db.execute(text("""
            INSERT INTO company (company_id, company_name, website_url, hq_city, industry)
            VALUES (1, 'Tech Corp', 'https://tech.com', 'Austin', 'Technology')
        """))
        test_db.commit()

        update_data = {
            "company_id": 1,
            "hq_state": "TX",
            "linkedin_url": "https://linkedin.com/company/tech"
        }

        response = client.put("/v1/company", json=update_data)

        assert response.status_code == 200

        # Verify only specified fields were updated
        company = test_db.execute(text("SELECT * FROM company WHERE company_id = 1")).first()
        assert company.company_name == "Tech Corp"  # Unchanged
        assert company.website_url == "https://tech.com"  # Unchanged
        assert company.hq_state == "TX"  # Updated
        assert company.linkedin_url == "https://linkedin.com/company/tech"  # Updated

    def test_update_company_logo_and_report(self, client, test_db):
        """Test updating logo_file and report_html fields."""
        # Create initial company
        test_db.execute(text("""
            INSERT INTO company (company_id, company_name)
            VALUES (1, 'Report Co')
        """))
        test_db.commit()

        update_data = {
            "company_id": 1,
            "logo_file": "logo.png",
            "report_html": "<html><body>Company Report</body></html>"
        }

        response = client.put("/v1/company", json=update_data)

        assert response.status_code == 200

        # Verify fields were updated
        company = test_db.execute(text("SELECT * FROM company WHERE company_id = 1")).first()
        assert company.logo_file == "logo.png"
        assert company.report_html == "<html><body>Company Report</body></html>"

    def test_update_company_with_job_id(self, client, test_db):
        """Test updating company with job_id."""
        # Create test job and company
        test_db.execute(text("""
            INSERT INTO job (job_id, company, job_title, job_status, job_active, job_directory)
            VALUES (1, 'Test Co', 'Engineer', 'applied', true, 'test_co_engineer')
        """))
        test_db.execute(text("""
            INSERT INTO company (company_id, company_name)
            VALUES (1, 'Test Co')
        """))
        test_db.commit()

        update_data = {
            "company_id": 1,
            "job_id": 1
        }

        response = client.put("/v1/company", json=update_data)

        assert response.status_code == 200

        # Verify job_id was updated
        company = test_db.execute(text("SELECT * FROM company WHERE company_id = 1")).first()
        assert company.job_id == 1

    def test_update_company_not_found(self, client, test_db):
        """Test updating non-existent company."""
        update_data = {
            "company_id": 999,
            "company_name": "Does Not Exist"
        }

        response = client.put("/v1/company", json=update_data)

        assert response.status_code == 404
        assert "Company with id 999 not found" in response.json()['detail']

    def test_update_company_with_invalid_job_id(self, client, test_db):
        """Test updating company with non-existent job_id fails."""
        # Create company
        test_db.execute(text("""
            INSERT INTO company (company_id, company_name)
            VALUES (1, 'Test Co')
        """))
        test_db.commit()

        update_data = {
            "company_id": 1,
            "job_id": 999
        }

        response = client.put("/v1/company", json=update_data)

        assert response.status_code == 404
        assert "Job with id 999 not found" in response.json()['detail']

    def test_update_company_missing_company_id(self, client, test_db):
        """Test updating without company_id fails."""
        update_data = {
            "company_name": "No ID"
        }

        response = client.put("/v1/company", json=update_data)

        assert response.status_code == 422  # Validation error


class TestGetCompany:
    """Test suite for GET /v1/company/<company_id> endpoint."""

    def test_get_company_success(self, client, test_db):
        """Test retrieving a company by ID."""
        # Create company
        test_db.execute(text("""
            INSERT INTO company (company_id, company_name, website_url, hq_city, hq_state, industry, linkedin_url)
            VALUES (1, 'Acme Inc', 'https://acme.com', 'San Francisco', 'CA', 'Technology', 'https://linkedin.com/company/acme')
        """))
        test_db.commit()

        response = client.get("/v1/company/1")

        assert response.status_code == 200
        data = response.json()

        assert data['company_id'] == 1
        assert data['company_name'] == "Acme Inc"
        assert data['website_url'] == "https://acme.com"
        assert data['hq_city'] == "San Francisco"
        assert data['hq_state'] == "CA"
        assert data['industry'] == "Technology"
        assert data['linkedin_url'] == "https://linkedin.com/company/acme"
        assert 'company_created' in data
        assert data['report_created'] is None

    def test_get_company_with_optional_fields(self, client, test_db):
        """Test retrieving company with logo and report."""
        # Create company with all fields
        test_db.execute(text("""
            INSERT INTO company (company_id, company_name, website_url, logo_file, report_html, report_created)
            VALUES (1, 'Report Co', 'https://report.com', 'logo.png', '<html>Report</html>', CURRENT_TIMESTAMP)
        """))
        test_db.commit()

        response = client.get("/v1/company/1")

        assert response.status_code == 200
        data = response.json()

        assert data['company_name'] == "Report Co"
        assert data['logo_file'] == "logo.png"
        assert data['report_html'] == "<html>Report</html>"
        assert data['report_created'] is not None

    def test_get_company_with_job_link(self, client, test_db):
        """Test retrieving company linked to a job."""
        # Create job and company
        test_db.execute(text("""
            INSERT INTO job (job_id, company, job_title, job_status, job_active, job_directory)
            VALUES (1, 'Test Co', 'Engineer', 'applied', true, 'test_co_engineer')
        """))
        test_db.execute(text("""
            INSERT INTO company (company_id, company_name, job_id)
            VALUES (1, 'Test Co', 1)
        """))
        test_db.commit()

        response = client.get("/v1/company/1")

        assert response.status_code == 200
        data = response.json()

        assert data['company_name'] == "Test Co"
        assert data['job_id'] == 1

    def test_get_company_not_found(self, client, test_db):
        """Test retrieving non-existent company."""
        response = client.get("/v1/company/999")

        assert response.status_code == 404
        assert "Company with id 999 not found" in response.json()['detail']

    def test_get_company_minimal_data(self, client, test_db):
        """Test retrieving company with only required field."""
        # Create company with minimal data
        test_db.execute(text("""
            INSERT INTO company (company_id, company_name)
            VALUES (1, 'Minimal Co')
        """))
        test_db.commit()

        response = client.get("/v1/company/1")

        assert response.status_code == 200
        data = response.json()

        assert data['company_name'] == "Minimal Co"
        assert data['website_url'] is None
        assert data['hq_city'] is None
        assert data['hq_state'] is None
        assert data['industry'] is None
        assert data['linkedin_url'] is None
        assert data['job_id'] is None
        assert data['logo_file'] is None
        assert data['report_html'] is None
        assert 'company_created' in data


class TestGetCompanyList:
    """Test suite for GET /v1/company/list endpoint."""

    def test_get_company_list_success(self, client, test_db):
        """Test retrieving list of active companies."""
        # Create companies with report_active=true
        test_db.execute(text("""
            INSERT INTO company (company_id, company_name, website_url, hq_city, hq_state, industry, report_active)
            VALUES
                (1, 'Alpha Corp', 'https://alpha.com', 'Austin', 'TX', 'Technology', true),
                (2, 'Beta Inc', 'https://beta.com', 'Boston', 'MA', 'Finance', true),
                (3, 'Inactive Co', 'https://inactive.com', 'Portland', 'OR', 'Retail', false)
        """))
        test_db.commit()

        response = client.get("/v1/company/list")

        assert response.status_code == 200
        data = response.json()

        assert len(data) == 2  # Only active companies
        assert data[0]['company_name'] == "Alpha Corp"
        assert data[1]['company_name'] == "Beta Inc"

    def test_get_company_list_ordered_by_name(self, client, test_db):
        """Test that companies are ordered by name."""
        # Create companies in non-alphabetical order
        test_db.execute(text("""
            INSERT INTO company (company_id, company_name, report_active)
            VALUES
                (1, 'Zebra Corp', true),
                (2, 'Apple Inc', true),
                (3, 'Microsoft', true)
        """))
        test_db.commit()

        response = client.get("/v1/company/list")

        assert response.status_code == 200
        data = response.json()

        assert len(data) == 3
        assert data[0]['company_name'] == "Apple Inc"
        assert data[1]['company_name'] == "Microsoft"
        assert data[2]['company_name'] == "Zebra Corp"

    def test_get_company_list_includes_all_fields(self, client, test_db):
        """Test that response includes all company fields."""
        test_db.execute(text("""
            INSERT INTO company (
                company_id, company_name, website_url, hq_city, hq_state,
                industry, logo_file, linkedin_url, job_id, report_html,
                report_created, report_active
            )
            VALUES (
                1, 'Full Data Corp', 'https://full.com', 'Denver', 'CO',
                'Technology', 'logo.png', 'https://linkedin.com/company/full',
                NULL, '<html>Report</html>', CURRENT_TIMESTAMP, true
            )
        """))
        test_db.commit()

        response = client.get("/v1/company/list")

        assert response.status_code == 200
        data = response.json()

        assert len(data) == 1
        company = data[0]
        assert company['company_name'] == "Full Data Corp"
        assert company['website_url'] == "https://full.com"
        assert company['hq_city'] == "Denver"
        assert company['hq_state'] == "CO"
        assert company['industry'] == "Technology"
        assert company['logo_file'] == "logo.png"
        assert company['linkedin_url'] == "https://linkedin.com/company/full"
        assert company['report_html'] == "<html>Report</html>"
        assert company['report_created'] != ""

    def test_get_company_list_empty(self, client, test_db):
        """Test retrieving empty company list."""
        response = client.get("/v1/company/list")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0


class TestDeleteCompany:
    """Test suite for DELETE /v1/company/<company_id> endpoint."""

    def test_delete_company_success(self, client, test_db):
        """Test soft deleting a company."""
        # Create company
        test_db.execute(text("""
            INSERT INTO company (company_id, company_name, report_active)
            VALUES (1, 'Delete Me', true)
        """))
        test_db.commit()

        response = client.delete("/v1/company/1")

        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'success'
        assert 'deleted successfully' in data['message']

        # Verify company was soft deleted
        company = test_db.execute(text("SELECT * FROM company WHERE company_id = 1")).first()
        assert company.report_active is False

    def test_delete_company_not_found(self, client, test_db):
        """Test deleting non-existent company."""
        response = client.delete("/v1/company/999")

        assert response.status_code == 404
        assert "Company with id 999 not found" in response.json()['detail']

    def test_delete_company_preserves_data(self, client, test_db):
        """Test that deletion only sets report_active to false."""
        # Create company with data
        test_db.execute(text("""
            INSERT INTO company (
                company_id, company_name, website_url, report_html, report_active
            )
            VALUES (1, 'Preserve Me', 'https://preserve.com', '<html>Report</html>', true)
        """))
        test_db.commit()

        response = client.delete("/v1/company/1")

        assert response.status_code == 200

        # Verify data is preserved but report_active is false
        company = test_db.execute(text("SELECT * FROM company WHERE company_id = 1")).first()
        assert company.company_name == "Preserve Me"
        assert company.website_url == "https://preserve.com"
        assert company.report_html == "<html>Report</html>"
        assert company.report_active is False


class TestDownloadCompanyReport:
    """Test suite for GET /v1/company/download/<company_id> endpoint."""

    def test_download_company_report_success(self, client, test_db, tmp_path, monkeypatch):
        """Test downloading a company report."""
        # Mock the settings.report_dir
        import os
        from app.core import config
        test_report_dir = str(tmp_path / "reports")
        os.makedirs(test_report_dir, exist_ok=True)
        monkeypatch.setattr(config.settings, 'report_dir', test_report_dir)

        # Create company with report
        test_db.execute(text("""
            INSERT INTO company (company_id, company_name, report_html)
            VALUES (1, 'Test Company', '<html><body>Test Report</body></html>')
        """))
        test_db.commit()

        response = client.get("/v1/company/download/1")

        assert response.status_code == 200
        data = response.json()
        assert 'file_name' in data
        assert data['file_name'] == 'test_company_company_report.docx'

        # Verify file was created
        expected_path = os.path.join(test_report_dir, 'test_company_company_report.docx')
        assert os.path.exists(expected_path)

    def test_download_company_report_not_found(self, client, test_db):
        """Test downloading report for non-existent company."""
        response = client.get("/v1/company/download/999")

        assert response.status_code == 404
        assert "Company with id 999 not found" in response.json()['detail']

    def test_download_company_report_no_html(self, client, test_db):
        """Test downloading report when no report_html exists."""
        # Create company without report
        test_db.execute(text("""
            INSERT INTO company (company_id, company_name)
            VALUES (1, 'No Report Co')
        """))
        test_db.commit()

        response = client.get("/v1/company/download/1")

        assert response.status_code == 404
        assert "No report found" in response.json()['detail']

    def test_download_company_report_sanitizes_filename(self, client, test_db, tmp_path, monkeypatch):
        """Test that filename is properly sanitized."""
        # Mock the settings.report_dir
        import os
        from app.core import config
        test_report_dir = str(tmp_path / "reports")
        os.makedirs(test_report_dir, exist_ok=True)
        monkeypatch.setattr(config.settings, 'report_dir', test_report_dir)

        # Create company with special characters in name
        test_db.execute(text("""
            INSERT INTO company (company_id, company_name, report_html)
            VALUES (1, 'Company & Co. (LLC)!', '<html><body>Test</body></html>')
        """))
        test_db.commit()

        response = client.get("/v1/company/download/1")

        assert response.status_code == 200
        data = response.json()
        # Verify special characters are removed
        assert 'file_name' in data
        # Should only have alphanumeric and underscores
        filename = data['file_name'].replace('_company_report.docx', '')
        assert all(c.isalnum() or c == '_' for c in filename)
