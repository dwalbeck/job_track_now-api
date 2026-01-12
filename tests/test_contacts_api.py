import pytest
from unittest.mock import patch
from sqlalchemy import text


class TestCreateOrUpdateContact:
    """Test suite for POST /v1/contact endpoint."""

    @patch('app.api.contacts.update_job_activity')
    def test_create_contact_without_job(self, mock_update_activity, client, test_db):
        """Test creating a contact without linking to a job."""
        contact_data = {
            "first_name": "John",
            "last_name": "Doe",
            "job_title": "Recruiter",
            "email": "john.doe@example.com",
            "phone": "555-1234",
            "company": "Tech Corp",
            "linkedin": "https://linkedin.com/in/johndoe",
            "contact_note": "Met at career fair"
        }

        response = client.post("/v1/contact", json=contact_data)

        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'success'
        assert 'contact_id' in data

        # Verify contact was created
        contact = test_db.execute(text(f"SELECT * FROM contact WHERE contact_id = {data['contact_id']}")).first()
        assert contact.first_name == "John"
        assert contact.last_name == "Doe"
        assert contact.email == "john.doe@example.com"
        assert contact.contact_active == True

    @patch('app.api.contacts.update_job_activity')
    def test_create_contact_with_job_link(self, mock_update_activity, client, test_db):
        """Test creating a contact and linking to a job."""
        # Create test job
        test_db.execute(text("""
            INSERT INTO job (job_id, company, job_title, job_status, job_active, job_directory)
            VALUES (1, 'Test Co', 'Engineer', 'applied', true, 'test_co_engineer')
        """))
        test_db.commit()

        contact_data = {
            "first_name": "Jane",
            "last_name": "Smith",
            "job_title": "Hiring Manager",
            "email": "jane.smith@example.com",
            "phone": "555-5678",
            "company": "Test Co",
            "job_id": 1
        }

        response = client.post("/v1/contact", json=contact_data)

        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'success'

        # Verify job_contact link was created
        link = test_db.execute(text(f"""
            SELECT * FROM job_contact
            WHERE job_id = 1 AND contact_id = {data['contact_id']}
        """)).first()
        assert link is not None
        mock_update_activity.assert_called_once_with(test_db, 1)

    @patch('app.api.contacts.update_job_activity')
    def test_update_contact(self, mock_update_activity, client, test_db):
        """Test updating an existing contact."""
        # Create initial contact
        test_db.execute(text("""
            INSERT INTO contact (contact_id, first_name, last_name, email, phone, contact_active)
            VALUES (1, 'Old', 'Name', 'old@example.com', '555-0000', true)
        """))
        test_db.commit()

        update_data = {
            "contact_id": 1,
            "first_name": "New",
            "last_name": "Name",
            "email": "new@example.com",
            "phone": "555-9999"
        }

        response = client.post("/v1/contact", json=update_data)

        assert response.status_code == 200
        assert response.json()['status'] == 'success'

        # Verify contact was updated
        contact = test_db.execute(text("SELECT * FROM contact WHERE contact_id = 1")).first()
        assert contact.first_name == "New"
        assert contact.email == "new@example.com"

    def test_update_contact_not_found(self, client, test_db):
        """Test updating non-existent contact."""
        update_data = {
            "contact_id": 999,
            "first_name": "Does Not",
            "last_name": "Exist"
        }

        response = client.post("/v1/contact", json=update_data)

        assert response.status_code == 404
        assert "Contact not found" in response.json()['detail']

    @patch('app.api.contacts.update_job_activity')
    def test_create_contact_duplicate_job_link(self, mock_update_activity, client, test_db):
        """Test creating duplicate job_contact link doesn't cause error."""
        # Create test job and contact
        test_db.execute(text("""
            INSERT INTO job (job_id, company, job_title, job_status, job_active, job_directory)
            VALUES (1, 'Test Co', 'Engineer', 'applied', true, 'test_co_engineer')
        """))
        test_db.execute(text("""
            INSERT INTO contact (contact_id, first_name, last_name, contact_active)
            VALUES (1, 'Test', 'Contact', true)
        """))
        test_db.execute(text("""
            INSERT INTO job_contact (job_id, contact_id)
            VALUES (1, 1)
        """))
        test_db.commit()

        # Try to create the same link again
        contact_data = {
            "contact_id": 1,
            "first_name": "Test",
            "last_name": "Contact",
            "job_id": 1
        }

        response = client.post("/v1/contact", json=contact_data)

        assert response.status_code == 200
        assert response.json()['status'] == 'success'


class TestDeleteContact:
    """Test suite for DELETE /v1/contact/{contact_id} endpoint."""

    def test_delete_contact_success(self, client, test_db):
        """Test successfully deleting a contact."""
        # Create test contact
        test_db.execute(text("""
            INSERT INTO contact (contact_id, first_name, last_name, contact_active)
            VALUES (1, 'Delete', 'Me', true)
        """))
        test_db.commit()

        response = client.delete("/v1/contact/1")

        assert response.status_code == 200
        assert response.json()['status'] == 'success'

        # Verify soft delete
        contact = test_db.execute(text("SELECT contact_active FROM contact WHERE contact_id = 1")).first()
        assert contact.contact_active == False

    def test_delete_contact_not_found(self, client, test_db):
        """Test deleting non-existent contact."""
        response = client.delete("/v1/contact/999")

        assert response.status_code == 404
        assert "Contact not found" in response.json()['detail']


class TestGetContact:
    """Test suite for GET /v1/contact/{contact_id} endpoint."""

    def test_get_contact_success(self, client, test_db):
        """Test getting a contact by ID."""
        # Create test contact
        test_db.execute(text("""
            INSERT INTO contact (contact_id, first_name, last_name, job_title, email, phone, company, linkedin, contact_note, contact_active)
            VALUES (1, 'John', 'Doe', 'Recruiter', 'john@example.com', '555-1234', 'Tech Corp', 'linkedin.com/in/john', 'Great contact', true)
        """))
        test_db.commit()

        response = client.get("/v1/contact/1")

        assert response.status_code == 200
        contact = response.json()

        assert contact['contact_id'] == 1
        assert contact['first_name'] == 'John'
        assert contact['last_name'] == 'Doe'
        assert contact['email'] == 'john@example.com'
        assert contact['linked_to'] == []

    def test_get_contact_with_job_links(self, client, test_db):
        """Test getting a contact with linked jobs."""
        # Create test data
        test_db.execute(text("""
            INSERT INTO job (job_id, company, job_title, job_status, job_active, job_directory)
            VALUES
                (1, 'Company A', 'Engineer', 'applied', true, 'company_a_engineer'),
                (2, 'Company B', 'Developer', 'interviewing', true, 'company_b_developer')
        """))
        test_db.execute(text("""
            INSERT INTO contact (contact_id, first_name, last_name, contact_active)
            VALUES (1, 'Jane', 'Smith', true)
        """))
        test_db.execute(text("""
            INSERT INTO job_contact (job_id, contact_id)
            VALUES (1, 1), (2, 1)
        """))
        test_db.commit()

        response = client.get("/v1/contact/1")

        assert response.status_code == 200
        contact = response.json()

        assert contact['contact_id'] == 1
        assert len(contact['linked_to']) == 2
        assert any(job['company'] == 'Company A' for job in contact['linked_to'])
        assert any(job['company'] == 'Company B' for job in contact['linked_to'])

    def test_get_contact_filtered_by_job(self, client, test_db):
        """Test getting a contact filtered by specific job."""
        # Create test data
        test_db.execute(text("""
            INSERT INTO job (job_id, company, job_title, job_status, job_active, job_directory)
            VALUES
                (1, 'Company A', 'Engineer', 'applied', true, 'company_a_engineer'),
                (2, 'Company B', 'Developer', 'interviewing', true, 'company_b_developer')
        """))
        test_db.execute(text("""
            INSERT INTO contact (contact_id, first_name, last_name, contact_active)
            VALUES (1, 'Test', 'Contact', true)
        """))
        test_db.execute(text("""
            INSERT INTO job_contact (job_id, contact_id)
            VALUES (1, 1), (2, 1)
        """))
        test_db.commit()

        response = client.get("/v1/contact/1?job_id=1")

        assert response.status_code == 200
        contact = response.json()

        assert len(contact['linked_to']) == 1
        assert contact['linked_to'][0]['job_id'] == 1
        assert contact['linked_to'][0]['company'] == 'Company A'

    def test_get_contact_not_found(self, client, test_db):
        """Test getting non-existent contact."""
        response = client.get("/v1/contact/999")

        assert response.status_code == 404
        assert "Contact not found" in response.json()['detail']

    def test_get_contact_inactive(self, client, test_db):
        """Test that inactive contacts return 404."""
        test_db.execute(text("""
            INSERT INTO contact (contact_id, first_name, last_name, contact_active)
            VALUES (1, 'Inactive', 'Contact', false)
        """))
        test_db.commit()

        response = client.get("/v1/contact/1")

        assert response.status_code == 404


class TestGetContacts:
    """Test suite for GET /v1/contacts endpoint."""

    def test_get_all_contacts_empty(self, client, test_db):
        """Test getting contacts when none exist."""
        response = client.get("/v1/contacts")

        assert response.status_code == 200
        assert response.json() == []

    def test_get_all_contacts(self, client, test_db):
        """Test getting all active contacts."""
        # Create test contacts
        test_db.execute(text("""
            INSERT INTO contact (contact_id, first_name, last_name, email, contact_active)
            VALUES
                (1, 'Alice', 'Anderson', 'alice@example.com', true),
                (2, 'Bob', 'Brown', 'bob@example.com', true),
                (3, 'Charlie', 'Chen', 'charlie@example.com', false)
        """))
        test_db.commit()

        response = client.get("/v1/contacts")

        assert response.status_code == 200
        contacts = response.json()

        assert len(contacts) == 2
        # Should be sorted by first_name, last_name
        assert contacts[0]['first_name'] == 'Alice'
        assert contacts[1]['first_name'] == 'Bob'

    def test_get_contacts_filtered_by_job(self, client, test_db):
        """Test getting contacts filtered by job_id."""
        # Create test data
        test_db.execute(text("""
            INSERT INTO job (job_id, company, job_title, job_status, job_active, job_directory)
            VALUES (1, 'Test Co', 'Engineer', 'applied', true, 'test_co_engineer')
        """))
        test_db.execute(text("""
            INSERT INTO contact (contact_id, first_name, last_name, contact_active)
            VALUES
                (1, 'Linked', 'Contact', true),
                (2, 'Unlinked', 'Contact', true)
        """))
        test_db.execute(text("""
            INSERT INTO job_contact (job_id, contact_id)
            VALUES (1, 1)
        """))
        test_db.commit()

        response = client.get("/v1/contacts?job_id=1")

        assert response.status_code == 200
        contacts = response.json()

        assert len(contacts) == 1
        assert contacts[0]['first_name'] == 'Linked'

    def test_get_contacts_excludes_inactive(self, client, test_db):
        """Test that inactive contacts are excluded."""
        test_db.execute(text("""
            INSERT INTO contact (contact_id, first_name, last_name, contact_active)
            VALUES
                (1, 'Active', 'Contact', true),
                (2, 'Inactive', 'Contact', false)
        """))
        test_db.commit()

        response = client.get("/v1/contacts")

        assert response.status_code == 200
        contacts = response.json()

        assert len(contacts) == 1
        assert contacts[0]['first_name'] == 'Active'

    def test_get_contacts_sorted_by_name(self, client, test_db):
        """Test that contacts are sorted alphabetically."""
        test_db.execute(text("""
            INSERT INTO contact (contact_id, first_name, last_name, contact_active)
            VALUES
                (1, 'Zoe', 'Zulu', true),
                (2, 'Alice', 'Adams', true),
                (3, 'Alice', 'Zeta', true),
                (4, 'Bob', 'Baker', true)
        """))
        test_db.commit()

        response = client.get("/v1/contacts")

        assert response.status_code == 200
        contacts = response.json()

        assert len(contacts) == 4
        # Should be sorted by first_name ASC, then last_name ASC
        assert contacts[0]['first_name'] == 'Alice'
        assert contacts[0]['last_name'] == 'Adams'
        assert contacts[1]['first_name'] == 'Alice'
        assert contacts[1]['last_name'] == 'Zeta'
        assert contacts[2]['first_name'] == 'Bob'
        assert contacts[3]['first_name'] == 'Zoe'
