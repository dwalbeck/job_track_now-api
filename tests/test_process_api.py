import pytest
from sqlalchemy import text
from datetime import datetime


class TestPollStatus:
    """Test suite for GET /v1/process/poll/{process_id} endpoint."""

    def test_poll_running_process(self, client, test_db):
        """Test polling a process that is still running."""
        # Create a running process
        test_db.execute(text("""
            INSERT INTO process (process_id, endpoint_called, running_method, running_class, confirmed, failed)
            VALUES (1, '/v1/resume/rewrite', 'resume_rewrite_process', 'AiAgent', false, false)
        """))
        test_db.commit()

        response = client.get("/v1/process/poll/1")

        assert response.status_code == 200
        data = response.json()
        assert data['process_state'] == 'running'

    def test_poll_completed_process(self, client, test_db):
        """Test polling a process that has completed."""
        # Create a completed process
        test_db.execute(text("""
            INSERT INTO process (process_id, endpoint_called, running_method, running_class, completed, confirmed, failed)
            VALUES (1, '/v1/resume/rewrite', 'resume_rewrite_process', 'AiAgent', CURRENT_TIMESTAMP, false, false)
        """))
        test_db.commit()

        response = client.get("/v1/process/poll/1")

        assert response.status_code == 200
        data = response.json()
        assert data['process_state'] == 'complete'

        # Verify that the process was marked as confirmed
        result = test_db.execute(text("SELECT confirmed FROM process WHERE process_id = 1")).first()
        assert result.confirmed is True

    def test_poll_failed_process(self, client, test_db):
        """Test polling a process that has failed."""
        # Create a failed process
        test_db.execute(text("""
            INSERT INTO process (process_id, endpoint_called, running_method, running_class, failed, completed, confirmed)
            VALUES (1, '/v1/resume/rewrite', 'resume_rewrite_process', 'AiAgent', true, CURRENT_TIMESTAMP, false)
        """))
        test_db.commit()

        response = client.get("/v1/process/poll/1")

        assert response.status_code == 200
        data = response.json()
        assert data['process_state'] == 'failed'

    def test_poll_confirmed_process(self, client, test_db):
        """Test polling a process that has already been confirmed."""
        # Create a confirmed process
        test_db.execute(text("""
            INSERT INTO process (process_id, endpoint_called, running_method, running_class, completed, confirmed, failed)
            VALUES (1, '/v1/resume/rewrite', 'resume_rewrite_process', 'AiAgent', CURRENT_TIMESTAMP, true, false)
        """))
        test_db.commit()

        response = client.get("/v1/process/poll/1")

        assert response.status_code == 200
        data = response.json()
        assert data['process_state'] == 'confirmed'

    def test_poll_nonexistent_process(self, client, test_db):
        """Test polling a process that doesn't exist."""
        response = client.get("/v1/process/poll/999")

        assert response.status_code == 404
        data = response.json()
        assert 'detail' in data
        assert data['detail'] == 'Process not found'
