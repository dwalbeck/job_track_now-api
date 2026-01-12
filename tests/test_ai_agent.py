import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from app.utils.ai_agent import AiAgent


class TestAiAgentInit:
    """Test suite for AiAgent initialization."""

    @patch('app.utils.ai_agent.settings')
    @patch('app.utils.ai_agent.OpenAI')
    def test_init_loads_settings(self, mock_openai, mock_settings):
        """Test that AiAgent initialization loads settings."""
        mock_db = Mock()
        mock_settings.load_llm_settings_from_db = Mock()
        mock_settings.openai_api_key = "test-key"
        mock_settings.ai_model = "gpt-4"
        mock_settings.openai_project = None
        mock_settings.resume_extract_llm = "gpt-4o-mini"
        mock_settings.job_extract_llm = "gpt-4o-mini"
        mock_settings.rewrite_llm = "gpt-4"
        mock_settings.cover_llm = "gpt-4"

        agent = AiAgent(mock_db)

        assert agent.db == mock_db
        assert agent.api_key == "test-key"
        assert agent.model == "gpt-4"
        mock_settings.load_llm_settings_from_db.assert_called_once_with(mock_db)
        mock_openai.assert_called_once()

    @patch('app.utils.ai_agent.settings')
    @patch('app.utils.ai_agent.OpenAI')
    def test_init_with_project(self, mock_openai, mock_settings):
        """Test initialization with OpenAI project."""
        mock_db = Mock()
        mock_settings.load_llm_settings_from_db = Mock()
        mock_settings.openai_api_key = "test-key"
        mock_settings.ai_model = "gpt-4"
        mock_settings.openai_project = "test-project"
        mock_settings.resume_extract_llm = "gpt-4o-mini"
        mock_settings.job_extract_llm = "gpt-4o-mini"
        mock_settings.rewrite_llm = "gpt-4"
        mock_settings.cover_llm = "gpt-4"

        agent = AiAgent(mock_db)

        # Verify project was passed to OpenAI init
        call_kwargs = mock_openai.call_args[1]
        assert call_kwargs['project'] == "test-project"


class TestLoadPrompt:
    """Test suite for _load_prompt method."""

    @patch('app.utils.ai_agent.settings')
    @patch('app.utils.ai_agent.OpenAI')
    def test_load_prompt_success(self, mock_openai, mock_settings):
        """Test loading a prompt template successfully."""
        mock_db = Mock()
        mock_settings.load_llm_settings_from_db = Mock()
        mock_settings.openai_api_key = "test-key"
        mock_settings.ai_model = "gpt-4"
        mock_settings.openai_project = None
        mock_settings.resume_extract_llm = "gpt-4o-mini"
        mock_settings.job_extract_llm = "gpt-4o-mini"
        mock_settings.rewrite_llm = "gpt-4"
        mock_settings.cover_llm = "gpt-4"

        agent = AiAgent(mock_db)

        # Mock the prompt file
        mock_prompt_content = "Test prompt template with {variable}"
        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = mock_prompt_content

            result = agent._load_prompt("test_prompt")

            assert result == mock_prompt_content

    @patch('app.utils.ai_agent.settings')
    @patch('app.utils.ai_agent.OpenAI')
    def test_load_prompt_not_found(self, mock_openai, mock_settings):
        """Test loading non-existent prompt template."""
        mock_db = Mock()
        mock_settings.load_llm_settings_from_db = Mock()
        mock_settings.openai_api_key = "test-key"
        mock_settings.ai_model = "gpt-4"
        mock_settings.openai_project = None
        mock_settings.resume_extract_llm = "gpt-4o-mini"
        mock_settings.job_extract_llm = "gpt-4o-mini"
        mock_settings.rewrite_llm = "gpt-4"
        mock_settings.cover_llm = "gpt-4"

        agent = AiAgent(mock_db)

        with patch('pathlib.Path.exists', return_value=False):
            with pytest.raises(FileNotFoundError, match="Prompt template not found"):
                agent._load_prompt("nonexistent_prompt")


class TestGetMethods:
    """Test suite for get_html and get_markdown methods."""

    @patch('app.utils.ai_agent.settings')
    @patch('app.utils.ai_agent.OpenAI')
    def test_get_html_success(self, mock_openai, mock_settings):
        """Test getting HTML content from database."""
        mock_db = Mock()
        mock_settings.load_llm_settings_from_db = Mock()
        mock_settings.openai_api_key = "test-key"
        mock_settings.ai_model = "gpt-4"
        mock_settings.openai_project = None
        mock_settings.resume_extract_llm = "gpt-4o-mini"
        mock_settings.job_extract_llm = "gpt-4o-mini"
        mock_settings.rewrite_llm = "gpt-4"
        mock_settings.cover_llm = "gpt-4"

        # Mock database result
        mock_result = Mock()
        mock_result.__getitem__ = Mock(return_value="<html>Test HTML</html>")
        mock_db.execute.return_value.first.return_value = mock_result

        agent = AiAgent(mock_db)
        result = agent.get_html(1)

        assert result == "<html>Test HTML</html>"
        mock_db.execute.assert_called_once()

    @patch('app.utils.ai_agent.settings')
    @patch('app.utils.ai_agent.OpenAI')
    def test_get_html_not_found(self, mock_openai, mock_settings):
        """Test getting HTML when resume not found."""
        mock_db = Mock()
        mock_settings.load_llm_settings_from_db = Mock()
        mock_settings.openai_api_key = "test-key"
        mock_settings.ai_model = "gpt-4"
        mock_settings.openai_project = None
        mock_settings.resume_extract_llm = "gpt-4o-mini"
        mock_settings.job_extract_llm = "gpt-4o-mini"
        mock_settings.rewrite_llm = "gpt-4"
        mock_settings.cover_llm = "gpt-4"

        mock_db.execute.return_value.first.return_value = None

        agent = AiAgent(mock_db)

        with pytest.raises(ValueError, match="Resume not found"):
            agent.get_html(999)

    @patch('app.utils.ai_agent.settings')
    @patch('app.utils.ai_agent.OpenAI')
    def test_get_markdown_success(self, mock_openai, mock_settings):
        """Test getting Markdown content from database."""
        mock_db = Mock()
        mock_settings.load_llm_settings_from_db = Mock()
        mock_settings.openai_api_key = "test-key"
        mock_settings.ai_model = "gpt-4"
        mock_settings.openai_project = None
        mock_settings.resume_extract_llm = "gpt-4o-mini"
        mock_settings.job_extract_llm = "gpt-4o-mini"
        mock_settings.rewrite_llm = "gpt-4"
        mock_settings.cover_llm = "gpt-4"

        # Mock database result
        mock_result = Mock()
        mock_result.__getitem__ = Mock(return_value="# Test Markdown")
        mock_db.execute.return_value.first.return_value = mock_result

        agent = AiAgent(mock_db)
        result = agent.get_markdown(1)

        assert result == "# Test Markdown"

    @patch('app.utils.ai_agent.settings')
    @patch('app.utils.ai_agent.OpenAI')
    def test_get_markdown_not_found(self, mock_openai, mock_settings):
        """Test getting Markdown when resume not found."""
        mock_db = Mock()
        mock_settings.load_llm_settings_from_db = Mock()
        mock_settings.openai_api_key = "test-key"
        mock_settings.ai_model = "gpt-4"
        mock_settings.openai_project = None
        mock_settings.resume_extract_llm = "gpt-4o-mini"
        mock_settings.job_extract_llm = "gpt-4o-mini"
        mock_settings.rewrite_llm = "gpt-4"
        mock_settings.cover_llm = "gpt-4"

        mock_db.execute.return_value.first.return_value = None

        agent = AiAgent(mock_db)

        with pytest.raises(ValueError, match="Resume not found"):
            agent.get_markdown(999)


class TestExtractData:
    """Test suite for extract_data method."""

    @patch('app.utils.ai_agent.settings')
    @patch('app.utils.ai_agent.OpenAI')
    def test_extract_data_success(self, mock_openai, mock_settings):
        """Test extracting data from resume with valid JSON response."""
        mock_db = Mock()
        mock_settings.load_llm_settings_from_db = Mock()
        mock_settings.openai_api_key = "test-key"
        mock_settings.ai_model = "gpt-4"
        mock_settings.openai_project = None
        mock_settings.resume_extract_llm = "gpt-4o-mini"
        mock_settings.job_extract_llm = "gpt-4o-mini"
        mock_settings.rewrite_llm = "gpt-4"
        mock_settings.cover_llm = "gpt-4"

        # Mock database to return HTML
        mock_result = Mock()
        mock_result.__getitem__ = Mock(return_value="<html>Resume</html>")
        mock_db.execute.return_value.first.return_value = mock_result

        # Mock OpenAI response
        mock_client = Mock()
        mock_response = Mock()
        mock_choice = Mock()
        mock_message = Mock()
        expected_data = {
            "job_title": {"job_title": "Software Engineer", "line_number": 5},
            "suggestions": ["Add quantifiable achievements", "Improve formatting"]
        }
        mock_message.content = json.dumps(expected_data)
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        agent = AiAgent(mock_db)

        # Mock _load_prompt
        with patch.object(agent, '_load_prompt', return_value="Test prompt {resume_html}"):
            result = agent.extract_data(1)

            assert result['job_title'] == {"job_title": "Software Engineer", "line_number": 5}
            assert len(result['suggestions']) == 2
            mock_client.chat.completions.create.assert_called_once()

    @patch('app.utils.ai_agent.settings')
    @patch('app.utils.ai_agent.OpenAI')
    def test_extract_data_markdown_json(self, mock_openai, mock_settings):
        """Test extracting data with JSON in markdown code blocks."""
        mock_db = Mock()
        mock_settings.load_llm_settings_from_db = Mock()
        mock_settings.openai_api_key = "test-key"
        mock_settings.ai_model = "gpt-4"
        mock_settings.openai_project = None
        mock_settings.resume_extract_llm = "gpt-4o-mini"
        mock_settings.job_extract_llm = "gpt-4o-mini"
        mock_settings.rewrite_llm = "gpt-4"
        mock_settings.cover_llm = "gpt-4"

        # Mock database
        mock_result = Mock()
        mock_result.__getitem__ = Mock(return_value="<html>Resume</html>")
        mock_db.execute.return_value.first.return_value = mock_result

        # Mock OpenAI response with markdown-wrapped JSON
        mock_client = Mock()
        mock_response = Mock()
        mock_choice = Mock()
        mock_message = Mock()
        expected_data = {
            "job_title": {"job_title": "Developer", "line_number": 3},
            "suggestions": ["Improve skills section"]
        }
        mock_message.content = f"```json\n{json.dumps(expected_data)}\n```"
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        agent = AiAgent(mock_db)

        with patch.object(agent, '_load_prompt', return_value="Test prompt"):
            result = agent.extract_data(1)

            assert result['job_title']['job_title'] == "Developer"

    @patch('app.utils.ai_agent.settings')
    @patch('app.utils.ai_agent.OpenAI')
    def test_extract_data_invalid_json(self, mock_openai, mock_settings):
        """Test extracting data with invalid JSON response."""
        mock_db = Mock()
        mock_settings.load_llm_settings_from_db = Mock()
        mock_settings.openai_api_key = "test-key"
        mock_settings.ai_model = "gpt-4"
        mock_settings.openai_project = None
        mock_settings.resume_extract_llm = "gpt-4o-mini"
        mock_settings.job_extract_llm = "gpt-4o-mini"
        mock_settings.rewrite_llm = "gpt-4"
        mock_settings.cover_llm = "gpt-4"

        # Mock database
        mock_result = Mock()
        mock_result.__getitem__ = Mock(return_value="<html>Resume</html>")
        mock_db.execute.return_value.first.return_value = mock_result

        # Mock OpenAI response with invalid JSON
        mock_client = Mock()
        mock_response = Mock()
        mock_choice = Mock()
        mock_message = Mock()
        mock_message.content = "This is not valid JSON"
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        agent = AiAgent(mock_db)

        with patch.object(agent, '_load_prompt', return_value="Test prompt"):
            with pytest.raises(ValueError, match="Failed to parse AI response as JSON"):
                agent.extract_data(1)


class TestJobExtraction:
    """Test suite for job_extraction method."""

    @patch('app.utils.ai_agent.settings')
    @patch('app.utils.ai_agent.OpenAI')
    def test_job_extraction_success(self, mock_openai, mock_settings):
        """Test successful job extraction."""
        mock_db = Mock()
        mock_settings.load_llm_settings_from_db = Mock()
        mock_settings.openai_api_key = "test-key"
        mock_settings.ai_model = "gpt-4"
        mock_settings.openai_project = None
        mock_settings.resume_extract_llm = "gpt-4o-mini"
        mock_settings.job_extract_llm = "gpt-4o-mini"
        mock_settings.rewrite_llm = "gpt-4"
        mock_settings.cover_llm = "gpt-4"

        # Mock database - job exists and has description
        mock_job_result = Mock()
        mock_job_result.job_id = 1
        mock_desc_result = Mock()
        mock_desc_result.__getitem__ = Mock(return_value="Job description with Python and AWS requirements")

        def execute_side_effect(*args, **kwargs):
            if "job.job_id" in str(args[0]):
                mock_result = Mock()
                mock_result.first.return_value = mock_job_result
                return mock_result
            else:
                mock_result = Mock()
                mock_result.first.return_value = mock_desc_result
                return mock_result

        mock_db.execute.side_effect = execute_side_effect

        # Mock OpenAI response
        mock_client = Mock()
        mock_response = Mock()
        mock_choice = Mock()
        mock_message = Mock()
        expected_data = {
            "job_qualification": "5+ years Python, AWS experience required",
            "keywords": ["Python", "AWS", "Docker", "Kubernetes"]
        }
        mock_message.content = json.dumps(expected_data)
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        agent = AiAgent(mock_db)

        with patch.object(agent, '_load_prompt', return_value="Extract from {job_desc}"):
            result = agent.job_extraction(1)

            assert result['job_qualification'] == "5+ years Python, AWS experience required"
            assert len(result['keywords']) == 4
            assert "Python" in result['keywords']

    @patch('app.utils.ai_agent.settings')
    @patch('app.utils.ai_agent.OpenAI')
    def test_job_extraction_job_not_found(self, mock_openai, mock_settings):
        """Test job extraction when job doesn't exist."""
        mock_db = Mock()
        mock_settings.load_llm_settings_from_db = Mock()
        mock_settings.openai_api_key = "test-key"
        mock_settings.ai_model = "gpt-4"
        mock_settings.openai_project = None
        mock_settings.resume_extract_llm = "gpt-4o-mini"
        mock_settings.job_extract_llm = "gpt-4o-mini"
        mock_settings.rewrite_llm = "gpt-4"
        mock_settings.cover_llm = "gpt-4"

        mock_db.execute.return_value.first.return_value = None

        agent = AiAgent(mock_db)

        with pytest.raises(ValueError, match="Job not found or inactive"):
            agent.job_extraction(999)

    @patch('app.utils.ai_agent.settings')
    @patch('app.utils.ai_agent.OpenAI')
    def test_job_extraction_no_description(self, mock_openai, mock_settings):
        """Test job extraction when job has no description."""
        mock_db = Mock()
        mock_settings.load_llm_settings_from_db = Mock()
        mock_settings.openai_api_key = "test-key"
        mock_settings.ai_model = "gpt-4"
        mock_settings.openai_project = None
        mock_settings.resume_extract_llm = "gpt-4o-mini"
        mock_settings.job_extract_llm = "gpt-4o-mini"
        mock_settings.rewrite_llm = "gpt-4"
        mock_settings.cover_llm = "gpt-4"

        # Job exists but no description
        mock_job_result = Mock()
        mock_job_result.job_id = 1

        def execute_side_effect(*args, **kwargs):
            if "job.job_id" in str(args[0]):
                mock_result = Mock()
                mock_result.first.return_value = mock_job_result
                return mock_result
            else:
                mock_result = Mock()
                mock_result.first.return_value = None
                return mock_result

        mock_db.execute.side_effect = execute_side_effect

        agent = AiAgent(mock_db)

        with pytest.raises(ValueError, match="No job description found"):
            agent.job_extraction(1)


class TestWriteCoverLetter:
    """Test suite for write_cover_letter method."""

    @patch('app.utils.ai_agent.settings')
    @patch('app.utils.ai_agent.OpenAI')
    def test_write_cover_letter_success(self, mock_openai, mock_settings):
        """Test successful cover letter generation."""
        mock_db = Mock()
        mock_settings.load_llm_settings_from_db = Mock()
        mock_settings.openai_api_key = "test-key"
        mock_settings.ai_model = "gpt-4"
        mock_settings.openai_project = None
        mock_settings.resume_extract_llm = "gpt-4o-mini"
        mock_settings.job_extract_llm = "gpt-4o-mini"
        mock_settings.rewrite_llm = "gpt-4"
        mock_settings.cover_llm = "gpt-4"

        # Mock OpenAI response
        mock_client = Mock()
        mock_response = Mock()
        mock_choice = Mock()
        mock_message = Mock()
        expected_data = {
            "letter_content": "Dear Hiring Manager,\n\nI am writing to express my interest..."
        }
        mock_message.content = json.dumps(expected_data)
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        agent = AiAgent(mock_db)

        with patch.object(agent, '_load_prompt', return_value="Generate letter"):
            result = agent.write_cover_letter(
                letter_tone="professional",
                letter_length="medium",
                instruction="Focus on technical skills",
                job_desc="Software Engineer position",
                company="Tech Corp",
                job_title="Senior Engineer",
                resume_md_rewrite="# Resume content",
                first_name="John",
                last_name="Doe",
                city="San Francisco",
                state="CA",
                email="john@example.com",
                phone="555-1234"
            )

            assert "letter_content" in result
            assert "Dear Hiring Manager" in result['letter_content']
            mock_client.chat.completions.create.assert_called_once()

    @patch('app.utils.ai_agent.settings')
    @patch('app.utils.ai_agent.OpenAI')
    def test_write_cover_letter_missing_key(self, mock_openai, mock_settings):
        """Test cover letter generation with missing letter_content key."""
        mock_db = Mock()
        mock_settings.load_llm_settings_from_db = Mock()
        mock_settings.openai_api_key = "test-key"
        mock_settings.ai_model = "gpt-4"
        mock_settings.openai_project = None
        mock_settings.resume_extract_llm = "gpt-4o-mini"
        mock_settings.job_extract_llm = "gpt-4o-mini"
        mock_settings.rewrite_llm = "gpt-4"
        mock_settings.cover_llm = "gpt-4"

        # Mock OpenAI response without letter_content key
        mock_client = Mock()
        mock_response = Mock()
        mock_choice = Mock()
        mock_message = Mock()
        mock_message.content = json.dumps({"wrong_key": "value"})
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        agent = AiAgent(mock_db)

        with patch.object(agent, '_load_prompt', return_value="Generate letter"):
            with pytest.raises(ValueError, match="Response missing required key"):
                agent.write_cover_letter(
                    letter_tone="professional",
                    letter_length="short",
                    instruction="",
                    job_desc="Job desc",
                    company="Company",
                    job_title="Title",
                    resume_md_rewrite="Resume",
                    first_name="John",
                    last_name="Doe",
                    city="City",
                    state="State",
                    email="email@test.com",
                    phone="555-1234"
                )
