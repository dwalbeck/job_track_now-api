import pytest
from unittest.mock import patch
from sqlalchemy import text


class TestGetNotes:
    """Test suite for GET /v1/notes endpoint."""

    def test_get_notes_empty(self, client, test_db):
        """Test getting notes when none exist."""
        # Create test job
        test_db.execute(text("""
            INSERT INTO job (job_id, company, job_title, job_status, job_active, job_directory)
            VALUES (1, 'Test Co', 'Engineer', 'applied', true, 'test_co_engineer')
        """))
        test_db.commit()

        response = client.get("/v1/notes")

        assert response.status_code == 200
        assert response.json() == []

    def test_get_all_notes(self, client, test_db):
        """Test getting all active notes."""
        # Create test job and notes
        test_db.execute(text("""
            INSERT INTO job (job_id, company, job_title, job_status, job_active, job_directory)
            VALUES (1, 'Tech Corp', 'Engineer', 'applied', true, 'tech_corp_engineer')
        """))
        test_db.execute(text("""
            INSERT INTO note (note_id, job_id, note_title, note_content, note_active, note_created)
            VALUES
                (1, 1, 'First Note', 'This is the first note', true, '2025-01-15 10:00:00'),
                (2, 1, 'Second Note', 'This is the second note', true, '2025-01-16 11:00:00'),
                (3, 1, 'Inactive Note', 'This note is inactive', false, '2025-01-14 09:00:00')
        """))
        test_db.commit()

        response = client.get("/v1/notes")

        assert response.status_code == 200
        notes = response.json()

        # Should only return active notes, ordered by note_created DESC
        assert len(notes) == 2
        assert notes[0]['note_title'] == 'Second Note'
        assert notes[1]['note_title'] == 'First Note'
        assert notes[0]['company'] == 'Tech Corp'
        assert notes[0]['job_title'] == 'Engineer'

    def test_get_notes_filtered_by_job(self, client, test_db):
        """Test getting notes filtered by job_id."""
        # Create test jobs and notes
        test_db.execute(text("""
            INSERT INTO job (job_id, company, job_title, job_status, job_active, job_directory)
            VALUES
                (1, 'Company A', 'Engineer', 'applied', true, 'company_a_engineer'),
                (2, 'Company B', 'Developer', 'interviewing', true, 'company_b_developer')
        """))
        test_db.execute(text("""
            INSERT INTO note (note_id, job_id, note_title, note_content, note_active)
            VALUES
                (1, 1, 'Job 1 Note', 'Note for job 1', true),
                (2, 2, 'Job 2 Note', 'Note for job 2', true),
                (3, 1, 'Another Job 1 Note', 'Another note for job 1', true)
        """))
        test_db.commit()

        response = client.get("/v1/notes?job_id=1")

        assert response.status_code == 200
        notes = response.json()

        assert len(notes) == 2
        assert all(note['job_id'] == 1 for note in notes)
        assert any(note['note_title'] == 'Job 1 Note' for note in notes)
        assert any(note['note_title'] == 'Another Job 1 Note' for note in notes)

    def test_get_notes_excludes_inactive(self, client, test_db):
        """Test that inactive notes are excluded."""
        test_db.execute(text("""
            INSERT INTO job (job_id, company, job_title, job_status, job_active, job_directory)
            VALUES (1, 'Test Co', 'Engineer', 'applied', true, 'test_co_engineer')
        """))
        test_db.execute(text("""
            INSERT INTO note (note_id, job_id, note_title, note_content, note_active)
            VALUES
                (1, 1, 'Active Note', 'This is active', true),
                (2, 1, 'Inactive Note', 'This is inactive', false)
        """))
        test_db.commit()

        response = client.get("/v1/notes")

        assert response.status_code == 200
        notes = response.json()

        assert len(notes) == 1
        assert notes[0]['note_title'] == 'Active Note'

    def test_get_notes_ordered_by_created_desc(self, client, test_db):
        """Test that notes are ordered by note_created DESC."""
        test_db.execute(text("""
            INSERT INTO job (job_id, company, job_title, job_status, job_active, job_directory)
            VALUES (1, 'Test Co', 'Engineer', 'applied', true, 'test_co_engineer')
        """))
        test_db.execute(text("""
            INSERT INTO note (note_id, job_id, note_title, note_active, note_created)
            VALUES
                (1, 1, 'Oldest', true, '2025-01-10 10:00:00'),
                (2, 1, 'Middle', true, '2025-01-15 10:00:00'),
                (3, 1, 'Newest', true, '2025-01-20 10:00:00')
        """))
        test_db.commit()

        response = client.get("/v1/notes")

        assert response.status_code == 200
        notes = response.json()

        assert len(notes) == 3
        assert notes[0]['note_title'] == 'Newest'
        assert notes[1]['note_title'] == 'Middle'
        assert notes[2]['note_title'] == 'Oldest'


class TestCreateOrUpdateNote:
    """Test suite for POST /v1/note and POST /v1/notes endpoints."""

    @patch('app.api.notes.update_job_activity')
    def test_create_note_success(self, mock_update_activity, client, test_db):
        """Test creating a new note."""
        # Create test job
        test_db.execute(text("""
            INSERT INTO job (job_id, company, job_title, job_status, job_active, job_directory)
            VALUES (1, 'Test Co', 'Engineer', 'applied', true, 'test_co_engineer')
        """))
        test_db.commit()

        note_data = {
            "job_id": 1,
            "note_title": "Interview Notes",
            "note_content": "They asked about Python experience"
        }

        response = client.post("/v1/note", json=note_data)

        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'success'
        assert 'note_id' in data

        # Verify note was created
        note = test_db.execute(text(f"SELECT * FROM note WHERE note_id = {data['note_id']}")).first()
        assert note.job_id == 1
        assert note.note_title == "Interview Notes"
        assert note.note_content == "They asked about Python experience"
        assert note.note_active == True

        mock_update_activity.assert_called_once_with(test_db, 1)

    @patch('app.api.notes.update_job_activity')
    def test_create_note_plural_route(self, mock_update_activity, client, test_db):
        """Test creating a note using plural route /v1/notes."""
        # Create test job
        test_db.execute(text("""
            INSERT INTO job (job_id, company, job_title, job_status, job_active, job_directory)
            VALUES (1, 'Test Co', 'Engineer', 'applied', true, 'test_co_engineer')
        """))
        test_db.commit()

        note_data = {
            "job_id": 1,
            "note_title": "Test Note",
            "note_content": "Test content"
        }

        response = client.post("/v1/notes", json=note_data)

        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'success'
        assert 'note_id' in data

    def test_create_note_missing_job_id(self, client, test_db):
        """Test creating a note without job_id."""
        note_data = {
            "note_title": "Test Note",
            "note_content": "Test content"
        }

        response = client.post("/v1/note", json=note_data)

        assert response.status_code == 400
        assert "job_id and note_title are required" in response.json()['detail']

    def test_create_note_missing_title(self, client, test_db):
        """Test creating a note without note_title."""
        test_db.execute(text("""
            INSERT INTO job (job_id, company, job_title, job_status, job_active, job_directory)
            VALUES (1, 'Test Co', 'Engineer', 'applied', true, 'test_co_engineer')
        """))
        test_db.commit()

        note_data = {
            "job_id": 1,
            "note_content": "Test content"
        }

        response = client.post("/v1/note", json=note_data)

        assert response.status_code == 400
        assert "job_id and note_title are required" in response.json()['detail']

    def test_create_note_job_not_found(self, client, test_db):
        """Test creating a note for non-existent job."""
        note_data = {
            "job_id": 999,
            "note_title": "Test Note",
            "note_content": "Test content"
        }

        response = client.post("/v1/note", json=note_data)

        assert response.status_code == 404
        assert "Job not found" in response.json()['detail']

    @patch('app.api.notes.update_job_activity')
    def test_update_note_success(self, mock_update_activity, client, test_db):
        """Test updating an existing note."""
        # Create test job and note
        test_db.execute(text("""
            INSERT INTO job (job_id, company, job_title, job_status, job_active, job_directory)
            VALUES (1, 'Test Co', 'Engineer', 'applied', true, 'test_co_engineer')
        """))
        test_db.execute(text("""
            INSERT INTO note (note_id, job_id, note_title, note_content, note_active)
            VALUES (1, 1, 'Old Title', 'Old content', true)
        """))
        test_db.commit()

        update_data = {
            "note_id": 1,
            "note_title": "Updated Title",
            "note_content": "Updated content"
        }

        response = client.post("/v1/note", json=update_data)

        assert response.status_code == 200
        assert response.json()['status'] == 'success'

        # Verify note was updated
        note = test_db.execute(text("SELECT * FROM note WHERE note_id = 1")).first()
        assert note.note_title == "Updated Title"
        assert note.note_content == "Updated content"

        mock_update_activity.assert_called_once_with(test_db, 1)

    @patch('app.api.notes.update_job_activity')
    def test_update_note_partial_fields(self, mock_update_activity, client, test_db):
        """Test updating only some fields of a note."""
        # Create test job and note
        test_db.execute(text("""
            INSERT INTO job (job_id, company, job_title, job_status, job_active, job_directory)
            VALUES (1, 'Test Co', 'Engineer', 'applied', true, 'test_co_engineer')
        """))
        test_db.execute(text("""
            INSERT INTO note (note_id, job_id, note_title, note_content, note_active)
            VALUES (1, 1, 'Original Title', 'Original content', true)
        """))
        test_db.commit()

        # Update only the content
        update_data = {
            "note_id": 1,
            "note_content": "New content only"
        }

        response = client.post("/v1/note", json=update_data)

        assert response.status_code == 200

        # Verify only content changed
        note = test_db.execute(text("SELECT * FROM note WHERE note_id = 1")).first()
        assert note.note_title == "Original Title"
        assert note.note_content == "New content only"

    def test_update_note_not_found(self, client, test_db):
        """Test updating non-existent note."""
        update_data = {
            "note_id": 999,
            "note_title": "Does Not Exist"
        }

        response = client.post("/v1/note", json=update_data)

        assert response.status_code == 404
        assert "Note not found" in response.json()['detail']

    @patch('app.api.notes.update_job_activity')
    def test_create_note_minimal_data(self, mock_update_activity, client, test_db):
        """Test creating a note with only required fields."""
        test_db.execute(text("""
            INSERT INTO job (job_id, company, job_title, job_status, job_active, job_directory)
            VALUES (1, 'Test Co', 'Engineer', 'applied', true, 'test_co_engineer')
        """))
        test_db.commit()

        note_data = {
            "job_id": 1,
            "note_title": "Minimal Note"
        }

        response = client.post("/v1/note", json=note_data)

        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'success'

        # Verify note was created with null content
        note = test_db.execute(text(f"SELECT * FROM note WHERE note_id = {data['note_id']}")).first()
        assert note.note_title == "Minimal Note"
        assert note.note_content is None

    @patch('app.api.notes.update_job_activity')
    def test_update_job_activity_failure_doesnt_break_note_creation(self, mock_update_activity, client, test_db):
        """Test that note creation succeeds even if update_job_activity fails."""
        # Create test job
        test_db.execute(text("""
            INSERT INTO job (job_id, company, job_title, job_status, job_active, job_directory)
            VALUES (1, 'Test Co', 'Engineer', 'applied', true, 'test_co_engineer')
        """))
        test_db.commit()

        # Make update_job_activity raise an exception
        mock_update_activity.side_effect = Exception("Activity update failed")

        note_data = {
            "job_id": 1,
            "note_title": "Test Note",
            "note_content": "Test content"
        }

        response = client.post("/v1/note", json=note_data)

        # Note should still be created successfully
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'success'
        assert 'note_id' in data


class TestDeleteNote:
    """Test suite for DELETE /v1/note/{note_id} endpoint."""

    def test_delete_note_success(self, client, test_db):
        """Test successfully deleting a note."""
        # Create test job and note
        test_db.execute(text("""
            INSERT INTO job (job_id, company, job_title, job_status, job_active, job_directory)
            VALUES (1, 'Test Co', 'Engineer', 'applied', true, 'test_co_engineer')
        """))
        test_db.execute(text("""
            INSERT INTO note (note_id, job_id, note_title, note_content, note_active)
            VALUES (1, 1, 'Delete Me', 'This will be deleted', true)
        """))
        test_db.commit()

        response = client.delete("/v1/note/1")

        assert response.status_code == 200
        assert response.json()['status'] == 'success'

        # Verify soft delete (note_active set to false)
        note = test_db.execute(text("SELECT note_active FROM note WHERE note_id = 1")).first()
        assert note.note_active == False

    def test_delete_note_not_found(self, client, test_db):
        """Test deleting non-existent note."""
        response = client.delete("/v1/note/999")

        assert response.status_code == 404
        assert "Note not found" in response.json()['detail']

    def test_delete_note_already_inactive(self, client, test_db):
        """Test deleting an already inactive note."""
        # Create test job and inactive note
        test_db.execute(text("""
            INSERT INTO job (job_id, company, job_title, job_status, job_active, job_directory)
            VALUES (1, 'Test Co', 'Engineer', 'applied', true, 'test_co_engineer')
        """))
        test_db.execute(text("""
            INSERT INTO note (note_id, job_id, note_title, note_active)
            VALUES (1, 1, 'Already Inactive', false)
        """))
        test_db.commit()

        response = client.delete("/v1/note/1")

        assert response.status_code == 200
        assert response.json()['status'] == 'success'

        # Note should still be inactive
        note = test_db.execute(text("SELECT note_active FROM note WHERE note_id = 1")).first()
        assert note.note_active == False
