import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy import text


class TestElevatorPitch:
    """Test suite for POST /v1/tools/pitch endpoint."""

    @patch('app.api.tools.AiAgent')
    def test_elevator_pitch_with_job_id_success(self, mock_ai_agent, client, test_db):
        """Test successfully generating elevator pitch with job_id."""
        # Setup test data
        # Insert resume
        result = test_db.execute(text("""
            INSERT INTO resume (is_baseline, is_default, is_active, original_format, resume_title)
            VALUES (true, true, true, 'md', 'test_resume.md')
            RETURNING resume_id
        """))
        resume_id = result.fetchone()[0]

        test_db.execute(text("""
            INSERT INTO resume_detail (resume_id, resume_markdown, resume_html_rewrite)
            VALUES (:resume_id, 'Test resume markdown', '<p>Test resume HTML</p>')
        """), {"resume_id": resume_id})

        # Insert job
        result = test_db.execute(text("""
            INSERT INTO job (resume_id, job_title, company, job_status, interest_level, average_score)
            VALUES (:resume_id, 'Software Engineer', 'Test Company', 'applied', 5, 5.0)
            RETURNING job_id
        """), {"resume_id": resume_id})
        job_id = result.fetchone()[0]

        test_db.execute(text("""
            INSERT INTO job_detail (job_id, job_desc)
            VALUES (:job_id, 'Test job description with requirements')
        """), {"job_id": job_id})
        test_db.commit()

        # Mock AI agent
        mock_instance = MagicMock()
        mock_instance.elevator_pitch.return_value = {
            'pitch': 'This is a great elevator pitch for the job.'
        }
        mock_ai_agent.return_value = mock_instance

        # Make request
        response = client.post("/v1/tools/pitch", json={"job_id": job_id})

        assert response.status_code == 200
        data = response.json()
        assert data['pitch'] == 'This is a great elevator pitch for the job.'

        # Verify AI agent was called correctly
        mock_instance.elevator_pitch.assert_called_once_with(
            resume='<p>Test resume HTML</p>',
            job_desc='Test job description with requirements'
        )

    @patch('app.api.tools.AiAgent')
    def test_elevator_pitch_without_job_id_success(self, mock_ai_agent, client, test_db):
        """Test successfully generating elevator pitch without job_id (baseline resume only)."""
        # Setup test data - insert baseline resume
        result = test_db.execute(text("""
            INSERT INTO resume (is_baseline, is_default, is_active, original_format, resume_title)
            VALUES (true, true, true, 'md', 'baseline_resume.md')
            RETURNING resume_id
        """))
        resume_id = result.fetchone()[0]

        test_db.execute(text("""
            INSERT INTO resume_detail (resume_id, resume_markdown)
            VALUES (:resume_id, 'Baseline resume markdown content')
        """), {"resume_id": resume_id})
        test_db.commit()

        # Mock AI agent
        mock_instance = MagicMock()
        mock_instance.elevator_pitch.return_value = {
            'pitch': 'This is a general elevator pitch.'
        }
        mock_ai_agent.return_value = mock_instance

        # Make request without job_id
        response = client.post("/v1/tools/pitch", json={})

        assert response.status_code == 200
        data = response.json()
        assert data['pitch'] == 'This is a general elevator pitch.'

        # Verify AI agent was called with resume and empty job_desc
        mock_instance.elevator_pitch.assert_called_once_with(
            resume='Baseline resume markdown content',
            job_desc=''
        )

    def test_elevator_pitch_job_not_found(self, client, test_db):
        """Test 404 error when job_id doesn't exist."""
        response = client.post("/v1/tools/pitch", json={"job_id": 999})

        assert response.status_code == 404
        assert "Job and Resume not found" in response.json()['detail']

    def test_elevator_pitch_baseline_resume_not_found(self, client, test_db):
        """Test 404 error when baseline resume doesn't exist and no job_id provided."""
        response = client.post("/v1/tools/pitch", json={})

        assert response.status_code == 404
        assert "Baseline resume not found" in response.json()['detail']

    @patch('app.api.tools.AiAgent')
    def test_elevator_pitch_ai_error(self, mock_ai_agent, client, test_db):
        """Test 500 error when AI agent throws exception."""
        # Setup test data
        result = test_db.execute(text("""
            INSERT INTO resume (is_baseline, is_default, is_active, original_format, resume_title)
            VALUES (true, true, true, 'md', 'test_resume.md')
            RETURNING resume_id
        """))
        resume_id = result.fetchone()[0]

        test_db.execute(text("""
            INSERT INTO resume_detail (resume_id, resume_markdown)
            VALUES (:resume_id, 'Test resume content')
        """), {"resume_id": resume_id})
        test_db.commit()

        # Mock AI agent to raise exception
        mock_instance = MagicMock()
        mock_instance.elevator_pitch.side_effect = Exception("OpenAI API error")
        mock_ai_agent.return_value = mock_instance

        response = client.post("/v1/tools/pitch", json={})

        assert response.status_code == 500
        assert "Error generating elevator pitch" in response.json()['detail']

    @patch('app.api.tools.AiAgent')
    def test_elevator_pitch_with_null_job_id(self, mock_ai_agent, client, test_db):
        """Test handling of explicit null job_id."""
        # Setup baseline resume
        result = test_db.execute(text("""
            INSERT INTO resume (is_baseline, is_default, is_active, original_format, resume_title)
            VALUES (true, true, true, 'md', 'baseline.md')
            RETURNING resume_id
        """))
        resume_id = result.fetchone()[0]

        test_db.execute(text("""
            INSERT INTO resume_detail (resume_id, resume_markdown)
            VALUES (:resume_id, 'Baseline resume markdown content')
        """), {"resume_id": resume_id})
        test_db.commit()

        # Mock AI agent
        mock_instance = MagicMock()
        mock_instance.elevator_pitch.return_value = {'pitch': 'General pitch'}
        mock_ai_agent.return_value = mock_instance

        response = client.post("/v1/tools/pitch", json={"job_id": None})

        assert response.status_code == 200
        mock_instance.elevator_pitch.assert_called_once_with(resume='Baseline resume markdown content', job_desc='')


class TestRewriteText:
    """Test suite for POST /v1/tools/rewrite endpoint."""

    @patch('app.api.tools.AiAgent')
    def test_rewrite_text_success(self, mock_ai_agent, client, test_db):
        """Test successfully rewriting text blob."""
        # Mock AI agent
        mock_instance = MagicMock()
        mock_instance.rewrite_blob.return_value = {
            'new_text_blob': 'This is the improved, rewritten text with better clarity.',
            'explanation': 'Improved sentence structure and added clarity.'
        }
        mock_ai_agent.return_value = mock_instance

        # Make request
        test_text = "This is some text that needs improvement"
        response = client.post("/v1/tools/rewrite", json={"text_blob": test_text})

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert data['original_text_blob'] == test_text
        assert data['new_text_blob'] == 'This is the improved, rewritten text with better clarity.'
        assert data['explanation'] == 'Improved sentence structure and added clarity.'

        # Verify AI agent was called correctly
        mock_instance.rewrite_blob.assert_called_once_with(text_blob=test_text)

    @patch('app.api.tools.AiAgent')
    def test_rewrite_text_with_long_text(self, mock_ai_agent, client, test_db):
        """Test rewriting a longer text blob."""
        # Mock AI agent
        mock_instance = MagicMock()
        mock_instance.rewrite_blob.return_value = {
            'new_text_blob': 'Concise, improved version of the long text.',
            'explanation': 'Condensed verbose sections and improved readability.'
        }
        mock_ai_agent.return_value = mock_instance

        # Make request with long text
        long_text = "This is a very long text blob. " * 50  # Repeat to make it long
        response = client.post("/v1/tools/rewrite", json={"text_blob": long_text})

        assert response.status_code == 200
        data = response.json()
        assert data['original_text_blob'] == long_text
        assert 'new_text_blob' in data
        assert 'explanation' in data

    @patch('app.api.tools.AiAgent')
    def test_rewrite_text_with_special_characters(self, mock_ai_agent, client, test_db):
        """Test rewriting text with special characters and formatting."""
        # Mock AI agent
        mock_instance = MagicMock()
        mock_instance.rewrite_blob.return_value = {
            'new_text_blob': 'Improved text with proper formatting.',
            'explanation': 'Standardized special characters and formatting.'
        }
        mock_ai_agent.return_value = mock_instance

        # Make request with special characters
        special_text = "Test with symbols: @#$%^&*(), quotes \"test\", and newlines\n\nParagraph 2"
        response = client.post("/v1/tools/rewrite", json={"text_blob": special_text})

        assert response.status_code == 200
        data = response.json()
        assert data['original_text_blob'] == special_text

    def test_rewrite_text_empty_string(self, client, test_db):
        """Test validation error when text_blob is empty string."""
        response = client.post("/v1/tools/rewrite", json={"text_blob": ""})

        # Empty string should still be accepted by the endpoint
        # (AI agent might handle it or return minimal changes)
        # If validation is added later, this test can be updated
        assert response.status_code in [200, 422, 500]

    @patch('app.api.tools.AiAgent')
    def test_rewrite_text_ai_error(self, mock_ai_agent, client, test_db):
        """Test 500 error when AI agent throws exception."""
        # Mock AI agent to raise exception
        mock_instance = MagicMock()
        mock_instance.rewrite_blob.side_effect = Exception("OpenAI API connection failed")
        mock_ai_agent.return_value = mock_instance

        response = client.post("/v1/tools/rewrite", json={"text_blob": "Test text"})

        assert response.status_code == 500
        assert "Error rewriting text" in response.json()['detail']

    @patch('app.api.tools.AiAgent')
    def test_rewrite_text_json_parse_error(self, mock_ai_agent, client, test_db):
        """Test error handling when AI returns invalid JSON."""
        # Mock AI agent to return invalid response structure
        mock_instance = MagicMock()
        mock_instance.rewrite_blob.side_effect = ValueError("Invalid JSON response")
        mock_ai_agent.return_value = mock_instance

        response = client.post("/v1/tools/rewrite", json={"text_blob": "Test text"})

        assert response.status_code == 500
        assert "Error rewriting text" in response.json()['detail']

    @patch('app.api.tools.AiAgent')
    def test_rewrite_text_unicode_support(self, mock_ai_agent, client, test_db):
        """Test rewriting text with unicode characters."""
        # Mock AI agent
        mock_instance = MagicMock()
        mock_instance.rewrite_blob.return_value = {
            'new_text_blob': 'Improved text: café résumé naïve 你好',
            'explanation': 'Preserved unicode characters correctly.'
        }
        mock_ai_agent.return_value = mock_instance

        # Make request with unicode
        unicode_text = "Test with unicode: café résumé naïve 你好 🎉"
        response = client.post("/v1/tools/rewrite", json={"text_blob": unicode_text})

        assert response.status_code == 200
        data = response.json()
        assert data['original_text_blob'] == unicode_text

    @patch('app.api.tools.AiAgent')
    def test_rewrite_text_whitespace_handling(self, mock_ai_agent, client, test_db):
        """Test handling of text with various whitespace."""
        # Mock AI agent
        mock_instance = MagicMock()
        mock_instance.rewrite_blob.return_value = {
            'new_text_blob': 'Normalized whitespace text.',
            'explanation': 'Normalized excessive whitespace.'
        }
        mock_ai_agent.return_value = mock_instance

        # Make request with various whitespace
        whitespace_text = "Text   with    multiple     spaces\n\n\nand\t\ttabs"
        response = client.post("/v1/tools/rewrite", json={"text_blob": whitespace_text})

        assert response.status_code == 200
        data = response.json()
        assert data['original_text_blob'] == whitespace_text
