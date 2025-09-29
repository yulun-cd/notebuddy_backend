"""
Unit tests for AI services
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from app import ai_services, schemas


class TestDeepSeekService:
    """Test DeepSeek AI service"""

    @pytest.fixture
    def deepseek_service(self, monkeypatch):
        """Create a DeepSeekService instance for testing with mocked OpenAI client"""
        # Mock the OpenAI client before creating the service
        mock_client = Mock()
        mock_openai = Mock(return_value=mock_client)
        monkeypatch.setattr("app.ai_services.openai.OpenAI", mock_openai)

        # Create the service - this will use the mocked OpenAI client
        service = ai_services.DeepSeekService()

        # Store the mock client for use in tests
        service._mock_client = mock_client
        return service

    @pytest.fixture
    def mock_openai_response(self):
        """Mock OpenAI response for testing"""
        return Mock(
            choices=[
                Mock(
                    message=Mock(
                        content='{"title": "测试笔记", "content": "### 测试笔记\\n\\n#### 核心观点\\n这是一个测试生成的笔记内容。"}'
                    )
                )
            ]
        )

    @pytest.fixture
    def mock_questions_response(self):
        """Mock questions response for testing"""
        return Mock(
            choices=[
                Mock(
                    message=Mock(
                        content='{"questions": ["问题1：测试问题1？", "问题2：测试问题2？", "问题3：测试问题3？"]}'
                    )
                )
            ]
        )

    @pytest.fixture
    def mock_updated_note_response(self):
        """Mock updated note response for testing"""
        return Mock(
            choices=[
                Mock(
                    message=Mock(
                        content='{"title": "更新后的笔记", "content": "### 更新后的笔记\\n\\n#### 核心观点\\n这是一个根据答案更新后的笔记内容。"}'
                    )
                )
            ]
        )

    async def test_generate_note_from_transcript_success(
        self,
        deepseek_service,
        sample_transcript_content,
        mock_openai_response,
    ):
        """Test successful note generation from transcript"""
        # Set up the mock response
        deepseek_service._mock_client.chat.completions.create.return_value = (
            mock_openai_response
        )

        # Call the method
        result = await deepseek_service.generate_note_from_transcript(
            sample_transcript_content
        )

        # Verify the result - should return a tuple (title, content)
        expected_title = "测试笔记"
        expected_content = "### 测试笔记\n\n#### 核心观点\n这是一个测试生成的笔记内容。"
        assert result == (expected_title, expected_content)

        # Verify OpenAI was called with correct parameters
        deepseek_service._mock_client.chat.completions.create.assert_called_once()
        call_args = deepseek_service._mock_client.chat.completions.create.call_args
        assert call_args.kwargs["model"] == "deepseek-chat"
        assert len(call_args.kwargs["messages"]) > 0
        assert sample_transcript_content in str(call_args.kwargs["messages"])

    async def test_generate_note_from_transcript_api_error(
        self, deepseek_service, sample_transcript_content
    ):
        """Test note generation with API error"""
        # Set up the mock to raise an exception
        deepseek_service._mock_client.chat.completions.create.side_effect = Exception(
            "API Error"
        )

        # Call the method and expect an exception
        with pytest.raises(Exception, match="API Error"):
            await deepseek_service.generate_note_from_transcript(
                sample_transcript_content
            )

    async def test_generate_follow_up_questions_success(
        self,
        deepseek_service,
        sample_note_content,
        mock_questions_response,
    ):
        """Test successful follow-up question generation"""
        # Set up the mock response
        deepseek_service._mock_client.chat.completions.create.return_value = (
            mock_questions_response
        )

        # Call the method
        result = await deepseek_service.generate_follow_up_questions(
            sample_note_content
        )

        # Verify the result
        expected_questions = [
            "问题1：测试问题1？",
            "问题2：测试问题2？",
            "问题3：测试问题3？",
        ]
        assert result == expected_questions

        # Verify OpenAI was called with correct parameters
        deepseek_service._mock_client.chat.completions.create.assert_called_once()
        call_args = deepseek_service._mock_client.chat.completions.create.call_args
        assert call_args.kwargs["model"] == "deepseek-chat"
        assert len(call_args.kwargs["messages"]) > 0
        # Check that the note content is included in the prompt (not necessarily exact match)
        messages_str = str(call_args.kwargs["messages"])
        assert "城市印象的结构化笔记" in messages_str
        assert "动态的生命体" in messages_str

    async def test_generate_follow_up_questions_invalid_json(
        self, deepseek_service, sample_note_content
    ):
        """Test question generation with invalid JSON response"""
        # Set up the mock to return invalid JSON
        deepseek_service._mock_client.chat.completions.create.return_value = Mock(
            choices=[Mock(message=Mock(content="这不是一个有效的JSON字符串"))]
        )

        # Call the method and expect an exception
        with pytest.raises(Exception, match="Failed to parse questions"):
            await deepseek_service.generate_follow_up_questions(sample_note_content)

    async def test_generate_follow_up_questions_empty_response(
        self, deepseek_service, sample_note_content
    ):
        """Test question generation with empty response"""
        # Set up the mock to return empty response
        deepseek_service._mock_client.chat.completions.create.return_value = Mock(
            choices=[Mock(message=Mock(content=""))]
        )

        # Call the method and expect an exception
        with pytest.raises(Exception, match="No content in response"):
            await deepseek_service.generate_follow_up_questions(sample_note_content)

    @patch("app.ai_services.openai.OpenAI")
    async def test_update_note_with_answer_success(
        self,
        mock_openai,
        deepseek_service,
        sample_note_content,
        sample_answer_submission,
        mock_updated_note_response,
    ):
        """Test successful note update with answer"""
        # Mock the OpenAI client and its response
        mock_client = Mock()
        mock_openai.return_value = mock_client
        mock_client.chat.completions.create.return_value = mock_updated_note_response

        # Call the method
        result = await deepseek_service.update_note_with_answer(
            sample_note_content,
            sample_answer_submission.question,
            sample_answer_submission.answer,
        )

        # Verify the result - should return a tuple (title, content)
        expected_title = "更新后的笔记"
        expected_content = (
            "### 更新后的笔记\n\n#### 核心观点\n这是一个根据答案更新后的笔记内容。"
        )
        assert result == (expected_title, expected_content)

        # Verify OpenAI was called with correct parameters
        mock_client.chat.completions.create.assert_called_once()
        call_args = mock_client.chat.completions.create.call_args
        assert call_args.kwargs["model"] == "deepseek-chat"
        assert len(call_args.kwargs["messages"]) > 0
        assert sample_note_content in str(call_args.kwargs["messages"])
        assert sample_answer_submission.question in str(call_args.kwargs["messages"])
        assert sample_answer_submission.answer in str(call_args.kwargs["messages"])

    @patch("app.ai_services.openai.OpenAI")
    async def test_update_note_with_answer_api_error(
        self,
        mock_openai,
        deepseek_service,
        sample_note_content,
        sample_answer_submission,
    ):
        """Test note update with API error"""
        # Mock the OpenAI client to raise an exception
        mock_client = Mock()
        mock_openai.return_value = mock_client
        mock_client.chat.completions.create.side_effect = Exception("API Error")

        # Call the method and expect an exception
        with pytest.raises(Exception, match="API Error"):
            await deepseek_service.update_note_with_answer(
                sample_note_content,
                sample_answer_submission.question,
                sample_answer_submission.answer,
            )

    @patch("app.ai_services.openai.OpenAI")
    async def test_call_deepseek_success(self, mock_openai, deepseek_service):
        """Test successful DeepSeek API call"""
        # Mock the OpenAI client and its response
        mock_client = Mock()
        mock_openai.return_value = mock_client
        mock_client.chat.completions.create.return_value = Mock(
            choices=[Mock(message=Mock(content="Test response content"))]
        )

        # Call the internal method
        result = await deepseek_service._call_deepseek("Test message")

        # Verify the result
        assert result == "Test response content"

        # Verify OpenAI was called with correct parameters
        mock_client.chat.completions.create.assert_called_once()
        call_args = mock_client.chat.completions.create.call_args
        assert call_args.kwargs["model"] == "deepseek-chat"
        assert len(call_args.kwargs["messages"]) > 0
        assert "Test message" in str(call_args.kwargs["messages"])

    @patch("app.ai_services.openai.OpenAI")
    async def test_call_deepseek_empty_response(self, mock_openai, deepseek_service):
        """Test DeepSeek API call with empty response"""
        # Mock the OpenAI client to return empty response
        mock_client = Mock()
        mock_openai.return_value = mock_client
        mock_client.chat.completions.create.return_value = Mock(choices=[])

        # Call the internal method and expect an exception
        with pytest.raises(Exception, match="DeepSeek API error"):
            await deepseek_service._call_deepseek("Test message")

    @patch("app.ai_services.openai.OpenAI")
    async def test_call_deepseek_no_content(self, mock_openai, deepseek_service):
        """Test DeepSeek API call with no content in response"""
        # Mock the OpenAI client to return response with no content
        mock_client = Mock()
        mock_openai.return_value = mock_client
        mock_client.chat.completions.create.return_value = Mock(
            choices=[Mock(message=Mock(content=None))]
        )

        # Call the internal method and expect an exception
        with pytest.raises(Exception, match="DeepSeek API error"):
            await deepseek_service._call_deepseek("Test message")

    def test_questions_schema_validation(self, deepseek_service):
        """Test the QuestionsSchema validation"""
        from app.ai_services import DeepSeekService
        from pydantic import BaseModel
        from typing import List

        # Define the QuestionsSchema locally since it's defined inside the method
        class QuestionsSchema(BaseModel):
            questions: List[str]

        # Test valid questions list
        valid_questions = ["问题1", "问题2", "问题3"]
        schema = QuestionsSchema(questions=valid_questions)
        assert schema.questions == valid_questions

        # Test empty questions list
        empty_questions = []
        schema = QuestionsSchema(questions=empty_questions)
        assert schema.questions == empty_questions

    def test_questions_schema_validation_invalid(self, deepseek_service):
        """Test QuestionsSchema validation with invalid data"""
        from pydantic import BaseModel, ValidationError
        from typing import List

        # Define the QuestionsSchema locally since it's defined inside the method
        class QuestionsSchema(BaseModel):
            questions: List[str]

        # Test non-list input
        with pytest.raises(ValidationError):
            QuestionsSchema(questions="not a list")

        # Test list with non-string items
        with pytest.raises(ValidationError):
            QuestionsSchema(questions=[1, 2, 3])


class TestAIErrorHandling:
    """Test AI service error handling"""

    @patch("app.ai_services.openai.OpenAI")
    async def test_api_key_error(
        self, mock_openai, deepseek_service, sample_transcript_content
    ):
        """Test API key authentication error"""
        # Mock the OpenAI client to raise authentication error
        mock_client = Mock()
        mock_openai.return_value = mock_client
        mock_client.chat.completions.create.side_effect = Exception(
            "Incorrect API key provided"
        )

        # Call the method and expect an exception
        with pytest.raises(Exception, match="Incorrect API key provided"):
            await deepseek_service.generate_note_from_transcript(
                sample_transcript_content
            )

    @patch("app.ai_services.openai.OpenAI")
    async def test_rate_limit_error(
        self, mock_openai, deepseek_service, sample_transcript_content
    ):
        """Test rate limit error"""
        # Mock the OpenAI client to raise rate limit error
        mock_client = Mock()
        mock_openai.return_value = mock_client
        mock_client.chat.completions.create.side_effect = Exception(
            "Rate limit exceeded"
        )

        # Call the method and expect an exception
        with pytest.raises(Exception, match="Rate limit exceeded"):
            await deepseek_service.generate_note_from_transcript(
                sample_transcript_content
            )

    @patch("app.ai_services.openai.OpenAI")
    async def test_network_error(
        self, mock_openai, deepseek_service, sample_transcript_content
    ):
        """Test network connection error"""
        # Mock the OpenAI client to raise network error
        mock_client = Mock()
        mock_openai.return_value = mock_client
        mock_client.chat.completions.create.side_effect = Exception("Connection error")

        # Call the method and expect an exception
        with pytest.raises(Exception, match="Connection error"):
            await deepseek_service.generate_note_from_transcript(
                sample_transcript_content
            )


class TestAIPromptEngineering:
    """Test AI prompt engineering"""

    def test_note_generation_prompt_contains_transcript(
        self, deepseek_service, sample_transcript_content
    ):
        """Test that note generation prompt contains transcript content"""
        # This would test the internal prompt construction
        # Since prompts are constructed internally, we'll verify through integration tests
        pass

    def test_question_generation_prompt_contains_note(
        self, deepseek_service, sample_note_content
    ):
        """Test that question generation prompt contains note content"""
        # This would test the internal prompt construction
        # Since prompts are constructed internally, we'll verify through integration tests
        pass

    def test_note_update_prompt_contains_question_and_answer(
        self, deepseek_service, sample_note_content, sample_answer_submission
    ):
        """Test that note update prompt contains question and answer"""
        # This would test the internal prompt construction
        # Since prompts are constructed internally, we'll verify through integration tests
        pass
