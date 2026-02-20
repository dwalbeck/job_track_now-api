import pytest
from unittest.mock import Mock, patch
from sqlalchemy import text


# Helper to get test user ID
def get_test_user_id(test_db):
    result = test_db.execute(text("SELECT user_id FROM users WHERE login = 'testuser'")).first()
    return result.user_id if result else 1


class TestGetAllJobs:
    """Test suite for GET /v1/jobs endpoint."""

    def test_get_all_jobs_empty(self, client, test_db):
        """Test retrieving jobs when none exist."""
        response = client.get("/v1/jobs")

        assert response.status_code == 200
        assert response.json() == []

    def test_get_all_jobs_multiple(self, client, test_db):
        """Test retrieving multiple active jobs."""
        user_id = get_test_user_id(test_db)
        # Create test jobs
        test_db.execute(text("""
            INSERT INTO job (user_id, company, job_title, job_status, job_active, last_activity, job_directory, average_score, interest_level, starred)
            VALUES
                (:user_id, 'Google', 'Software Engineer', 'applied', true, '2025-01-10', 'google_software_engineer', 5, 5, false),
                (:user_id, 'Microsoft', 'Senior Developer', 'interviewing', true, '2025-01-15', 'microsoft_senior_developer', 5, 5, true),
                (:user_id, 'Amazon', 'Tech Lead', 'applied', true, '2025-01-05', 'amazon_tech_lead', 5, 5, false)
        """), {"user_id": user_id})
        test_db.commit()

        response = client.get("/v1/jobs")

        assert response.status_code == 200
        jobs = response.json()

        assert len(jobs) == 3
        # Should be ordered by last_activity DESC
        assert jobs[0]['company'] == 'Microsoft'
        assert jobs[1]['company'] == 'Google'
        assert jobs[2]['company'] == 'Amazon'
        # Verify starred field is present
        assert jobs[0]['starred'] == True
        assert jobs[1]['starred'] == False
        # Verify calendar fields are present (should be None without appointments)
        assert 'calendar_id' in jobs[0]
        assert 'start_date' in jobs[0]
        assert 'start_time' in jobs[0]

    def test_get_all_jobs_excludes_inactive(self, client, test_db):
        """Test that inactive jobs are not returned."""
        user_id = get_test_user_id(test_db)
        # Create active and inactive jobs
        test_db.execute(text("""
            INSERT INTO job (user_id, company, job_title, job_status, job_active, job_directory, average_score, interest_level)
            VALUES
                (:user_id, 'Active Co', 'Developer', 'applied', true, 'active_co_developer', 5, 5),
                (:user_id, 'Inactive Co', 'Engineer', 'applied', false, 'inactive_co_engineer', 5, 5)
        """), {"user_id": user_id})
        test_db.commit()

        response = client.get("/v1/jobs")

        assert response.status_code == 200
        jobs = response.json()

        assert len(jobs) == 1
        assert jobs[0]['company'] == 'Active Co'

    def test_get_all_jobs_with_calendar_appointments(self, client, test_db):
        """Test that jobs include latest calendar appointment data."""
        user_id = get_test_user_id(test_db)
        # Create test jobs
        test_db.execute(text("""
            INSERT INTO job (job_id, user_id, company, job_title, job_status, job_active, last_activity, job_directory, average_score, interest_level)
            VALUES
                (1, :user_id, 'Job With Appt', 'Engineer', 'interviewing', true, '2025-01-10', 'job_with_appt_engineer', 5, 5),
                (2, :user_id, 'Job No Appt', 'Developer', 'applied', true, '2025-01-08', 'job_no_appt_developer', 5, 5)
        """), {"user_id": user_id})
        # Create calendar appointments for first job (dates must be in the future)
        test_db.execute(text("""
            INSERT INTO calendar (user_id, job_id, start_date, start_time, calendar_type)
            VALUES
                (:user_id, 1, CURRENT_DATE + INTERVAL '10 days', '10:00:00', 'interview'),
                (:user_id, 1, CURRENT_DATE + INTERVAL '20 days', '14:30:00', 'interview')
        """), {"user_id": user_id})
        test_db.commit()

        response = client.get("/v1/jobs")

        assert response.status_code == 200
        jobs = response.json()

        assert len(jobs) == 2
        # First job should have calendar data from next upcoming appointment
        job_with_appt = next(job for job in jobs if job['company'] == 'Job With Appt')
        assert job_with_appt['calendar_id'] is not None
        assert job_with_appt['start_date'] is not None  # Date is dynamic
        assert job_with_appt['start_time'] == '10:00:00'  # First upcoming appointment

        # Second job should have None for calendar fields
        job_no_appt = next(job for job in jobs if job['company'] == 'Job No Appt')
        assert job_no_appt['calendar_id'] is None
        assert job_no_appt['start_date'] is None
        assert job_no_appt['start_time'] is None


class TestDeleteJob:
    """Test suite for DELETE /v1/job/{job_id} endpoint."""

    def test_delete_job_success(self, client, test_db):
        """Test successfully deleting a job."""
        user_id = get_test_user_id(test_db)
        # Create test job
        test_db.execute(text("""
            INSERT INTO job (job_id, user_id, company, job_title, job_status, job_active, job_directory)
            VALUES (1, :user_id, 'Test Co', 'Developer', 'applied', true, 'test_co_developer')
        """), {"user_id": user_id})
        test_db.commit()

        response = client.delete("/v1/job/1")

        assert response.status_code == 200
        assert response.json() == {"status": "success"}

        # Verify job is soft deleted
        result = test_db.execute(text("SELECT job_active FROM job WHERE job_id = 1")).first()
        assert result.job_active == False

    def test_delete_job_not_found(self, client, test_db):
        """Test deleting non-existent job."""
        response = client.delete("/v1/job/999")

        assert response.status_code == 404
        assert "Job not found" in response.json()['detail']


class TestGetJobList:
    """Test suite for GET /v1/job/list endpoint."""

    def test_get_job_list_empty(self, client, test_db):
        """Test job list when no jobs exist."""
        response = client.get("/v1/job/list")

        assert response.status_code == 200
        assert response.json() == []

    def test_get_job_list_multiple(self, client, test_db):
        """Test getting job list with multiple jobs."""
        user_id = get_test_user_id(test_db)
        # Create test jobs with different dates
        test_db.execute(text("""
            INSERT INTO job (job_id, user_id, company, job_title, job_status, job_active, job_directory, last_activity, date_applied, starred)
            VALUES
                (1, :user_id, 'Apple', 'iOS Developer', 'applied', true, 'apple_ios_developer', '2025-01-10', '2025-01-10', false),
                (2, :user_id, 'Facebook', 'Backend Engineer', 'interviewing', true, 'facebook_backend_engineer', '2025-01-15', '2025-01-14', true),
                (3, :user_id, 'Netflix', 'DevOps Engineer', 'applied', true, 'netflix_devops_engineer', '2025-01-05', '2025-01-05', false)
        """), {"user_id": user_id})
        test_db.commit()

        response = client.get("/v1/job/list")

        assert response.status_code == 200
        jobs = response.json()

        assert len(jobs) == 3
        # Should be ordered by last_activity DESC
        assert jobs[0]['job_id'] == 2
        assert jobs[0]['company'] == 'Facebook'
        assert jobs[0]['job_title'] == 'Backend Engineer'
        assert jobs[0]['starred'] == True
        assert 'starred' in jobs[1]

    def test_get_job_list_excludes_inactive(self, client, test_db):
        """Test that job list excludes inactive jobs."""
        user_id = get_test_user_id(test_db)
        test_db.execute(text("""
            INSERT INTO job (job_id, user_id, company, job_title, job_status, job_active, job_directory)
            VALUES
                (1, :user_id, 'Active Corp', 'Developer', 'applied', true, 'active_corp_developer'),
                (2, :user_id, 'Deleted Corp', 'Engineer', 'rejected', false, 'deleted_corp_engineer')
        """), {"user_id": user_id})
        test_db.commit()

        response = client.get("/v1/job/list")

        assert response.status_code == 200
        jobs = response.json()

        assert len(jobs) == 1
        assert jobs[0]['company'] == 'Active Corp'


class TestGetJob:
    """Test suite for GET /v1/job/{job_id} endpoint."""

    def test_get_job_success(self, client, test_db):
        """Test getting a job by ID."""
        user_id = get_test_user_id(test_db)
        # Create test job
        test_db.execute(text("""
            INSERT INTO job (job_id, user_id, company, job_title, job_status, posting_url, interest_level,
                           location, salary, job_active, job_directory)
            VALUES (1, :user_id, 'Tesla', 'Software Engineer', 'applied', 'https://tesla.com/jobs/123',
                   8, 'Palo Alto, CA', '$150,000 - $200,000', true, 'tesla_software_engineer')
        """), {"user_id": user_id})
        test_db.execute(text("""
            INSERT INTO job_detail (job_id, job_desc, job_qualification, job_keyword)
            VALUES (1, 'Build amazing software', 'BS in CS required', ARRAY['Python', 'React'])
        """))
        test_db.commit()

        response = client.get("/v1/job/1")

        assert response.status_code == 200
        job = response.json()

        assert job['job_id'] == 1
        assert job['company'] == 'Tesla'
        assert job['job_title'] == 'Software Engineer'
        assert job['job_status'] == 'applied'
        assert job['posting_url'] == 'https://tesla.com/jobs/123'
        assert job['interest_level'] == 8
        assert job['location'] == 'Palo Alto, CA'
        assert job['salary'] == '$150,000 - $200,000'
        assert job['job_desc'] == 'Build amazing software'
        assert job['job_qualification'] == 'BS in CS required'
        assert job['job_keyword'] == ['Python', 'React']

    def test_get_job_not_found(self, client, test_db):
        """Test getting non-existent job."""
        response = client.get("/v1/job/999")

        assert response.status_code == 404
        assert "Job not found" in response.json()['detail']

    def test_get_job_inactive_not_found(self, client, test_db):
        """Test that inactive jobs return 404."""
        user_id = get_test_user_id(test_db)
        test_db.execute(text("""
            INSERT INTO job (job_id, user_id, company, job_title, job_status, job_active, job_directory)
            VALUES (1, :user_id, 'Inactive Co', 'Developer', 'rejected', false, 'inactive_co_developer')
        """), {"user_id": user_id})
        test_db.commit()

        response = client.get("/v1/job/1")

        assert response.status_code == 404


class TestCreateOrUpdateJob:
    """Test suite for POST /v1/job endpoint."""

    @patch('app.utils.job_helpers.calc_avg_score')
    def test_create_job_success(self, mock_calc_avg, client, test_db):
        """Test creating a new job."""
        mock_calc_avg.return_value = None

        job_data = {
            "company": "Stripe",
            "job_title": "Full Stack Developer",
            "job_status": "applied",
            "posting_url": "https://stripe.com/careers/123",
            "interest_level": 9,
            "location": "San Francisco, CA",
            "salary": "$160,000 - $220,000",
            "job_desc": "Build payment systems"
        }

        response = client.post("/v1/job", json=job_data)

        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'success'
        assert 'job_id' in data

        # Verify job was created
        job = test_db.execute(text(f"SELECT * FROM job WHERE job_id = {data['job_id']}")).first()
        assert job.company == "Stripe"
        assert job.job_title == "Full Stack Developer"
        assert job.job_status == "applied"
        assert job.interest_level == 9
        assert job.job_active == True
        assert job.starred == False

        # Verify job_detail was created
        detail = test_db.execute(text(f"SELECT * FROM job_detail WHERE job_id = {data['job_id']}")).first()
        assert detail.job_desc == "Build payment systems"

    @patch('app.utils.job_helpers.calc_avg_score')
    def test_create_job_starred(self, mock_calc_avg, client, test_db):
        """Test creating a new starred job."""
        mock_calc_avg.return_value = None

        job_data = {
            "company": "Starred Co",
            "job_title": "Dream Job",
            "job_status": "applied",
            "interest_level": 10,
            "starred": True
        }

        response = client.post("/v1/job", json=job_data)

        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'success'

        job = test_db.execute(text(f"SELECT * FROM job WHERE job_id = {data['job_id']}")).first()
        assert job.starred == True

    @patch('app.utils.job_helpers.calc_avg_score')
    def test_update_job_starred(self, mock_calc_avg, client, test_db):
        """Test toggling starred on an existing job."""
        mock_calc_avg.return_value = None
        user_id = get_test_user_id(test_db)

        test_db.execute(text("""
            INSERT INTO job (job_id, user_id, company, job_title, job_status, job_active, job_directory, starred)
            VALUES (1, :user_id, 'Star Co', 'Engineer', 'applied', true, 'star_co_engineer', false)
        """), {"user_id": user_id})
        test_db.commit()

        response = client.post("/v1/job", json={"job_id": 1, "starred": True})

        assert response.status_code == 200

        job = test_db.execute(text("SELECT starred FROM job WHERE job_id = 1")).first()
        assert job.starred == True

    @patch('app.utils.job_helpers.calc_avg_score')
    def test_update_job_success(self, mock_calc_avg, client, test_db):
        """Test updating an existing job."""
        mock_calc_avg.return_value = None
        user_id = get_test_user_id(test_db)

        # Create initial job
        test_db.execute(text("""
            INSERT INTO job (job_id, user_id, company, job_title, job_status, job_active, job_directory)
            VALUES (1, :user_id, 'Old Company', 'Old Title', 'applied', true, 'old_company_old_title')
        """), {"user_id": user_id})
        test_db.commit()

        update_data = {
            "job_id": 1,
            "company": "New Company",
            "job_title": "New Title",
            "job_status": "interviewing",
            "interest_level": 10
        }

        response = client.post("/v1/job", json=update_data)

        assert response.status_code == 200
        assert response.json()['status'] == 'success'

        # Verify job was updated
        job = test_db.execute(text("SELECT * FROM job WHERE job_id = 1")).first()
        assert job.company == "New Company"
        assert job.job_title == "New Title"
        assert job.job_status == "interviewing"
        assert job.interest_level == 10

    def test_create_job_missing_required_fields(self, client, test_db):
        """Test creating job with missing required fields."""
        job_data = {
            "company": "Incomplete Co"
            # Missing job_title and job_status
        }

        response = client.post("/v1/job", json=job_data)

        assert response.status_code == 400
        assert "required" in response.json()['detail'].lower()

    def test_update_job_not_found(self, client, test_db):
        """Test updating non-existent job."""
        update_data = {
            "job_id": 999,
            "company": "Does Not Exist",
            "job_title": "Fake Job",
            "job_status": "applied"
        }

        response = client.post("/v1/job", json=update_data)

        assert response.status_code == 404
        assert "Job not found" in response.json()['detail']


class TestExtractJobData:
    """Test suite for POST /v1/job/extract endpoint."""

    @patch('app.utils.ai_agent.AiAgent.job_extraction')
    def test_extract_job_data_success(self, mock_extraction, client, test_db):
        """Test successful job data extraction."""
        user_id = get_test_user_id(test_db)
        # Create test job with description
        test_db.execute(text("""
            INSERT INTO job (job_id, user_id, company, job_title, job_status, job_active, job_directory)
            VALUES (1, :user_id, 'Airbnb', 'Backend Engineer', 'applied', true, 'airbnb_backend_engineer')
        """), {"user_id": user_id})
        test_db.execute(text("""
            INSERT INTO job_detail (job_id, job_desc)
            VALUES (1, 'We are looking for a backend engineer with Python and AWS experience.')
        """))
        test_db.commit()

        # Mock AI extraction
        mock_extraction.return_value = {
            'job_qualification': 'Python and AWS experience required',
            'keywords': ['Python', 'AWS', 'Backend', 'API']
        }

        response = client.post("/v1/job/extract", json={"job_id": 1})

        assert response.status_code == 200
        data = response.json()

        assert data['job_qualification'] == 'Python and AWS experience required'
        assert data['keywords'] == ['Python', 'AWS', 'Backend', 'API']

    def test_extract_job_data_cached(self, client, test_db):
        """Test extraction returns cached data if already extracted."""
        user_id = get_test_user_id(test_db)
        # Create job with existing qualification and keywords
        test_db.execute(text("""
            INSERT INTO job (job_id, user_id, company, job_title, job_status, job_active, job_directory)
            VALUES (1, :user_id, 'Cached Co', 'Engineer', 'applied', true, 'cached_co_engineer')
        """), {"user_id": user_id})
        test_db.execute(text("""
            INSERT INTO job_detail (job_id, job_desc, job_qualification, job_keyword)
            VALUES (1, 'Description', 'Cached qualification', ARRAY['Cached', 'Keywords'])
        """))
        test_db.commit()

        response = client.post("/v1/job/extract", json={"job_id": 1})

        assert response.status_code == 200
        data = response.json()

        assert data['job_qualification'] == 'Cached qualification'
        assert data['keywords'] == ['Cached', 'Keywords']

    def test_extract_job_data_job_not_found(self, client, test_db):
        """Test extraction with non-existent job."""
        response = client.post("/v1/job/extract", json={"job_id": 999})

        assert response.status_code == 404
        assert "Job not found" in response.json()['detail']


class TestCreateOrUpdateJobDetail:
    """Test suite for POST /v1/job/detail endpoint."""

    def test_create_job_detail_success(self, client, test_db):
        """Test creating job detail."""
        user_id = get_test_user_id(test_db)
        # Create test job
        test_db.execute(text("""
            INSERT INTO job (job_id, user_id, company, job_title, job_status, job_active, job_directory)
            VALUES (1, :user_id, 'Detail Co', 'Engineer', 'applied', true, 'detail_co_engineer')
        """), {"user_id": user_id})
        test_db.commit()

        detail_data = {
            "job_id": 1,
            "job_desc": "This is a job description",
            "job_qualification": "Bachelor's degree required",
            "job_keyword": ["Python", "Docker", "Kubernetes"]
        }

        response = client.post("/v1/job/detail", json=detail_data)

        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'success'
        assert data['job_id'] == 1

        # Verify detail was created
        detail = test_db.execute(text("SELECT * FROM job_detail WHERE job_id = 1")).first()
        assert detail.job_desc == "This is a job description"
        assert detail.job_qualification == "Bachelor's degree required"
        assert list(detail.job_keyword) == ["Python", "Docker", "Kubernetes"]

    def test_update_job_detail_success(self, client, test_db):
        """Test updating existing job detail."""
        user_id = get_test_user_id(test_db)
        # Create job and detail
        test_db.execute(text("""
            INSERT INTO job (job_id, user_id, company, job_title, job_status, job_active, job_directory)
            VALUES (1, :user_id, 'Update Co', 'Engineer', 'applied', true, 'update_co_engineer')
        """), {"user_id": user_id})
        test_db.execute(text("""
            INSERT INTO job_detail (job_id, job_desc, job_qualification)
            VALUES (1, 'Old description', 'Old qualification')
        """))
        test_db.commit()

        detail_data = {
            "job_id": 1,
            "job_desc": "Updated description",
            "job_qualification": "Updated qualification",
            "job_keyword": ["New", "Keywords"]
        }

        response = client.post("/v1/job/detail", json=detail_data)

        assert response.status_code == 200

        # Verify detail was updated
        detail = test_db.execute(text("SELECT * FROM job_detail WHERE job_id = 1")).first()
        assert detail.job_desc == "Updated description"
        assert detail.job_qualification == "Updated qualification"
        assert list(detail.job_keyword) == ["New", "Keywords"]

    def test_create_job_detail_job_not_found(self, client, test_db):
        """Test creating detail for non-existent job."""
        detail_data = {
            "job_id": 999,
            "job_desc": "Description"
        }

        response = client.post("/v1/job/detail", json=detail_data)

        assert response.status_code == 404
        assert "Job not found" in response.json()['detail']
