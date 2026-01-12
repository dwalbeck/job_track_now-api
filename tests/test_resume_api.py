import pytest
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy import text
from io import BytesIO


class TestGetBaselineResumes:
    """Test suite for GET /v1/resume/baseline endpoint."""

    def test_get_baseline_resumes_empty(self, client, test_db):
        """Test getting baseline resumes when none exist."""
        response = client.get("/v1/resume/baseline")

        assert response.status_code == 200
        assert response.json() == []

    def test_get_baseline_resumes_multiple(self, client, test_db):
        """Test getting multiple baseline resumes."""
        # Create test resumes
        test_db.execute(text("""
            INSERT INTO resume (resume_id, resume_title, file_name, original_format, is_baseline, is_default, is_active)
            VALUES
                (1, 'Default Resume', 'default.pdf', 'pdf', true, true, true),
                (2, 'Alternative Resume', 'alt.docx', 'docx', true, false, true),
                (3, 'Old Resume', 'old.pdf', 'pdf', true, false, true)
        """))
        test_db.execute(text("""
            INSERT INTO resume_detail (resume_id, keyword_count, focus_count)
            VALUES
                (1, 25, 10),
                (2, 30, 12),
                (3, 20, 8)
        """))
        test_db.commit()

        response = client.get("/v1/resume/baseline")

        assert response.status_code == 200
        resumes = response.json()

        assert len(resumes) == 3
        # Default should be first
        assert resumes[0]['resume_title'] == 'Default Resume'
        assert resumes[0]['is_default'] == True
        assert resumes[0]['keyword_count'] == 25
        assert resumes[0]['focus_count'] == 10

    def test_get_baseline_resumes_excludes_inactive(self, client, test_db):
        """Test that inactive resumes are excluded."""
        test_db.execute(text("""
            INSERT INTO resume (resume_id, resume_title, file_name, original_format, is_baseline, is_default, is_active)
            VALUES
                (1, 'Active Resume', 'active.pdf', 'pdf', true, false, true),
                (2, 'Deleted Resume', 'deleted.pdf', 'pdf', true, false, false)
        """))
        test_db.commit()

        response = client.get("/v1/resume/baseline")

        assert response.status_code == 200
        resumes = response.json()

        assert len(resumes) == 1
        assert resumes[0]['resume_title'] == 'Active Resume'


class TestGetBaselineResumeList:
    """Test suite for GET /v1/resume/baseline/list endpoint."""

    def test_get_baseline_list_empty(self, client, test_db):
        """Test getting baseline list when none exist."""
        response = client.get("/v1/resume/baseline/list")

        assert response.status_code == 200
        assert response.json() == []

    def test_get_baseline_list_ordered_by_created(self, client, test_db):
        """Test that baseline list is ordered by resume_created DESC."""
        test_db.execute(text("""
            INSERT INTO resume (resume_id, resume_title, file_name, original_format, is_baseline, is_default, is_active, resume_created)
            VALUES
                (1, 'Oldest', 'oldest.pdf', 'pdf', true, false, true, '2024-01-01'),
                (2, 'Newest', 'newest.pdf', 'pdf', true, true, true, '2025-01-15'),
                (3, 'Middle', 'middle.pdf', 'pdf', true, false, true, '2024-06-01')
        """))
        test_db.commit()

        response = client.get("/v1/resume/baseline/list")

        assert response.status_code == 200
        resumes = response.json()

        assert len(resumes) == 3
        # Should be ordered by created date DESC
        assert resumes[0]['resume_title'] == 'Newest'
        assert resumes[1]['resume_title'] == 'Middle'
        assert resumes[2]['resume_title'] == 'Oldest'


class TestGetJobResumes:
    """Test suite for GET /v1/resume/job endpoint."""

    def test_get_job_resumes_empty(self, client, test_db):
        """Test getting job resumes when none exist."""
        response = client.get("/v1/resume/job")

        assert response.status_code == 200
        assert response.json() == []

    def test_get_job_resumes_multiple(self, client, test_db):
        """Test getting multiple job-specific resumes."""
        # Create test jobs
        test_db.execute(text("""
            INSERT INTO job (job_id, company, job_title, job_status, job_active, job_directory)
            VALUES
                (1, 'Google', 'SWE', 'applied', true, 'google_swe'),
                (2, 'Meta', 'Engineer', 'interviewing', true, 'meta_engineer')
        """))
        # Create baseline resume
        test_db.execute(text("""
            INSERT INTO resume (resume_id, resume_title, file_name, original_format, is_baseline, is_default, is_active)
            VALUES (10, 'Baseline', 'baseline.pdf', 'pdf', true, true, true)
        """))
        # Create job resumes
        test_db.execute(text("""
            INSERT INTO resume (resume_id, resume_title, file_name, original_format, is_baseline, is_default, is_active, job_id, baseline_resume_id)
            VALUES
                (1, 'Google Resume', 'google.html', 'html', false, false, true, 1, 10),
                (2, 'Meta Resume', 'meta.html', 'html', false, false, true, 2, 10)
        """))
        test_db.execute(text("""
            INSERT INTO resume_detail (resume_id, keyword_count, focus_count, baseline_score, rewrite_score)
            VALUES
                (1, 30, 15, 75, 92),
                (2, 28, 14, 70, 88)
        """))
        test_db.commit()

        response = client.get("/v1/resume/job")

        assert response.status_code == 200
        resumes = response.json()

        assert len(resumes) == 2
        assert resumes[0]['company'] == 'Google' or resumes[0]['company'] == 'Meta'
        assert resumes[0]['baseline_resume_id'] == 10
        assert 'baseline_score' in resumes[0]
        assert 'rewrite_score' in resumes[0]


class TestGetResume:
    """Test suite for GET /v1/resume/{resume_id} endpoint."""

    def test_get_resume_success(self, client, test_db):
        """Test getting a resume by ID."""
        test_db.execute(text("""
            INSERT INTO resume (resume_id, resume_title, file_name, original_format, is_baseline, is_default, is_active)
            VALUES (1, 'Test Resume', 'test.pdf', 'pdf', true, true, true)
        """))
        test_db.commit()

        response = client.get("/v1/resume/1")

        assert response.status_code == 200
        resume = response.json()

        assert resume['resume_id'] == 1
        assert resume['resume_title'] == 'Test Resume'
        assert resume['file_name'] == 'test.pdf'
        assert resume['original_format'] == 'pdf'
        assert resume['is_baseline'] == True
        assert resume['is_default'] == True
        assert resume['is_active'] == True

    def test_get_resume_not_found(self, client, test_db):
        """Test getting non-existent resume."""
        response = client.get("/v1/resume/999")

        assert response.status_code == 404
        assert "Resume not found" in response.json()['detail']


class TestGetResumeDetail:
    """Test suite for GET /v1/resume/detail/{resume_id} endpoint."""

    def test_get_resume_detail_success(self, client, test_db):
        """Test getting resume detail."""
        test_db.execute(text("""
            INSERT INTO resume (resume_id, resume_title, file_name, original_format, is_baseline, is_default, is_active)
            VALUES (1, 'Test Resume', 'test.pdf', 'pdf', true, true, true)
        """))
        test_db.execute(text("""
            INSERT INTO resume_detail (resume_id, resume_markdown, resume_html, keyword_count, focus_count, baseline_score, rewrite_score)
            VALUES (1, '# Resume', '<h1>Resume</h1>', 25, 10, 75, 90)
        """))
        test_db.commit()

        response = client.get("/v1/resume/detail/1")

        assert response.status_code == 200
        detail = response.json()

        assert detail['resume_id'] == 1
        assert detail['resume_markdown'] == '# Resume'
        assert detail['resume_html'] == '<h1>Resume</h1>'
        assert detail['keyword_count'] == 25
        assert detail['focus_count'] == 10
        assert detail['baseline_score'] == 75
        assert detail['rewrite_score'] == 90

    def test_get_resume_detail_not_found(self, client, test_db):
        """Test getting detail for non-existent resume."""
        response = client.get("/v1/resume/detail/999")

        assert response.status_code == 404
        assert "Resume detail not found" in response.json()['detail']


class TestCreateOrUpdateResume:
    """Test suite for POST /v1/resume endpoint."""

    @patch('app.api.resume.update_job_activity')
    def test_create_baseline_resume(self, mock_update_activity, client, test_db):
        """Test creating a baseline resume."""
        # Create a mock PDF file
        pdf_content = b'%PDF-1.4 fake pdf content'
        files = {'upload_file': ('resume.pdf', BytesIO(pdf_content), 'application/pdf')}
        data = {
            'resume_title': 'My Resume',
            'is_baseline': 'true',
            'is_default': 'false'
        }

        response = client.post("/v1/resume", data=data, files=files)

        assert response.status_code == 200
        result = response.json()
        assert result['status'] == 'success'
        assert 'resume_id' in result

        # Verify resume was created
        resume = test_db.execute(text(f"SELECT * FROM resume WHERE resume_id = {result['resume_id']}")).first()
        assert resume.resume_title == 'My Resume'
        assert resume.is_baseline == True
        assert resume.is_default == False
        assert resume.original_format == 'pdf'

    @patch('app.api.resume.update_job_activity')
    def test_create_job_resume(self, mock_update_activity, client, test_db):
        """Test creating a job-specific resume."""
        # Create test job
        test_db.execute(text("""
            INSERT INTO job (job_id, company, job_title, job_status, job_active, job_directory)
            VALUES (1, 'Test Co', 'Engineer', 'applied', true, 'test_co_engineer')
        """))
        test_db.commit()

        html_content = b'<html><body>Resume</body></html>'
        files = {'upload_file': ('resume.html', BytesIO(html_content), 'text/html')}
        data = {
            'resume_title': 'Job Resume',
            'job_id': '1',
            'is_baseline': 'false'
        }

        response = client.post("/v1/resume", data=data, files=files)

        assert response.status_code == 200
        result = response.json()
        assert result['status'] == 'success'

        # Verify resume was created
        resume = test_db.execute(text(f"SELECT * FROM resume WHERE resume_id = {result['resume_id']}")).first()
        assert resume.job_id == 1
        assert resume.is_baseline == False

    def test_create_resume_no_file(self, client, test_db):
        """Test creating resume without file fails."""
        data = {
            'resume_title': 'No File Resume',
            'is_baseline': 'true'
        }

        response = client.post("/v1/resume", data=data)

        assert response.status_code == 400
        assert "upload_file" in response.json()['detail']

    def test_update_resume_set_default(self, client, test_db):
        """Test setting a resume as default."""
        # Create two resumes
        test_db.execute(text("""
            INSERT INTO resume (resume_id, resume_title, file_name, original_format, is_baseline, is_default, is_active)
            VALUES
                (1, 'Resume 1', 'r1.pdf', 'pdf', true, true, true),
                (2, 'Resume 2', 'r2.pdf', 'pdf', true, false, true)
        """))
        test_db.commit()

        data = {
            'resume_id': '2',
            'resume_title': 'Resume 2',
            'is_baseline': 'true',
            'is_default': 'true'
        }

        response = client.post("/v1/resume", data=data)

        assert response.status_code == 200

        # Verify only resume 2 is default
        r1 = test_db.execute(text("SELECT is_default FROM resume WHERE resume_id = 1")).first()
        r2 = test_db.execute(text("SELECT is_default FROM resume WHERE resume_id = 2")).first()
        assert r1.is_default == False
        assert r2.is_default == True


class TestUpdateResumeJSON:
    """Test suite for PUT /v1/resume endpoint."""

    @patch('app.api.resume.update_job_activity')
    def test_update_resume_json_success(self, mock_update_activity, client, test_db):
        """Test updating resume via JSON."""
        test_db.execute(text("""
            INSERT INTO resume (resume_id, resume_title, file_name, original_format, is_baseline, is_default, is_active)
            VALUES (1, 'Old Title', 'old.pdf', 'pdf', true, false, true)
        """))
        test_db.commit()

        update_data = {
            'resume_id': 1,
            'resume_title': 'New Title',
            'is_default': True
        }

        response = client.put("/v1/resume", json=update_data)

        assert response.status_code == 200
        assert response.json()['status'] == 'success'

        # Verify update
        resume = test_db.execute(text("SELECT * FROM resume WHERE resume_id = 1")).first()
        assert resume.resume_title == 'New Title'
        assert resume.is_default == True

    def test_update_resume_json_not_found(self, client, test_db):
        """Test updating non-existent resume."""
        update_data = {
            'resume_id': 999,
            'resume_title': 'Does Not Exist'
        }

        response = client.put("/v1/resume", json=update_data)

        assert response.status_code == 404

    def test_update_resume_json_missing_id(self, client, test_db):
        """Test updating without resume_id."""
        update_data = {
            'resume_title': 'No ID'
        }

        response = client.put("/v1/resume", json=update_data)

        assert response.status_code == 400
        assert "resume_id is required" in response.json()['detail']


class TestCreateOrUpdateResumeDetail:
    """Test suite for POST /v1/resume/detail endpoint."""

    def test_create_resume_detail_success(self, client, test_db):
        """Test creating resume detail."""
        test_db.execute(text("""
            INSERT INTO resume (resume_id, resume_title, file_name, original_format, is_baseline, is_default, is_active)
            VALUES (1, 'Test Resume', 'test.pdf', 'pdf', true, true, true)
        """))
        test_db.commit()

        detail_data = {
            'resume_id': 1,
            'resume_markdown': '# My Resume\n\nExperience...',
            'resume_html': '<h1>My Resume</h1><p>Experience...</p>',
            'position_title': 'Software Engineer',
            'resume_keyword': ['Python', 'React', 'AWS'],
            'keyword_final': ['Python', 'React'],
            'focus_final': ['AWS'],
            'keyword_count': 3,
            'focus_count': 1
        }

        response = client.post("/v1/resume/detail", json=detail_data)

        assert response.status_code == 200
        assert response.json()['status'] == 'success'

        # Verify detail was created
        detail = test_db.execute(text("SELECT * FROM resume_detail WHERE resume_id = 1")).first()
        assert detail.resume_markdown == '# My Resume\n\nExperience...'
        assert detail.position_title == 'Software Engineer'
        assert detail.keyword_count == 3

    def test_update_resume_detail_success(self, client, test_db):
        """Test updating existing resume detail."""
        test_db.execute(text("""
            INSERT INTO resume (resume_id, resume_title, file_name, original_format, is_baseline, is_default, is_active)
            VALUES (1, 'Test Resume', 'test.pdf', 'pdf', true, true, true)
        """))
        test_db.execute(text("""
            INSERT INTO resume_detail (resume_id, resume_markdown, keyword_count)
            VALUES (1, '# Old', 5)
        """))
        test_db.commit()

        detail_data = {
            'resume_id': 1,
            'resume_markdown': '# Updated',
            'keyword_count': 10
        }

        response = client.post("/v1/resume/detail", json=detail_data)

        assert response.status_code == 200

        # Verify update
        detail = test_db.execute(text("SELECT * FROM resume_detail WHERE resume_id = 1")).first()
        assert detail.resume_markdown == '# Updated'
        assert detail.keyword_count == 10

    def test_create_resume_detail_resume_not_found(self, client, test_db):
        """Test creating detail for non-existent resume."""
        detail_data = {
            'resume_id': 999,
            'resume_markdown': '# Resume'
        }

        response = client.post("/v1/resume/detail", json=detail_data)

        assert response.status_code == 404


class TestDeleteResume:
    """Test suite for DELETE /v1/resume endpoint."""

    def test_delete_resume_success(self, client, test_db):
        """Test deleting a resume."""
        test_db.execute(text("""
            INSERT INTO resume (resume_id, resume_title, file_name, original_format, is_baseline, is_default, is_active)
            VALUES (1, 'Delete Me', 'delete.pdf', 'pdf', true, false, true)
        """))
        test_db.commit()

        response = client.delete("/v1/resume?resume_id=1")

        assert response.status_code == 200
        assert response.json()['status'] == 'success'

        # Verify soft delete
        resume = test_db.execute(text("SELECT is_active FROM resume WHERE resume_id = 1")).first()
        assert resume.is_active == False

    def test_delete_resume_not_found(self, client, test_db):
        """Test deleting non-existent resume."""
        response = client.delete("/v1/resume?resume_id=999")

        assert response.status_code == 404


class TestCloneResume:
    """Test suite for POST /v1/resume/clone endpoint."""

    def test_clone_baseline_resume(self, client, test_db):
        """Test cloning a baseline resume."""
        # Create original resume
        test_db.execute(text("""
            INSERT INTO resume (resume_id, resume_title, file_name, original_format, is_baseline, is_default, is_active)
            VALUES (1, 'Original', 'original.pdf', 'pdf', true, true, true)
        """))
        test_db.execute(text("""
            INSERT INTO resume_detail (resume_id, resume_markdown, keyword_count)
            VALUES (1, '# Original Resume', 10)
        """))
        test_db.commit()

        response = client.post("/v1/resume/clone", json={'resume_id': 1})

        assert response.status_code == 200
        result = response.json()

        # Verify clone was created
        clone = test_db.execute(text(f"SELECT * FROM resume WHERE resume_id = {result['resume_id']}")).first()
        assert clone.resume_title == 'Original (1)'
        assert clone.is_baseline == True
        assert clone.is_default == False  # Clone should not be default

        # Verify detail was cloned
        clone_detail = test_db.execute(text(f"SELECT * FROM resume_detail WHERE resume_id = {result['resume_id']}")).first()
        assert clone_detail.resume_markdown == '# Original Resume'

    def test_clone_resume_not_found(self, client, test_db):
        """Test cloning non-existent resume."""
        response = client.post("/v1/resume/clone", json={'resume_id': 999})

        assert response.status_code == 404


class TestResumeExtraction:
    """Test suite for POST /v1/resume/extract endpoint."""

    @patch('app.utils.ai_agent.AiAgent.resume_extraction')
    @patch('app.api.resume._convert_to_markdown')
    def test_extract_resume_success(self, mock_convert, mock_extraction, client, test_db):
        """Test successful resume extraction."""
        # Create test resume
        test_db.execute(text("""
            INSERT INTO resume (resume_id, resume_title, file_name, original_format, is_baseline, is_default, is_active)
            VALUES (1, 'Test Resume', 'test.pdf', 'pdf', true, true, true)
        """))
        test_db.commit()

        # Mock conversion
        mock_convert.return_value = '# Software Engineer\n\nExperience with Python and React'

        # Mock AI extraction
        mock_extraction.return_value = {
            'position_title': 'Software Engineer',
            'title_line_no': 1,
            'keywords': ['Python', 'React', 'AWS']
        }

        response = client.post("/v1/resume/extract", json={'resume_id': 1})

        assert response.status_code == 200
        data = response.json()

        assert data['position_title'] == 'Software Engineer'
        assert data['title_line_no'] == 1
        assert 'Python' in data['keywords']

    def test_extract_resume_not_found(self, client, test_db):
        """Test extraction with non-existent resume."""
        response = client.post("/v1/resume/extract", json={'resume_id': 999})

        assert response.status_code == 404


class TestResumeRewrite:
    """Test suite for POST /v1/resume/rewrite endpoint (async version with background threading)."""

    def test_rewrite_resume_initiates_process(self, client, test_db):
        """Test that resume rewrite initiates a background process and returns 202 with process_id."""
        # Create test job with job_detail
        test_db.execute(text("""
            INSERT INTO job (job_id, company, job_title, job_status, job_active, job_directory)
            VALUES (1, 'Test Co', 'Engineer', 'applied', true, 'test_co_engineer')
        """))
        test_db.execute(text("""
            INSERT INTO job_detail (job_id, job_desc, job_keyword)
            VALUES (1, 'Test job description', ARRAY['Python', 'AWS'])
        """))
        # Create baseline resume and associate with job
        test_db.execute(text("""
            INSERT INTO resume (resume_id, resume_title, file_name, original_format, is_baseline, is_default, is_active)
            VALUES (1, 'Baseline', 'baseline.html', 'html', true, true, true)
        """))
        test_db.execute(text("""
            INSERT INTO resume_detail (resume_id, resume_html, keyword_final, focus_final, baseline_score)
            VALUES (1, '<h1>Resume Content</h1>', ARRAY['Python'], ARRAY['AWS'], 75)
        """))
        test_db.execute(text("""
            UPDATE job SET resume_id = 1 WHERE job_id = 1
        """))
        test_db.commit()

        rewrite_data = {
            'job_id': 1
        }

        response = client.post("/v1/resume/rewrite", json=rewrite_data)

        # Should return 202 Accepted with process_id
        assert response.status_code == 202
        data = response.json()
        assert 'process_id' in data
        assert isinstance(data['process_id'], int)

        # Verify process record was created
        process = test_db.execute(
            text("SELECT * FROM process WHERE process_id = :pid"),
            {"pid": data['process_id']}
        ).first()
        assert process is not None
        assert process.endpoint_called == '/v1/resume/rewrite'
        assert process.running_method == 'resume_rewrite_process'
        assert process.running_class == 'AiAgent'

    def test_rewrite_resume_job_not_found(self, client, test_db):
        """Test rewrite with non-existent job."""
        response = client.post("/v1/resume/rewrite", json={'job_id': 999})

        assert response.status_code == 404

    def test_rewrite_resume_no_resume_associated(self, client, test_db):
        """Test rewrite with job that has no resume."""
        # Create job without resume
        test_db.execute(text("""
            INSERT INTO job (job_id, company, job_title, job_status, job_active, job_directory)
            VALUES (1, 'Test Co', 'Engineer', 'applied', true, 'test_co_engineer')
        """))
        test_db.commit()

        response = client.post("/v1/resume/rewrite", json={'job_id': 1})

        assert response.status_code == 400
        assert 'no resume' in response.json()['detail'].lower()

    def test_rewrite_returns_immediately_without_blocking(self, client, test_db):
        """
        Test that the rewrite endpoint returns 202 immediately without waiting for
        the background thread to complete, ensuring HTTP connection is not blocked.
        """
        import time

        # Create test job with job_detail
        test_db.execute(text("""
            INSERT INTO job (job_id, company, job_title, job_status, job_active, job_directory)
            VALUES (1, 'Test Co', 'Engineer', 'applied', true, 'test_co_engineer')
        """))
        test_db.execute(text("""
            INSERT INTO job_detail (job_id, job_desc, job_keyword)
            VALUES (1, 'Test job description', ARRAY['Python', 'AWS'])
        """))
        # Create baseline resume and associate with job
        test_db.execute(text("""
            INSERT INTO resume (resume_id, resume_title, file_name, original_format, is_baseline, is_default, is_active)
            VALUES (1, 'Baseline', 'baseline.html', 'html', true, true, true)
        """))
        test_db.execute(text("""
            INSERT INTO resume_detail (resume_id, resume_html, keyword_final, focus_final, baseline_score)
            VALUES (1, '<h1>Resume Content</h1>', ARRAY['Python'], ARRAY['AWS'], 75)
        """))
        test_db.execute(text("""
            UPDATE job SET resume_id = 1 WHERE job_id = 1
        """))
        test_db.commit()

        # Measure response time
        start_time = time.time()
        response = client.post("/v1/resume/rewrite", json={'job_id': 1})
        response_time = time.time() - start_time

        # Should return 202 Accepted immediately (within 2 seconds)
        assert response.status_code == 202
        assert response_time < 2.0, f"Response took {response_time}s - endpoint is blocking!"

        data = response.json()
        assert 'process_id' in data

        # Verify process record exists and is in running state
        process = test_db.execute(
            text("SELECT * FROM process WHERE process_id = :pid"),
            {"pid": data['process_id']}
        ).first()
        assert process is not None
        assert process.endpoint_called == '/v1/resume/rewrite'
        # Process should not be completed yet since AI call takes time
        assert process.completed is None


class TestGetRewriteData:
    """Test suite for GET /v1/resume/rewrite/{job_id} endpoint."""

    def test_get_rewrite_data_success(self, client, test_db):
        """Test retrieving resume rewrite data after process completes."""
        # Create test job
        test_db.execute(text("""
            INSERT INTO job (job_id, company, job_title, job_status, job_active, job_directory)
            VALUES (1, 'Test Co', 'Engineer', 'applied', true, 'test_co_engineer')
        """))
        # Create resume with rewrite data
        test_db.execute(text("""
            INSERT INTO resume (resume_id, resume_title, file_name, original_format, is_baseline, is_default, is_active)
            VALUES (1, 'Test Resume', 'test.html', 'html', false, false, true)
        """))
        test_db.execute(text("""
            INSERT INTO resume_detail (resume_id, resume_html, resume_html_rewrite, suggestion, baseline_score, rewrite_score)
            VALUES (1, '<h1>Original</h1>', '<h1>Rewritten</h1>', ARRAY['Suggestion 1', 'Suggestion 2'], 75, 92)
        """))
        test_db.execute(text("""
            UPDATE job SET resume_id = 1 WHERE job_id = 1
        """))
        test_db.commit()

        response = client.get("/v1/resume/rewrite/1")

        assert response.status_code == 200
        data = response.json()
        assert data['resume_id'] == 1
        assert data['resume_html'] == '<h1>Original</h1>'
        assert data['resume_html_rewrite'] == '<h1>Rewritten</h1>'
        assert data['suggestion'] == ['Suggestion 1', 'Suggestion 2']
        assert data['baseline_score'] == 75
        assert data['rewrite_score'] == 92

    def test_get_rewrite_data_job_not_found(self, client, test_db):
        """Test retrieving data for non-existent job."""
        response = client.get("/v1/resume/rewrite/999")

        assert response.status_code == 404
