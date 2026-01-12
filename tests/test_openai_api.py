import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import httpx


class TestGetLLMModels:
    """Test suite for GET /v1/openai/llm endpoint."""

    @patch('app.api.openai_api.httpx.AsyncClient')
    def test_get_llm_models_success(self, mock_client, client, test_db):
        """Test successfully retrieving LLM models from OpenAI."""
        # Mock response from OpenAI API
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "object": "list",
            "data": [
                {"id": "gpt-4o", "object": "model", "created": 1686588896, "owned_by": "openai"},
                {"id": "gpt-4o-mini", "object": "model", "created": 1686588800, "owned_by": "openai"},
                {"id": "gpt-3.5-turbo", "object": "model", "created": 1686588700, "owned_by": "openai"}
            ]
        }
        mock_response.raise_for_status = MagicMock()

        # Setup mock client with async context manager support
        async_mock_get = AsyncMock(return_value=mock_response)
        mock_client_instance = MagicMock()
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)
        mock_client_instance.get = async_mock_get
        mock_client.return_value = mock_client_instance

        response = client.get("/v1/openai/llm")

        assert response.status_code == 200
        data = response.json()

        # Verify models are returned sorted by created date (descending)
        assert isinstance(data, list)
        assert len(data) == 3
        assert data[0] == "gpt-4o"  # Newest first
        assert data[1] == "gpt-4o-mini"
        assert data[2] == "gpt-3.5-turbo"

    @patch('app.api.openai_api.httpx.AsyncClient')
    def test_get_llm_models_removes_duplicates(self, mock_client, client, test_db):
        """Test that duplicate model IDs are removed."""
        # Mock response with duplicate model IDs
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "object": "list",
            "data": [
                {"id": "gpt-4o", "object": "model", "created": 1686588896, "owned_by": "openai"},
                {"id": "gpt-4o-mini", "object": "model", "created": 1686588800, "owned_by": "openai"},
                {"id": "gpt-4o", "object": "model", "created": 1686588700, "owned_by": "openai"}  # Duplicate
            ]
        }
        mock_response.raise_for_status = MagicMock()

        async_mock_get = AsyncMock(return_value=mock_response)
        mock_client_instance = MagicMock()
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)
        mock_client_instance.get = async_mock_get
        mock_client.return_value = mock_client_instance

        response = client.get("/v1/openai/llm")

        assert response.status_code == 200
        data = response.json()

        # Verify duplicates are removed
        assert len(data) == 2
        assert data.count("gpt-4o") == 1

    @patch('app.api.openai_api.httpx.AsyncClient')
    def test_get_llm_models_http_error(self, mock_client, client, test_db):
        """Test error handling when OpenAI API returns HTTP error."""
        # Mock HTTP error
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Unauthorized", request=MagicMock(), response=mock_response
        )

        async_mock_get = AsyncMock(return_value=mock_response)
        mock_client_instance = MagicMock()
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)
        mock_client_instance.get = async_mock_get
        mock_client.return_value = mock_client_instance

        response = client.get("/v1/openai/llm")

        assert response.status_code == 502
        assert "Failed to fetch models from OpenAI API" in response.json()['detail']

    @patch('app.api.openai_api.httpx.AsyncClient')
    def test_get_llm_models_request_error(self, mock_client, client, test_db):
        """Test error handling when request to OpenAI fails."""
        # Mock request error
        mock_client_instance = AsyncMock()
        mock_client_instance.__aenter__.return_value = mock_client_instance
        mock_client_instance.__aexit__.return_value = None
        mock_client_instance.get.side_effect = httpx.RequestError("Connection failed")
        mock_client.return_value = mock_client_instance

        response = client.get("/v1/openai/llm")

        assert response.status_code == 503
        assert "Failed to connect to OpenAI API" in response.json()['detail']

    @patch('app.api.openai_api.httpx.AsyncClient')
    def test_get_llm_models_empty_list(self, mock_client, client, test_db):
        """Test handling of empty model list from OpenAI."""
        # Mock empty response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "object": "list",
            "data": []
        }
        mock_response.raise_for_status = MagicMock()

        async_mock_get = AsyncMock(return_value=mock_response)
        mock_client_instance = MagicMock()
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)
        mock_client_instance.get = async_mock_get
        mock_client.return_value = mock_client_instance

        response = client.get("/v1/openai/llm")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    @patch('app.api.openai_api.httpx.AsyncClient')
    def test_get_llm_models_sorts_by_created_desc(self, mock_client, client, test_db):
        """Test that models are sorted by created date in descending order."""
        # Mock response with models in random order
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "object": "list",
            "data": [
                {"id": "model-2", "object": "model", "created": 2000, "owned_by": "openai"},
                {"id": "model-1", "object": "model", "created": 3000, "owned_by": "openai"},  # Newest
                {"id": "model-3", "object": "model", "created": 1000, "owned_by": "openai"}   # Oldest
            ]
        }
        mock_response.raise_for_status = MagicMock()

        async_mock_get = AsyncMock(return_value=mock_response)
        mock_client_instance = MagicMock()
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)
        mock_client_instance.get = async_mock_get
        mock_client.return_value = mock_client_instance

        response = client.get("/v1/openai/llm")

        assert response.status_code == 200
        data = response.json()

        # Verify correct order (newest first)
        assert data[0] == "model-1"  # created: 3000
        assert data[1] == "model-2"  # created: 2000
        assert data[2] == "model-3"  # created: 1000

    @patch('app.api.openai_api.httpx.AsyncClient')
    def test_get_llm_models_handles_missing_created_field(self, mock_client, client, test_db):
        """Test handling of models without created field."""
        # Mock response with missing created fields
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "object": "list",
            "data": [
                {"id": "model-1", "object": "model", "created": 2000, "owned_by": "openai"},
                {"id": "model-2", "object": "model", "owned_by": "openai"},  # Missing created
                {"id": "model-3", "object": "model", "created": 3000, "owned_by": "openai"}
            ]
        }
        mock_response.raise_for_status = MagicMock()

        async_mock_get = AsyncMock(return_value=mock_response)
        mock_client_instance = MagicMock()
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)
        mock_client_instance.get = async_mock_get
        mock_client.return_value = mock_client_instance

        response = client.get("/v1/openai/llm")

        assert response.status_code == 200
        data = response.json()

        # Should still return all models, with missing created defaulting to 0
        assert len(data) == 3
        assert "model-1" in data
        assert "model-2" in data
        assert "model-3" in data
