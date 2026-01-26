import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
import hashlib
import base64
import secrets
from urllib.parse import urlparse, parse_qs

from app.utils.oauth_utils import (
    generate_authorization_code,
    store_authorization_code,
    retrieve_authorization_code,
    mark_authorization_code_used,
    verify_pkce_challenge,
    create_access_token,
    verify_access_token
)


# Helper functions for PKCE
def generate_code_verifier():
    """Generate PKCE code verifier"""
    return secrets.token_urlsafe(32)


def generate_code_challenge(verifier):
    """Generate PKCE code challenge from verifier"""
    hash_digest = hashlib.sha256(verifier.encode('ascii')).digest()
    return base64.urlsafe_b64encode(hash_digest).decode('ascii').rstrip('=')


@pytest.fixture(autouse=True)
def setup_test_user(test_db):
    """Setup test user with credentials in users table"""
    from app.utils.password import hash_password

    # Hash the test password
    hashed_password = hash_password("testpass123")

    test_db.execute(text("""
        INSERT INTO users (first_name, last_name, login, passwd, email, is_admin)
        VALUES ('John', 'Doe', 'oauthoauthtestuser', :passwd, 'john@example.com', false)
        ON CONFLICT DO NOTHING
    """), {"passwd": hashed_password})

    # Get the user_id
    result = test_db.execute(text("SELECT user_id FROM users WHERE login = 'oauthoauthtestuser'")).first()
    if result:
        user_id = result.user_id
        # Create user settings
        test_db.execute(text("""
            INSERT INTO user_setting (
                user_id,
                default_llm, resume_extract_llm, job_extract_llm, rewrite_llm, cover_llm, company_llm, tools_llm,
                docx2html, odt2html, pdf2html, html2docx, html2odt, html2pdf
            )
            VALUES (
                :user_id,
                'gpt-4.1-mini', 'gpt-4.1-mini', 'gpt-4.1-mini', 'gpt-4.1-mini', 'gpt-4.1-mini', 'gpt-4.1-mini', 'gpt-4.1-mini',
                'docx-parser-converter', 'pandoc', 'markitdown',
                'html4docx', 'pandoc', 'weasyprint'
            )
            ON CONFLICT (user_id) DO NOTHING
        """), {"user_id": user_id})
    test_db.commit()
    yield
    # Cleanup auth codes from database after each test
    test_db.execute(text("DELETE FROM oauth_codes"))
    test_db.commit()


class TestOAuthUtils:
    """Test OAuth utility functions"""

    def test_generate_authorization_code(self):
        """Test authorization code generation"""
        code = generate_authorization_code()
        assert isinstance(code, str)
        assert len(code) > 20

        # Test uniqueness
        code2 = generate_authorization_code()
        assert code != code2

    def test_store_and_retrieve_authorization_code(self):
        """Test storing and retrieving authorization code"""
        code = "test_auth_code_123"
        username = "oauthtestuser"
        redirect_uri = "http://localhost:3000/callback"
        code_challenge = "test_challenge"
        code_challenge_method = "S256"
        state = "test_state"
        scope = "all"

        # Store code
        store_authorization_code(
            code=code,
            username=username,
            redirect_uri=redirect_uri,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
            state=state,
            scope=scope,
            user_id=1,
            is_admin=False
        )

        # Retrieve code
        data = retrieve_authorization_code(code)
        assert data is not None
        assert data["username"] == username
        assert data["redirect_uri"] == redirect_uri
        assert data["code_challenge"] == code_challenge
        assert data["state"] == state
        assert data["used"] is False

    def test_retrieve_nonexistent_code(self):
        """Test retrieving non-existent authorization code"""
        data = retrieve_authorization_code("nonexistent_code")
        assert data is None

    def test_mark_code_as_used(self):
        """Test marking authorization code as used"""
        code = "test_auth_code_456"
        store_authorization_code(
            code=code,
            username="oauthtestuser",
            redirect_uri="http://localhost:3000/callback",
            code_challenge="challenge",
            code_challenge_method="S256",
            state="state",
            scope="all",
            user_id=1,
            is_admin=False
        )

        # Mark as used
        mark_authorization_code_used(code)

        # Should not be retrievable after marking as used
        data = retrieve_authorization_code(code)
        assert data is None

    def test_verify_pkce_challenge_s256(self):
        """Test PKCE challenge verification with S256 method"""
        verifier = generate_code_verifier()
        challenge = generate_code_challenge(verifier)

        # Should verify successfully
        assert verify_pkce_challenge(verifier, challenge, "S256") is True

        # Should fail with wrong verifier
        wrong_verifier = generate_code_verifier()
        assert verify_pkce_challenge(wrong_verifier, challenge, "S256") is False

    def test_verify_pkce_challenge_plain(self):
        """Test PKCE challenge verification with plain method"""
        verifier = "plain_text_verifier"
        challenge = "plain_text_verifier"

        # Should verify successfully
        assert verify_pkce_challenge(verifier, challenge, "plain") is True

        # Should fail with wrong verifier
        assert verify_pkce_challenge("wrong", challenge, "plain") is False

    def test_create_and_verify_access_token(self):
        """Test JWT access token creation and verification"""
        username = "oauthtestuser"
        scope = "all"

        # Create token
        token = create_access_token(username=username, scope=scope)
        assert isinstance(token, str)
        assert len(token) > 50

        # Verify token
        payload = verify_access_token(token)
        assert payload is not None
        assert payload["sub"] == username
        assert payload["preferred_username"] == username
        assert payload["scope"] == scope
        assert payload["typ"] == "Bearer"
        assert payload["iss"] == "job-track-now-api"
        assert "exp" in payload
        assert "iat" in payload

    def test_verify_invalid_token(self):
        """Test verification of invalid token"""
        invalid_token = "invalid.jwt.token"
        payload = verify_access_token(invalid_token)
        assert payload is None


class TestAuthorizeEndpoint:
    """Test /authorize endpoint"""

    def test_authorize_success(self, client):
        """Test successful authorization request"""
        verifier = generate_code_verifier()
        challenge = generate_code_challenge(verifier)

        response = client.get("/v1/authorize", params={
            "response_type": "code",
            "redirect_uri": "http://localhost:3000/callback",
            "state": "test_state_123",
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "scope": "all"
        })

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

        # Check HTML contains form elements
        html_content = response.text
        assert "Username" in html_content
        assert "Password" in html_content
        assert 'action="/v1/login"' in html_content
        assert f'value="{challenge}"' in html_content

    def test_authorize_invalid_response_type(self, client):
        """Test authorization with invalid response_type"""
        response = client.get("/v1/authorize", params={
            "response_type": "invalid",
            "redirect_uri": "http://localhost:3000/callback",
            "state": "test_state",
            "code_challenge": "challenge",
            "code_challenge_method": "S256"
        })

        assert response.status_code == 400
        assert "Invalid response_type" in response.json()["detail"]

    def test_authorize_invalid_challenge_method(self, client):
        """Test authorization with invalid challenge method"""
        response = client.get("/v1/authorize", params={
            "response_type": "code",
            "redirect_uri": "http://localhost:3000/callback",
            "state": "test_state",
            "code_challenge": "challenge",
            "code_challenge_method": "invalid"
        })

        assert response.status_code == 400
        assert "Invalid code_challenge_method" in response.json()["detail"]


class TestLoginEndpoint:
    """Test /login endpoint"""

    def test_login_success(self, client):
        """Test successful login"""
        verifier = generate_code_verifier()
        challenge = generate_code_challenge(verifier)
        redirect_uri = "http://localhost:3000/callback"
        state = "test_state_123"

        response = client.post("/v1/login", data={
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "state": state,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "username": "oauthtestuser",
            "password": "testpass123",
            "scope": "all"
        }, follow_redirects=False)

        assert response.status_code == 302

        # Check redirect location
        location = response.headers["location"]
        assert location.startswith(redirect_uri)

        # Parse query string
        parsed = urlparse(location)
        query_params = parse_qs(parsed.query)

        assert "code" in query_params
        assert "state" in query_params
        assert query_params["state"][0] == state

        # Verify auth code was stored
        auth_code = query_params["code"][0]
        code_data = retrieve_authorization_code(auth_code)
        assert code_data is not None
        assert code_data["username"] == "oauthtestuser"

    def test_login_invalid_username(self, client):
        """Test login with invalid username"""
        response = client.post("/v1/login", data={
            "response_type": "code",
            "redirect_uri": "http://localhost:3000/callback",
            "state": "test_state",
            "code_challenge": "challenge",
            "code_challenge_method": "S256",
            "username": "nonexistent",
            "password": "password",
            "scope": "all"
        })

        assert response.status_code == 401
        assert "Invalid username or password" in response.json()["detail"]

    def test_login_invalid_password(self, client):
        """Test login with invalid password"""
        response = client.post("/v1/login", data={
            "response_type": "code",
            "redirect_uri": "http://localhost:3000/callback",
            "state": "test_state",
            "code_challenge": "challenge",
            "code_challenge_method": "S256",
            "username": "oauthtestuser",
            "password": "wrongpassword",
            "scope": "all"
        })

        assert response.status_code == 401
        assert "Invalid username or password" in response.json()["detail"]


class TestTokenEndpoint:
    """Test /token endpoint"""

    def test_token_exchange_success(self, client):
        """Test successful token exchange"""
        verifier = generate_code_verifier()
        challenge = generate_code_challenge(verifier)
        redirect_uri = "http://localhost:3000/callback"

        # First, get authorization code via login
        login_response = client.post("/v1/login", data={
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "state": "test_state",
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "username": "oauthtestuser",
            "password": "testpass123",
            "scope": "all"
        }, follow_redirects=False)

        assert login_response.status_code == 302

        # Extract authorization code
        location = login_response.headers["location"]
        parsed = urlparse(location)
        query_params = parse_qs(parsed.query)
        auth_code = query_params["code"][0]

        # Exchange code for token
        token_response = client.post("/v1/token", data={
            "grant_type": "authorization_code",
            "code": auth_code,
            "code_verifier": verifier,
            "redirect_uri": redirect_uri
        })

        assert token_response.status_code == 200

        token_data = token_response.json()
        assert "access_token" in token_data
        assert token_data["token_type"] == "Bearer"
        assert token_data["expires_in"] == 86400

        # Verify token is valid
        access_token = token_data["access_token"]
        payload = verify_access_token(access_token)
        assert payload is not None
        assert payload["preferred_username"] == "oauthtestuser"

    def test_token_exchange_invalid_grant_type(self, client):
        """Test token exchange with invalid grant type"""
        response = client.post("/v1/token", data={
            "grant_type": "invalid",
            "code": "test_code",
            "code_verifier": "verifier",
            "redirect_uri": "http://localhost:3000/callback"
        })

        assert response.status_code == 400
        assert "Invalid grant_type" in response.json()["detail"]

    def test_token_exchange_invalid_code(self, client):
        """Test token exchange with invalid authorization code"""
        response = client.post("/v1/token", data={
            "grant_type": "authorization_code",
            "code": "invalid_code",
            "code_verifier": "verifier",
            "redirect_uri": "http://localhost:3000/callback"
        })

        assert response.status_code == 400
        assert "Invalid or expired authorization code" in response.json()["detail"]

    def test_token_exchange_redirect_uri_mismatch(self, client):
        """Test token exchange with mismatched redirect URI"""
        verifier = generate_code_verifier()
        challenge = generate_code_challenge(verifier)
        redirect_uri = "http://localhost:3000/callback"

        # Get authorization code
        login_response = client.post("/v1/login", data={
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "state": "test_state",
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "username": "oauthtestuser",
            "password": "testpass123",
            "scope": "all"
        }, follow_redirects=False)

        location = login_response.headers["location"]
        parsed = urlparse(location)
        query_params = parse_qs(parsed.query)
        auth_code = query_params["code"][0]

        # Try to exchange with different redirect URI
        token_response = client.post("/v1/token", data={
            "grant_type": "authorization_code",
            "code": auth_code,
            "code_verifier": verifier,
            "redirect_uri": "http://different-url.com/callback"
        })

        assert token_response.status_code == 400
        assert "Redirect URI mismatch" in token_response.json()["detail"]

    def test_token_exchange_invalid_verifier(self, client):
        """Test token exchange with invalid PKCE verifier"""
        verifier = generate_code_verifier()
        challenge = generate_code_challenge(verifier)
        redirect_uri = "http://localhost:3000/callback"

        # Get authorization code
        login_response = client.post("/v1/login", data={
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "state": "test_state",
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "username": "oauthtestuser",
            "password": "testpass123",
            "scope": "all"
        }, follow_redirects=False)

        location = login_response.headers["location"]
        parsed = urlparse(location)
        query_params = parse_qs(parsed.query)
        auth_code = query_params["code"][0]

        # Try to exchange with wrong verifier
        wrong_verifier = generate_code_verifier()
        token_response = client.post("/v1/token", data={
            "grant_type": "authorization_code",
            "code": auth_code,
            "code_verifier": wrong_verifier,
            "redirect_uri": redirect_uri
        })

        assert token_response.status_code == 400
        assert "Invalid code_verifier" in token_response.json()["detail"]

    def test_token_exchange_code_reuse(self, client):
        """Test that authorization code cannot be reused"""
        verifier = generate_code_verifier()
        challenge = generate_code_challenge(verifier)
        redirect_uri = "http://localhost:3000/callback"

        # Get authorization code
        login_response = client.post("/v1/login", data={
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "state": "test_state",
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "username": "oauthtestuser",
            "password": "testpass123",
            "scope": "all"
        }, follow_redirects=False)

        location = login_response.headers["location"]
        parsed = urlparse(location)
        query_params = parse_qs(parsed.query)
        auth_code = query_params["code"][0]

        # First exchange should succeed
        token_response1 = client.post("/v1/token", data={
            "grant_type": "authorization_code",
            "code": auth_code,
            "code_verifier": verifier,
            "redirect_uri": redirect_uri
        })

        assert token_response1.status_code == 200

        # Second exchange with same code should fail
        token_response2 = client.post("/v1/token", data={
            "grant_type": "authorization_code",
            "code": auth_code,
            "code_verifier": verifier,
            "redirect_uri": redirect_uri
        })

        assert token_response2.status_code == 400
        assert "Invalid or expired authorization code" in token_response2.json()["detail"]


class TestCompleteOAuthFlow:
    """Test the complete OAuth2 flow from start to finish"""

    def test_complete_flow(self, client):
        """Test complete OAuth2 authorization code flow with PKCE"""
        # 1. Generate PKCE parameters
        verifier = generate_code_verifier()
        challenge = generate_code_challenge(verifier)
        redirect_uri = "http://localhost:3000/callback"
        state = "random_state_123"

        # 2. Request authorization page
        auth_response = client.get("/v1/authorize", params={
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "state": state,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "scope": "all"
        })

        assert auth_response.status_code == 200
        assert "Username" in auth_response.text

        # 3. Submit login credentials
        login_response = client.post("/v1/login", data={
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "state": state,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "username": "oauthtestuser",
            "password": "testpass123",
            "scope": "all"
        }, follow_redirects=False)

        assert login_response.status_code == 302

        # 4. Extract authorization code from redirect
        location = login_response.headers["location"]
        parsed = urlparse(location)
        query_params = parse_qs(parsed.query)
        auth_code = query_params["code"][0]
        returned_state = query_params["state"][0]

        assert returned_state == state

        # 5. Exchange authorization code for access token
        token_response = client.post("/v1/token", data={
            "grant_type": "authorization_code",
            "code": auth_code,
            "code_verifier": verifier,
            "redirect_uri": redirect_uri
        })

        assert token_response.status_code == 200

        token_data = token_response.json()
        access_token = token_data["access_token"]

        # 6. Verify access token
        payload = verify_access_token(access_token)
        assert payload is not None
        assert payload["preferred_username"] == "oauthtestuser"
        assert payload["scope"] == "all"
        assert "realm_access" in payload
        assert "roles" in payload["realm_access"]
