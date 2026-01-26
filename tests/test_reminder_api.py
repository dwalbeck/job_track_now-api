import pytest
from sqlalchemy import text
from datetime import date, time, timedelta


# Helper to get test user ID
def get_test_user_id(test_db):
    result = test_db.execute(text("SELECT user_id FROM users WHERE login = 'testuser'")).first()
    return result.user_id if result else 1


class TestCreateOrUpdateReminder:
    """Test suite for POST /v1/reminder endpoint."""

    def test_create_reminder_without_job(self, client, test_db):
        """Test creating a reminder without linking to a job."""
        reminder_data = {
            "reminder_date": "2025-01-20",
            "reminder_time": "10:00:00",
            "reminder_message": "Follow up on application",
            "reminder_dismissed": False
        }

        response = client.post("/v1/reminder", json=reminder_data)

        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'success'

        # Verify reminder was created
        result = test_db.execute(text("""
            SELECT * FROM reminder
            WHERE reminder_message = 'Follow up on application'
        """)).first()
        assert result is not None
        assert str(result.reminder_date) == '2025-01-20'
        assert result.reminder_dismissed == False
        assert result.job_id is None

    def test_create_reminder_with_job(self, client, test_db):
        """Test creating a reminder linked to a job."""
        user_id = get_test_user_id(test_db)
        # Create test job
        test_db.execute(text("""
            INSERT INTO job (job_id, user_id, company, job_title, job_status, job_active, job_directory)
            VALUES (1, :user_id, 'Test Co', 'Engineer', 'applied', true, 'test_co_engineer')
        """), {"user_id": user_id})
        test_db.commit()

        reminder_data = {
            "reminder_date": "2025-01-25",
            "reminder_time": "14:30:00",
            "reminder_message": "Prepare for interview",
            "reminder_dismissed": False,
            "job_id": 1
        }

        response = client.post("/v1/reminder", json=reminder_data)

        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'success'

        # Verify reminder was created with job link
        result = test_db.execute(text("""
            SELECT * FROM reminder
            WHERE reminder_message = 'Prepare for interview'
        """)).first()
        assert result is not None
        assert result.job_id == 1
        assert str(result.reminder_time) == '14:30:00'

    def test_create_reminder_dismissed(self, client, test_db):
        """Test creating a dismissed reminder."""
        reminder_data = {
            "reminder_date": "2025-01-15",
            "reminder_time": "09:00:00",
            "reminder_message": "Already handled",
            "reminder_dismissed": True
        }

        response = client.post("/v1/reminder", json=reminder_data)

        assert response.status_code == 200

        # Verify reminder was created as dismissed
        result = test_db.execute(text("""
            SELECT * FROM reminder
            WHERE reminder_message = 'Already handled'
        """)).first()
        assert result.reminder_dismissed == True

    def test_update_reminder_success(self, client, test_db):
        """Test updating an existing reminder."""
        user_id = get_test_user_id(test_db)
        # Create initial reminder
        test_db.execute(text("""
            INSERT INTO reminder (reminder_id, user_id, reminder_date, reminder_time, reminder_message, reminder_dismissed)
            VALUES (1, :user_id, '2025-01-20', '10:00:00', 'Original message', false)
        """), {"user_id": user_id})
        test_db.commit()

        update_data = {
            "reminder_id": 1,
            "reminder_date": "2025-01-22",
            "reminder_time": "15:00:00",
            "reminder_message": "Updated message",
            "reminder_dismissed": False
        }

        response = client.post("/v1/reminder", json=update_data)

        assert response.status_code == 200
        assert response.json()['status'] == 'success'

        # Verify reminder was updated
        result = test_db.execute(text("SELECT * FROM reminder WHERE reminder_id = 1")).first()
        assert str(result.reminder_date) == '2025-01-22'
        assert str(result.reminder_time) == '15:00:00'
        assert result.reminder_message == 'Updated message'

    def test_update_reminder_dismiss(self, client, test_db):
        """Test dismissing a reminder."""
        user_id = get_test_user_id(test_db)
        # Create test job
        test_db.execute(text("""
            INSERT INTO job (job_id, user_id, company, job_title, job_status, job_active, job_directory)
            VALUES (1, :user_id, 'Test Co', 'Engineer', 'applied', true, 'test_co_engineer')
        """), {"user_id": user_id})
        # Create initial reminder
        test_db.execute(text("""
            INSERT INTO reminder (reminder_id, user_id, reminder_date, reminder_time, reminder_message, reminder_dismissed, job_id)
            VALUES (1, :user_id, '2025-01-20', '10:00:00', 'Follow up', false, 1)
        """), {"user_id": user_id})
        test_db.commit()

        update_data = {
            "reminder_id": 1,
            "reminder_date": "2025-01-20",
            "reminder_time": "10:00:00",
            "reminder_message": "Follow up",
            "reminder_dismissed": True,
            "job_id": 1
        }

        response = client.post("/v1/reminder", json=update_data)

        assert response.status_code == 200

        # Verify reminder was dismissed
        result = test_db.execute(text("SELECT * FROM reminder WHERE reminder_id = 1")).first()
        assert result.reminder_dismissed == True

    def test_update_reminder_change_job_link(self, client, test_db):
        """Test updating a reminder's job link."""
        user_id = get_test_user_id(test_db)
        # Create test jobs
        test_db.execute(text("""
            INSERT INTO job (job_id, user_id, company, job_title, job_status, job_active, job_directory)
            VALUES
                (1, :user_id, 'Company A', 'Engineer', 'applied', true, 'company_a_engineer'),
                (2, :user_id, 'Company B', 'Developer', 'interviewing', true, 'company_b_developer')
        """), {"user_id": user_id})
        # Create initial reminder linked to job 1
        test_db.execute(text("""
            INSERT INTO reminder (reminder_id, user_id, reminder_date, reminder_time, reminder_message, reminder_dismissed, job_id)
            VALUES (1, :user_id, '2025-01-20', '10:00:00', 'Interview prep', false, 1)
        """), {"user_id": user_id})
        test_db.commit()

        # Update to link to job 2
        update_data = {
            "reminder_id": 1,
            "reminder_date": "2025-01-20",
            "reminder_time": "10:00:00",
            "reminder_message": "Interview prep",
            "reminder_dismissed": False,
            "job_id": 2
        }

        response = client.post("/v1/reminder", json=update_data)

        assert response.status_code == 200

        # Verify job link was updated
        result = test_db.execute(text("SELECT * FROM reminder WHERE reminder_id = 1")).first()
        assert result.job_id == 2

    def test_create_reminder_missing_required_fields(self, client, test_db):
        """Test creating a reminder with missing required fields."""
        # Missing reminder_date
        reminder_data = {
            "reminder_time": "10:00:00",
            "reminder_message": "Test"
        }

        response = client.post("/v1/reminder", json=reminder_data)

        # Should fail validation
        assert response.status_code == 422


class TestDeleteReminder:
    """Test suite for DELETE /v1/reminder endpoint."""

    def test_delete_reminder_success(self, client, test_db):
        """Test successfully deleting a reminder."""
        user_id = get_test_user_id(test_db)
        # Create test reminder
        test_db.execute(text("""
            INSERT INTO reminder (reminder_id, user_id, reminder_date, reminder_time, reminder_message, reminder_dismissed)
            VALUES (1, :user_id, '2025-01-20', '10:00:00', 'Delete me', false)
        """), {"user_id": user_id})
        test_db.commit()

        response = client.delete("/v1/reminder?reminder_id=1")

        assert response.status_code == 200
        assert response.json()['status'] == 'success'

        # Verify reminder was deleted (hard delete)
        result = test_db.execute(text("SELECT * FROM reminder WHERE reminder_id = 1")).first()
        assert result is None

    def test_delete_reminder_not_found(self, client, test_db):
        """Test deleting non-existent reminder."""
        response = client.delete("/v1/reminder?reminder_id=999")

        assert response.status_code == 404
        assert "Reminder not found" in response.json()['detail']

    def test_delete_reminder_with_job_link(self, client, test_db):
        """Test deleting a reminder that is linked to a job."""
        user_id = get_test_user_id(test_db)
        # Create test job and reminder
        test_db.execute(text("""
            INSERT INTO job (job_id, user_id, company, job_title, job_status, job_active, job_directory)
            VALUES (1, :user_id, 'Test Co', 'Engineer', 'applied', true, 'test_co_engineer')
        """), {"user_id": user_id})
        test_db.execute(text("""
            INSERT INTO reminder (reminder_id, user_id, reminder_date, reminder_time, reminder_message, reminder_dismissed, job_id)
            VALUES (1, :user_id, '2025-01-20', '10:00:00', 'Interview reminder', false, 1)
        """), {"user_id": user_id})
        test_db.commit()

        response = client.delete("/v1/reminder?reminder_id=1")

        assert response.status_code == 200
        assert response.json()['status'] == 'success'

        # Verify reminder was deleted
        result = test_db.execute(text("SELECT * FROM reminder WHERE reminder_id = 1")).first()
        assert result is None

        # Verify job still exists
        job = test_db.execute(text("SELECT * FROM job WHERE job_id = 1")).first()
        assert job is not None


class TestListReminders:
    """Test suite for POST /v1/reminder/list endpoint."""

    def test_list_reminders_day_duration(self, client, test_db):
        """Test listing reminders for a single day."""
        user_id = get_test_user_id(test_db)
        # Create test job
        test_db.execute(text("""
            INSERT INTO job (job_id, user_id, company, job_title, job_status, job_active, job_directory)
            VALUES (1, :user_id, 'Test Co', 'Engineer', 'applied', true, 'test_co_engineer')
        """), {"user_id": user_id})
        # Create reminders on different days
        test_db.execute(text("""
            INSERT INTO reminder (reminder_id, user_id, reminder_date, reminder_time, reminder_message, reminder_dismissed, job_id)
            VALUES
                (1, :user_id, '2025-01-20', '10:00:00', 'Same day morning', false, 1),
                (2, :user_id, '2025-01-20', '15:00:00', 'Same day afternoon', false, 1),
                (3, :user_id, '2025-01-21', '10:00:00', 'Next day', false, 1)
        """), {"user_id": user_id})
        test_db.commit()

        list_data = {
            "duration": "day",
            "start_date": "2025-01-20"
        }

        response = client.post("/v1/reminder/list", json=list_data)

        assert response.status_code == 200
        reminders = response.json()

        # Should only return reminders for 2025-01-20
        assert len(reminders) == 2
        assert all(r['reminder_date'] == '2025-01-20' for r in reminders)
        # Should be ordered by reminder_time DESC
        assert reminders[0]['reminder_message'] == 'Same day afternoon'
        assert reminders[1]['reminder_message'] == 'Same day morning'

    def test_list_reminders_week_duration(self, client, test_db):
        """Test listing reminders for a week."""
        user_id = get_test_user_id(test_db)
        # Create test job
        test_db.execute(text("""
            INSERT INTO job (job_id, user_id, company, job_title, job_status, job_active, job_directory)
            VALUES (1, :user_id, 'Test Co', 'Engineer', 'applied', true, 'test_co_engineer')
        """), {"user_id": user_id})
        # Create reminders across a week+ period
        test_db.execute(text("""
            INSERT INTO reminder (reminder_id, user_id, reminder_date, reminder_time, reminder_message, reminder_dismissed, job_id)
            VALUES
                (1, :user_id, '2025-01-20', '10:00:00', 'Day 1', false, 1),
                (2, :user_id, '2025-01-22', '10:00:00', 'Day 3', false, 1),
                (3, :user_id, '2025-01-26', '10:00:00', 'Day 7', false, 1),
                (4, :user_id, '2025-01-28', '10:00:00', 'Outside range', false, 1)
        """), {"user_id": user_id})
        test_db.commit()

        list_data = {
            "duration": "week",
            "start_date": "2025-01-20"
        }

        response = client.post("/v1/reminder/list", json=list_data)

        assert response.status_code == 200
        reminders = response.json()

        # Should return 7 days (start_date + 6 days)
        assert len(reminders) == 3
        messages = [r['reminder_message'] for r in reminders]
        assert 'Day 1' in messages
        assert 'Day 3' in messages
        assert 'Day 7' in messages
        assert 'Outside range' not in messages

    def test_list_reminders_month_duration(self, client, test_db):
        """Test listing reminders for a month."""
        user_id = get_test_user_id(test_db)
        # Create test job
        test_db.execute(text("""
            INSERT INTO job (job_id, user_id, company, job_title, job_status, job_active, job_directory)
            VALUES (1, :user_id, 'Test Co', 'Engineer', 'applied', true, 'test_co_engineer')
        """), {"user_id": user_id})
        # Create reminders across a month+ period
        test_db.execute(text("""
            INSERT INTO reminder (reminder_id, user_id, reminder_date, reminder_time, reminder_message, reminder_dismissed, job_id)
            VALUES
                (1, :user_id, '2025-01-20', '10:00:00', 'Week 1', false, 1),
                (2, :user_id, '2025-02-01', '10:00:00', 'Week 2', false, 1),
                (3, :user_id, '2025-02-15', '10:00:00', 'Week 4', false, 1),
                (4, :user_id, '2025-02-20', '10:00:00', 'Outside range', false, 1)
        """), {"user_id": user_id})
        test_db.commit()

        list_data = {
            "duration": "month",
            "start_date": "2025-01-20"
        }

        response = client.post("/v1/reminder/list", json=list_data)

        assert response.status_code == 200
        reminders = response.json()

        # Should return 30 days (start_date + 29 days)
        assert len(reminders) == 3
        messages = [r['reminder_message'] for r in reminders]
        assert 'Week 1' in messages
        assert 'Week 2' in messages
        assert 'Week 4' in messages
        assert 'Outside range' not in messages

    def test_list_reminders_filtered_by_job(self, client, test_db):
        """Test listing reminders filtered by job_id."""
        user_id = get_test_user_id(test_db)
        # Create test jobs
        test_db.execute(text("""
            INSERT INTO job (job_id, user_id, company, job_title, job_status, job_active, job_directory)
            VALUES
                (1, :user_id, 'Company A', 'Engineer', 'applied', true, 'company_a_engineer'),
                (2, :user_id, 'Company B', 'Developer', 'interviewing', true, 'company_b_developer')
        """), {"user_id": user_id})
        # Create reminders for different jobs
        test_db.execute(text("""
            INSERT INTO reminder (reminder_id, user_id, reminder_date, reminder_time, reminder_message, reminder_dismissed, job_id)
            VALUES
                (1, :user_id, '2025-01-20', '10:00:00', 'Job 1 reminder', false, 1),
                (2, :user_id, '2025-01-21', '10:00:00', 'Job 2 reminder', false, 2),
                (3, :user_id, '2025-01-22', '10:00:00', 'Job 1 another', false, 1)
        """), {"user_id": user_id})
        test_db.commit()

        list_data = {
            "duration": "month",
            "start_date": "2025-01-20",
            "job_id": 1
        }

        response = client.post("/v1/reminder/list", json=list_data)

        assert response.status_code == 200
        reminders = response.json()

        assert len(reminders) == 2
        assert all(r['job_id'] == 1 for r in reminders)
        messages = [r['reminder_message'] for r in reminders]
        assert 'Job 1 reminder' in messages
        assert 'Job 1 another' in messages
        assert 'Job 2 reminder' not in messages

    def test_list_reminders_excludes_dismissed(self, client, test_db):
        """Test that dismissed reminders are excluded."""
        user_id = get_test_user_id(test_db)
        # Create test job
        test_db.execute(text("""
            INSERT INTO job (job_id, user_id, company, job_title, job_status, job_active, job_directory)
            VALUES (1, :user_id, 'Test Co', 'Engineer', 'applied', true, 'test_co_engineer')
        """), {"user_id": user_id})
        # Create reminders with different dismissed states
        test_db.execute(text("""
            INSERT INTO reminder (reminder_id, user_id, reminder_date, reminder_time, reminder_message, reminder_dismissed, job_id)
            VALUES
                (1, :user_id, '2025-01-20', '10:00:00', 'Active reminder', false, 1),
                (2, :user_id, '2025-01-21', '10:00:00', 'Dismissed reminder', true, 1),
                (3, :user_id, '2025-01-22', '10:00:00', 'Another active', NULL, 1)
        """), {"user_id": user_id})
        test_db.commit()

        list_data = {
            "duration": "month",
            "start_date": "2025-01-20"
        }

        response = client.post("/v1/reminder/list", json=list_data)

        assert response.status_code == 200
        reminders = response.json()

        assert len(reminders) == 2
        messages = [r['reminder_message'] for r in reminders]
        assert 'Active reminder' in messages
        assert 'Another active' in messages
        assert 'Dismissed reminder' not in messages

    def test_list_reminders_empty_result(self, client, test_db):
        """Test listing reminders when none exist."""
        list_data = {
            "duration": "month",
            "start_date": "2025-01-20"
        }

        response = client.post("/v1/reminder/list", json=list_data)

        assert response.status_code == 200
        assert response.json() == []

    def test_list_reminders_ordered_by_date_time_desc(self, client, test_db):
        """Test that reminders are ordered by date DESC, time DESC."""
        user_id = get_test_user_id(test_db)
        # Create test job
        test_db.execute(text("""
            INSERT INTO job (job_id, user_id, company, job_title, job_status, job_active, job_directory)
            VALUES (1, :user_id, 'Test Co', 'Engineer', 'applied', true, 'test_co_engineer')
        """), {"user_id": user_id})
        # Create reminders with different dates and times
        test_db.execute(text("""
            INSERT INTO reminder (reminder_id, user_id, reminder_date, reminder_time, reminder_message, reminder_dismissed, job_id)
            VALUES
                (1, :user_id, '2025-01-20', '10:00:00', 'Oldest', false, 1),
                (2, :user_id, '2025-01-25', '14:00:00', 'Newest', false, 1),
                (3, :user_id, '2025-01-25', '09:00:00', 'Same day earlier', false, 1),
                (4, :user_id, '2025-01-22', '15:00:00', 'Middle', false, 1)
        """), {"user_id": user_id})
        test_db.commit()

        list_data = {
            "duration": "month",
            "start_date": "2025-01-20"
        }

        response = client.post("/v1/reminder/list", json=list_data)

        assert response.status_code == 200
        reminders = response.json()

        assert len(reminders) == 4
        # Should be ordered by date DESC, time DESC
        assert reminders[0]['reminder_message'] == 'Newest'
        assert reminders[1]['reminder_message'] == 'Same day earlier'
        assert reminders[2]['reminder_message'] == 'Middle'
        assert reminders[3]['reminder_message'] == 'Oldest'

    def test_list_reminders_without_job_id(self, client, test_db):
        """Test listing reminders without job_id filter."""
        user_id = get_test_user_id(test_db)
        # Create test jobs
        test_db.execute(text("""
            INSERT INTO job (job_id, user_id, company, job_title, job_status, job_active, job_directory)
            VALUES
                (1, :user_id, 'Company A', 'Engineer', 'applied', true, 'company_a_engineer'),
                (2, :user_id, 'Company B', 'Developer', 'interviewing', true, 'company_b_developer')
        """), {"user_id": user_id})
        # Create reminders with different job links and no job
        test_db.execute(text("""
            INSERT INTO reminder (reminder_id, user_id, reminder_date, reminder_time, reminder_message, reminder_dismissed, job_id)
            VALUES
                (1, :user_id, '2025-01-20', '10:00:00', 'Job 1 reminder', false, 1),
                (2, :user_id, '2025-01-21', '10:00:00', 'Job 2 reminder', false, 2),
                (3, :user_id, '2025-01-22', '10:00:00', 'No job reminder', false, NULL)
        """), {"user_id": user_id})
        test_db.commit()

        list_data = {
            "duration": "month",
            "start_date": "2025-01-20"
        }

        response = client.post("/v1/reminder/list", json=list_data)

        assert response.status_code == 200
        reminders = response.json()

        # Should return all reminders
        assert len(reminders) == 3
        messages = [r['reminder_message'] for r in reminders]
        assert 'Job 1 reminder' in messages
        assert 'Job 2 reminder' in messages
        assert 'No job reminder' in messages
