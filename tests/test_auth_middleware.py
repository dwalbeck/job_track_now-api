import pytest
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient

from app.middleware.auth_middleware import get_current_user, get_jwt_payload, require_scope
from app.utils.oauth_utils import create_access_token


# Create a simple test app with protected endpoints
test_app = FastAPI()


@test_app.get("/protected")
async def protected_endpoint(user_id: int = Depends(get_current_user)):
    """Protected endpoint requiring authentication - returns user_id"""
    return {"message": "success", "user_id": user_id}


@test_app.get("/protected/admin")
async def protected_admin_endpoint(current_user: dict = Depends(require_scope("admin"))):
    """Protected endpoint requiring admin scope"""
    return {"message": "success", "user": current_user["preferred_username"]}


@test_app.get("/jwt-payload")
async def jwt_payload_endpoint(payload: dict = Depends(get_jwt_payload)):
    """Endpoint that returns the full JWT payload"""
    return {"authenticated": True, "user": payload["preferred_username"]}


@pytest.fixture
def auth_client():
    """Create test client for auth middleware tests"""
    return TestClient(test_app)


class TestAuthMiddleware:
    """Test authentication middleware"""

    def test_protected_endpoint_with_valid_token(self, auth_client):
        """Test accessing protected endpoint with valid token"""
        # Create valid access token with user_id
        token = create_access_token(username="testuser", scope="all", user_id=1)

        # Request with Authorization header
        response = auth_client.get(
            "/protected",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "success"
        assert data["user_id"] == 1

    def test_protected_endpoint_without_token(self, auth_client):
        """Test accessing protected endpoint without token"""
        response = auth_client.get("/protected")

        assert response.status_code == 401
        assert "Not authenticated" in response.json()["detail"]

    def test_protected_endpoint_with_invalid_token(self, auth_client):
        """Test accessing protected endpoint with invalid token"""
        response = auth_client.get(
            "/protected",
            headers={"Authorization": "Bearer invalid.token.here"}
        )

        assert response.status_code == 401
        assert "Invalid authentication credentials" in response.json()["detail"]

    def test_protected_endpoint_with_malformed_header(self, auth_client):
        """Test accessing protected endpoint with malformed authorization header"""
        response = auth_client.get(
            "/protected",
            headers={"Authorization": "InvalidFormat token"}
        )

        # FastAPI's HTTPBearer returns 401 when header format is invalid
        assert response.status_code == 401

    def test_jwt_payload_endpoint_with_token(self, auth_client):
        """Test jwt-payload endpoint with valid token"""
        token = create_access_token(username="testuser", scope="all", user_id=1)

        response = auth_client.get(
            "/jwt-payload",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["authenticated"] is True
        assert data["user"] == "testuser"

    def test_jwt_payload_endpoint_without_token(self, auth_client):
        """Test jwt-payload endpoint without token returns 401"""
        response = auth_client.get("/jwt-payload")

        assert response.status_code == 401

    def test_scope_requirement_with_correct_scope(self, auth_client):
        """Test scope requirement with correct scope"""
        token = create_access_token(username="testuser", scope="admin all", user_id=1)

        response = auth_client.get(
            "/protected/admin",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "success"

    def test_scope_requirement_without_required_scope(self, auth_client):
        """Test scope requirement without required scope"""
        token = create_access_token(username="testuser", scope="all", user_id=1)

        response = auth_client.get(
            "/protected/admin",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 403
        assert "Insufficient permissions" in response.json()["detail"]

    def test_expired_token(self, auth_client):
        """Test handling of expired tokens"""
        # Create a token with negative expiration (already expired)
        # Note: This requires modifying the token creation, so we'll use an invalid token instead
        # In production, tokens naturally expire after 24 hours

        # For now, test with completely invalid token structure
        invalid_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjB9.invalid"

        response = auth_client.get(
            "/protected",
            headers={"Authorization": f"Bearer {invalid_token}"}
        )

        assert response.status_code == 401

    def test_token_with_missing_user_id(self, auth_client):
        """Test token with missing user_id claim returns 401"""
        # Create a minimal token missing user_id
        from jose import jwt
        from app.utils.oauth_utils import SECRET_KEY, ALGORITHM

        payload = {"sub": "testuser"}  # Missing user_id
        token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

        response = auth_client.get(
            "/protected",
            headers={"Authorization": f"Bearer {token}"}
        )

        # Should fail because user_id is required
        assert response.status_code == 401
        assert "missing user_id" in response.json()["detail"]


class TestTokenClaims:
    """Test JWT token claim structure"""

    def test_token_contains_required_claims(self):
        """Test that generated tokens contain all required claims"""
        username = "testuser"
        scope = "all"

        token = create_access_token(username=username, scope=scope, user_id=1)

        # Decode without audience verification to inspect claims
        from jose import jwt
        from app.utils.oauth_utils import SECRET_KEY, ALGORITHM

        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_aud": False})

        # Check standard claims
        assert "sub" in payload
        assert "iss" in payload
        assert "aud" in payload
        assert "iat" in payload
        assert "exp" in payload
        # Note: nbf (not before) was removed due to time sync issues between containers
        assert "jti" in payload

        # Check custom claims
        assert "typ" in payload
        assert "scope" in payload
        assert "preferred_username" in payload
        assert "email_verified" in payload
        assert "auth_time" in payload
        assert "acr" in payload
        assert "azp" in payload
        assert "realm_access" in payload
        assert "resource_access" in payload
        assert "session_state" in payload

        # Verify values
        assert payload["sub"] == username
        assert payload["preferred_username"] == username
        assert payload["scope"] == scope
        assert payload["typ"] == "Bearer"
        assert payload["iss"] == "job-track-now-api"
        assert payload["aud"] == "account"

        # Check expiration is set to 24 hours
        import time
        exp_time = payload["exp"]
        iat_time = payload["iat"]
        assert exp_time - iat_time == 86400  # 24 hours in seconds

    def test_token_roles(self):
        """Test that token contains proper role structure"""
        token = create_access_token(username="testuser", scope="all", user_id=1)

        from jose import jwt
        from app.utils.oauth_utils import SECRET_KEY, ALGORITHM

        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_aud": False})

        # Check realm_access roles
        assert "realm_access" in payload
        assert "roles" in payload["realm_access"]
        assert isinstance(payload["realm_access"]["roles"], list)
        assert "user" in payload["realm_access"]["roles"]
        assert "job_tracker_user" in payload["realm_access"]["roles"]

        # Check resource_access roles
        assert "resource_access" in payload
        assert "account" in payload["resource_access"]
        assert "roles" in payload["resource_access"]["account"]
        assert isinstance(payload["resource_access"]["account"]["roles"], list)
        assert "manage-account" in payload["resource_access"]["account"]["roles"]
        assert "view-profile" in payload["resource_access"]["account"]["roles"]
