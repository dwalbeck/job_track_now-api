import pytest
from unittest.mock import patch
from sqlalchemy import text
from datetime import date


# Helper to get test user ID
def get_test_user_id(test_db):
    result = test_db.execute(text("SELECT user_id FROM users WHERE login = 'testuser'")).first()
    return result.user_id if result else 1


class TestGetJobAppointments:
    """Test suite for GET /v1/calendar/appt endpoint."""

    def test_get_job_appointments_empty(self, client, test_db):
        """Test getting appointments when none exist."""
        user_id = get_test_user_id(test_db)
        # Create test job
        test_db.execute(text("""
            INSERT INTO job (job_id, user_id, company, job_title, job_status, job_active, job_directory)
            VALUES (1, :user_id, 'Test Co', 'Engineer', 'applied', true, 'test_co_engineer')
        """), {"user_id": user_id})
        test_db.commit()

        response = client.get("/v1/calendar/appt?job_id=1")

        assert response.status_code == 200
        assert response.json() == []

    def test_get_job_appointments_multiple(self, client, test_db):
        """Test getting multiple appointments for a job."""
        user_id = get_test_user_id(test_db)
        # Create test job
        test_db.execute(text("""
            INSERT INTO job (job_id, user_id, company, job_title, job_status, job_active, job_directory)
            VALUES (1, :user_id, 'Test Co', 'Engineer', 'applied', true, 'test_co_engineer')
        """), {"user_id": user_id})
        test_db.execute(text("""
            INSERT INTO calendar (calendar_id, user_id, job_id, calendar_type, start_date, start_time, end_date, end_time, participant, calendar_desc, outcome_score)
            VALUES
                (1, :user_id, 1, 'phone_call', '2025-01-15', '10:00:00', '2025-01-15', '10:30:00', ARRAY['John Doe'], 'Phone screening', 8),
                (2, :user_id, 1, 'interview', '2025-01-20', '14:00:00', '2025-01-20', '15:00:00', ARRAY['Jane Smith', 'Bob Jones'], 'Technical interview', 9)
        """), {"user_id": user_id})
        test_db.commit()

        response = client.get("/v1/calendar/appt?job_id=1")

        assert response.status_code == 200
        appts = response.json()

        assert len(appts) == 2
        # Should be ordered by start_date DESC, start_time DESC
        assert appts[0]['calendar_id'] == 2
        assert appts[0]['calendar_type'] == 'interview'
        assert appts[1]['calendar_id'] == 1


class TestGetMonthCalendar:
    """Test suite for GET /v1/calendar/month endpoint."""

    def test_get_month_calendar_success(self, client, test_db):
        """Test getting calendar for a specific month."""
        user_id = get_test_user_id(test_db)
        # Create test job and calendar entries
        test_db.execute(text("""
            INSERT INTO job (job_id, user_id, company, job_title, job_status, job_active, job_directory)
            VALUES (1, :user_id, 'Company A', 'Engineer', 'applied', true, 'company_a_engineer')
        """), {"user_id": user_id})
        test_db.execute(text("""
            INSERT INTO calendar (calendar_id, user_id, job_id, calendar_type, start_date, start_time)
            VALUES
                (1, :user_id, 1, 'phone_call', '2025-01-15', '10:00:00'),
                (2, :user_id, 1, 'interview', '2025-01-20', '14:00:00'),
                (3, :user_id, 1, 'interview', '2025-02-05', '11:00:00')
        """), {"user_id": user_id})
        test_db.commit()

        response = client.get("/v1/calendar/month?date=2025-01")

        assert response.status_code == 200
        events = response.json()

        # Should only return January events
        assert len(events) == 2
        assert events[0]['start_date'] == '2025-01-15'
        assert events[1]['start_date'] == '2025-01-20'

    def test_get_month_calendar_filtered_by_job(self, client, test_db):
        """Test getting month calendar filtered by job_id."""
        user_id = get_test_user_id(test_db)
        # Create test jobs and calendar entries
        test_db.execute(text("""
            INSERT INTO job (job_id, user_id, company, job_title, job_status, job_active, job_directory)
            VALUES
                (1, :user_id, 'Company A', 'Engineer', 'applied', true, 'company_a_engineer'),
                (2, :user_id, 'Company B', 'Developer', 'applied', true, 'company_b_developer')
        """), {"user_id": user_id})
        test_db.execute(text("""
            INSERT INTO calendar (calendar_id, user_id, job_id, calendar_type, start_date, start_time)
            VALUES
                (1, :user_id, 1, 'phone_call', '2025-01-15', '10:00:00'),
                (2, :user_id, 2, 'interview', '2025-01-20', '14:00:00')
        """), {"user_id": user_id})
        test_db.commit()

        response = client.get("/v1/calendar/month?date=2025-01&job_id=1")

        assert response.status_code == 200
        events = response.json()

        assert len(events) == 1
        assert events[0]['job_id'] == 1
        assert events[0]['company'] == 'Company A'

    def test_get_month_calendar_invalid_date(self, client, test_db):
        """Test invalid date format returns 400."""
        response = client.get("/v1/calendar/month?date=invalid")

        assert response.status_code == 400
        assert "Invalid date format" in response.json()['detail']


class TestGetWeekCalendar:
    """Test suite for GET /v1/calendar/week endpoint."""

    def test_get_week_calendar_success(self, client, test_db):
        """Test getting calendar for a specific week."""
        user_id = get_test_user_id(test_db)
        # Create test job and calendar entries (2025-01-13 is a Monday)
        test_db.execute(text("""
            INSERT INTO job (job_id, user_id, company, job_title, job_status, job_active, job_directory)
            VALUES (1, :user_id, 'Test Co', 'Engineer', 'applied', true, 'test_co_engineer')
        """), {"user_id": user_id})
        test_db.execute(text("""
            INSERT INTO calendar (calendar_id, user_id, job_id, calendar_type, start_date, start_time)
            VALUES
                (1, :user_id, 1, 'phone_call', '2025-01-13', '10:00:00'),
                (2, :user_id, 1, 'interview', '2025-01-15', '14:00:00'),
                (3, :user_id, 1, 'interview', '2025-01-20', '11:00:00')
        """), {"user_id": user_id})
        test_db.commit()

        response = client.get("/v1/calendar/week?date=2025-01-13")

        assert response.status_code == 200
        events = response.json()

        # Should return events from 2025-01-13 to 2025-01-19 (Monday to Sunday)
        assert len(events) == 2
        assert events[0]['start_date'] == '2025-01-13'
        assert events[1]['start_date'] == '2025-01-15'

    def test_get_week_calendar_not_monday(self, client, test_db):
        """Test that date must be a Monday."""
        # 2025-01-15 is a Wednesday
        response = client.get("/v1/calendar/week?date=2025-01-15")

        assert response.status_code == 400
        assert "must be a Monday" in response.json()['detail']


class TestGetDayCalendar:
    """Test suite for GET /v1/calendar/day endpoint."""

    def test_get_day_calendar_success(self, client, test_db):
        """Test getting calendar for a specific day."""
        user_id = get_test_user_id(test_db)
        # Create test job and calendar entries
        test_db.execute(text("""
            INSERT INTO job (job_id, user_id, company, job_title, job_status, job_active, job_directory)
            VALUES (1, :user_id, 'Test Co', 'Engineer', 'applied', true, 'test_co_engineer')
        """), {"user_id": user_id})
        test_db.execute(text("""
            INSERT INTO calendar (calendar_id, user_id, job_id, calendar_type, start_date, start_time)
            VALUES
                (1, :user_id, 1, 'phone_call', '2025-01-15', '10:00:00'),
                (2, :user_id, 1, 'interview', '2025-01-15', '14:00:00'),
                (3, :user_id, 1, 'interview', '2025-01-16', '11:00:00')
        """), {"user_id": user_id})
        test_db.commit()

        response = client.get("/v1/calendar/day?date=2025-01-15")

        assert response.status_code == 200
        events = response.json()

        assert len(events) == 2
        assert all(e['start_date'] == '2025-01-15' for e in events)

    def test_get_day_calendar_empty(self, client, test_db):
        """Test getting calendar for a day with no events."""
        user_id = get_test_user_id(test_db)
        test_db.execute(text("""
            INSERT INTO job (job_id, user_id, company, job_title, job_status, job_active, job_directory)
            VALUES (1, :user_id, 'Test Co', 'Engineer', 'applied', true, 'test_co_engineer')
        """), {"user_id": user_id})
        test_db.commit()

        response = client.get("/v1/calendar/day?date=2025-01-15")

        assert response.status_code == 200
        assert response.json() == []


class TestCreateOrUpdateCalendar:
    """Test suite for POST /v1/calendar endpoint."""

    @patch('app.api.calendar.update_job_activity')
    @patch('app.api.calendar.calc_avg_score')
    def test_create_calendar_event(self, mock_calc_avg, mock_update_activity, client, test_db):
        """Test creating a new calendar event."""
        user_id = get_test_user_id(test_db)
        # Create test job
        test_db.execute(text("""
            INSERT INTO job (job_id, user_id, company, job_title, job_status, job_active, job_directory)
            VALUES (1, :user_id, 'Test Co', 'Engineer', 'applied', true, 'test_co_engineer')
        """), {"user_id": user_id})
        test_db.commit()

        calendar_data = {
            "job_id": 1,
            "calendar_type": "phone_call",
            "start_date": "2025-01-15",
            "start_time": "10:00:00",
            "end_date": "2025-01-15",
            "end_time": "10:30:00",
            "participant": ["John Doe"],
            "calendar_desc": "Initial phone screening",
            "outcome_score": 8
        }

        response = client.post("/v1/calendar", json=calendar_data)

        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'success'
        assert 'calendar_id' in data

        # Verify event was created
        event = test_db.execute(text(f"SELECT * FROM calendar WHERE calendar_id = {data['calendar_id']}")).first()
        assert event.job_id == 1
        assert event.calendar_type == 'phone_call'
        assert str(event.start_date) == '2025-01-15'

        mock_update_activity.assert_called_once_with(test_db, 1)
        mock_calc_avg.assert_called_once_with(test_db, 1)

    @patch('app.api.calendar.update_job_activity')
    @patch('app.api.calendar.calc_avg_score')
    def test_update_calendar_event(self, mock_calc_avg, mock_update_activity, client, test_db):
        """Test updating an existing calendar event."""
        user_id = get_test_user_id(test_db)
        # Create test job and calendar event
        test_db.execute(text("""
            INSERT INTO job (job_id, user_id, company, job_title, job_status, job_active, job_directory)
            VALUES (1, :user_id, 'Test Co', 'Engineer', 'applied', true, 'test_co_engineer')
        """), {"user_id": user_id})
        test_db.execute(text("""
            INSERT INTO calendar (calendar_id, user_id, job_id, calendar_type, start_date, start_time, outcome_score)
            VALUES (1, :user_id, 1, 'phone_call', '2025-01-15', '10:00:00', 5)
        """), {"user_id": user_id})
        test_db.commit()

        update_data = {
            "calendar_id": 1,
            "job_id": 1,
            "calendar_type": "interview",
            "outcome_score": 9,
            "outcome_note": "Great interview!"
        }

        response = client.post("/v1/calendar", json=update_data)

        assert response.status_code == 200
        assert response.json()['status'] == 'success'

        # Verify event was updated
        event = test_db.execute(text("SELECT * FROM calendar WHERE calendar_id = 1")).first()
        assert event.calendar_type == 'interview'
        assert event.outcome_score == 9
        assert event.outcome_note == 'Great interview!'

    def test_create_calendar_job_not_found(self, client, test_db):
        """Test creating calendar event for non-existent job."""
        calendar_data = {
            "job_id": 999,
            "calendar_type": "phone_call",
            "start_date": "2025-01-15",
            "start_time": "10:00:00"
        }

        response = client.post("/v1/calendar", json=calendar_data)

        assert response.status_code == 404
        assert "Job not found" in response.json()['detail']

    def test_create_calendar_missing_job_id(self, client, test_db):
        """Test creating calendar event without job_id."""
        calendar_data = {
            "calendar_type": "phone_call",
            "start_date": "2025-01-15",
            "start_time": "10:00:00"
        }

        response = client.post("/v1/calendar", json=calendar_data)

        assert response.status_code == 400
        assert "job_id is required" in response.json()['detail']

    def test_update_calendar_event_not_found(self, client, test_db):
        """Test updating non-existent calendar event."""
        user_id = get_test_user_id(test_db)
        test_db.execute(text("""
            INSERT INTO job (job_id, user_id, company, job_title, job_status, job_active, job_directory)
            VALUES (1, :user_id, 'Test Co', 'Engineer', 'applied', true, 'test_co_engineer')
        """), {"user_id": user_id})
        test_db.commit()

        update_data = {
            "calendar_id": 999,
            "job_id": 1,
            "calendar_type": "interview"
        }

        response = client.post("/v1/calendar", json=update_data)

        assert response.status_code == 404
        assert "Calendar event not found" in response.json()['detail']


class TestGetCalendarEvent:
    """Test suite for GET /v1/calendar/{calendar_id} endpoint."""

    def test_get_calendar_event_success(self, client, test_db):
        """Test getting a calendar event by ID."""
        user_id = get_test_user_id(test_db)
        # Create test job and calendar event
        test_db.execute(text("""
            INSERT INTO job (job_id, user_id, company, job_title, job_status, job_active, job_directory)
            VALUES (1, :user_id, 'Tech Corp', 'Engineer', 'applied', true, 'tech_corp_engineer')
        """), {"user_id": user_id})
        test_db.execute(text("""
            INSERT INTO calendar (calendar_id, user_id, job_id, calendar_type, start_date, start_time, end_date, end_time, participant, calendar_desc, outcome_score)
            VALUES (1, :user_id, 1, 'interview', '2025-01-15', '10:00:00', '2025-01-15', '11:00:00', ARRAY['John Doe'], 'Technical interview', 9)
        """), {"user_id": user_id})
        test_db.commit()

        response = client.get("/v1/calendar/1")

        assert response.status_code == 200
        event = response.json()

        assert event['calendar_id'] == 1
        assert event['job_id'] == 1
        assert event['company'] == 'Tech Corp'
        assert event['calendar_type'] == 'interview'
        assert event['start_date'] == '2025-01-15'
        assert event['outcome_score'] == 9

    def test_get_calendar_event_not_found(self, client, test_db):
        """Test getting non-existent calendar event."""
        response = client.get("/v1/calendar/999")

        assert response.status_code == 404
        assert "Calendar event not found" in response.json()['detail']


class TestDeleteCalendarAppointment:
    """Test suite for DELETE /v1/calendar/appt endpoint."""

    @patch('app.api.calendar.calc_avg_score')
    def test_delete_calendar_appointment_success(self, mock_calc_avg, client, test_db):
        """Test successfully deleting a calendar appointment."""
        user_id = get_test_user_id(test_db)
        # Create test job and calendar event
        test_db.execute(text("""
            INSERT INTO job (job_id, user_id, company, job_title, job_status, job_active, job_directory)
            VALUES (1, :user_id, 'Test Co', 'Engineer', 'applied', true, 'test_co_engineer')
        """), {"user_id": user_id})
        test_db.execute(text("""
            INSERT INTO calendar (calendar_id, user_id, job_id, calendar_type, start_date, start_time)
            VALUES (1, :user_id, 1, 'phone_call', '2025-01-15', '10:00:00')
        """), {"user_id": user_id})
        test_db.commit()

        response = client.delete("/v1/calendar/appt?appointment_id=1")

        assert response.status_code == 200
        assert "deleted successfully" in response.json()['message']

        # Verify appointment was deleted
        result = test_db.execute(text("SELECT * FROM calendar WHERE calendar_id = 1")).first()
        assert result is None

        mock_calc_avg.assert_called_once_with(test_db, 1)

    def test_delete_calendar_appointment_not_found(self, client, test_db):
        """Test deleting non-existent appointment."""
        response = client.delete("/v1/calendar/appt?appointment_id=999")

        assert response.status_code == 404
        assert "Appointment not found" in response.json()['detail']
