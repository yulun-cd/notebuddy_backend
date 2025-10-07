"""
Integration tests for API endpoints
"""

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app
from app import schemas, crud


class TestAuthenticationEndpoints:
    """Test authentication endpoints"""

    async def test_register_success(self, client, database):
        """Test successful user registration"""
        user_data = {"email": "newuser@example.com", "password": "newpassword123"}

        response = client.post("/auth/register", json=user_data)

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == user_data["email"]
        assert "id" in data
        assert "created_at" in data
        assert "password" not in data  # Password should not be returned

    async def test_register_duplicate_email(self, client, database, test_user):
        """Test registration with duplicate email"""
        user_data = {
            "email": test_user["email"],  # Use existing email
            "password": "newpassword123",
        }

        response = client.post("/auth/register", json=user_data)

        assert response.status_code == 400
        assert "Email already registered" in response.json()["detail"]

    async def test_register_invalid_email(self, client, database):
        """Test registration with invalid email"""
        user_data = {"email": "invalid-email", "password": "password123"}

        response = client.post("/auth/register", json=user_data)

        assert response.status_code == 422  # Validation error

    async def test_login_success(self, client, database, test_user):
        """Test successful login"""
        login_data = {"email": test_user["email"], "password": "testpassword123"}

        response = client.post("/auth/login", json=login_data)

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"

    async def test_login_wrong_password(self, client, database, test_user):
        """Test login with wrong password"""
        login_data = {"email": test_user["email"], "password": "wrongpassword"}

        response = client.post("/auth/login", json=login_data)

        assert response.status_code == 401
        assert "Incorrect email or password" in response.json()["detail"]

    async def test_login_nonexistent_user(self, client, database):
        """Test login with non-existent user"""
        login_data = {"email": "nonexistent@example.com", "password": "password123"}

        response = client.post("/auth/login", json=login_data)

        assert response.status_code == 401
        assert "Incorrect email or password" in response.json()["detail"]


class TestTranscriptEndpoints:
    """Test transcript endpoints"""

    @pytest.fixture
    def authenticated_client(self, client, test_user):
        """Create authenticated test client"""
        # Login to get token
        login_data = {"email": test_user["email"], "password": "testpassword123"}
        response = client.post("/auth/login", json=login_data)
        token = response.json()["access_token"]

        # Set authorization header
        client.headers.update({"Authorization": f"Bearer {token}"})
        return client

    async def test_create_transcript_success(
        self, authenticated_client, database, test_user
    ):
        """Test successful transcript creation"""
        transcript_data = {
            "title": "Test Transcript",
            "content": "This is a test transcript content.",
        }

        response = authenticated_client.post("/transcripts/", json=transcript_data)

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == transcript_data["title"]
        assert data["content"] == transcript_data["content"]
        assert data["user_id"] == test_user["id"]
        assert "id" in data
        assert "created_at" in data
        assert data["updated_at"] is None  # Should be None on creation

    async def test_create_transcript_unauthenticated(self, client, database):
        """Test transcript creation without authentication"""
        transcript_data = {
            "title": "Test Transcript",
            "content": "This is a test transcript content.",
        }

        response = client.post("/transcripts/", json=transcript_data)

        assert response.status_code == 401  # Unauthorized

    async def test_get_transcript_success(
        self, authenticated_client, database, test_transcript
    ):
        """Test successful transcript retrieval"""
        response = authenticated_client.get(f"/transcripts/{test_transcript['id']}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_transcript["id"]
        assert data["title"] == test_transcript["title"]
        assert data["content"] == test_transcript["content"]

    async def test_get_transcript_not_found(self, authenticated_client, database):
        """Test transcript retrieval with non-existent ID"""
        response = authenticated_client.get("/transcripts/99999")

        assert response.status_code == 404
        assert "Transcript not found" in response.json()["detail"]

    async def test_get_transcript_unauthorized(self, authenticated_client, database):
        """Test transcript retrieval with wrong user"""
        # Create a transcript with a different user
        other_user_data = schemas.UserCreate(
            email="otheruser@example.com", password="password123"
        )
        other_user = await crud.create_user(database, other_user_data)

        transcript_data = schemas.TranscriptCreate(
            title="Other User Transcript",
            content="This transcript belongs to another user.",
        )
        other_transcript = await crud.create_transcript(
            database, transcript_data, other_user["id"]
        )

        # Try to access other user's transcript
        response = authenticated_client.get(f"/transcripts/{other_transcript['id']}")

        assert response.status_code == 404  # Should not be found due to user isolation

    async def test_get_all_transcripts(
        self, authenticated_client, database, test_transcript
    ):
        """Test getting all transcripts for user"""
        response = authenticated_client.get("/transcripts/")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert any(t["id"] == test_transcript["id"] for t in data)

    async def test_update_transcript_success(
        self, authenticated_client, database, test_transcript
    ):
        """Test successful transcript update"""
        update_data = {
            "title": "Updated Transcript Title",
            "content": "Updated transcript content.",
        }

        response = authenticated_client.put(
            f"/transcripts/{test_transcript['id']}", json=update_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == update_data["title"]
        assert data["content"] == update_data["content"]
        assert data["updated_at"] is not None  # Should be set on update

    async def test_update_transcript_partial(
        self, authenticated_client, database, test_transcript
    ):
        """Test partial transcript update"""
        update_data = {"title": "Partially Updated Title"}

        response = authenticated_client.put(
            f"/transcripts/{test_transcript['id']}", json=update_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == update_data["title"]
        assert data["content"] == test_transcript["content"]  # Should remain unchanged

    async def test_delete_transcript_success(
        self, authenticated_client, database, test_user
    ):
        """Test successful transcript deletion"""
        # Create a transcript to delete
        transcript_data = schemas.TranscriptCreate(
            title="Transcript to Delete", content="This transcript will be deleted."
        )
        transcript = await crud.create_transcript(
            database, transcript_data, test_user["id"]
        )

        response = authenticated_client.delete(f"/transcripts/{transcript['id']}")

        assert response.status_code == 200
        assert "message" in response.json()

        # Verify it's gone
        get_response = authenticated_client.get(f"/transcripts/{transcript['id']}")
        assert get_response.status_code == 404

    async def test_delete_transcript_cascade_note_deletion(
        self, authenticated_client, database, test_user, test_transcript
    ):
        """Test that deleting a transcript also deletes its related note via API"""
        # Create a note for the transcript
        note_data = schemas.NoteCreate(
            title="Test Note for Cascade",
            content="This note should be deleted with the transcript.",
            transcript_id=test_transcript["id"],
        )
        note = await crud.create_note(database, note_data, test_user["id"])

        # Verify note exists via API
        note_response = authenticated_client.get(f"/notes/{note['id']}")
        assert note_response.status_code == 200

        # Delete the transcript via API
        delete_response = authenticated_client.delete(
            f"/transcripts/{test_transcript['id']}"
        )
        assert delete_response.status_code == 200

        # Verify transcript is gone
        transcript_response = authenticated_client.get(
            f"/transcripts/{test_transcript['id']}"
        )
        assert transcript_response.status_code == 404

        # Verify note is also gone (cascade deletion)
        note_response_after = authenticated_client.get(f"/notes/{note['id']}")
        assert note_response_after.status_code == 404


class TestNoteEndpoints:
    """Test note endpoints"""

    @pytest.fixture
    def authenticated_client(self, client, test_user):
        """Create authenticated test client"""
        # Login to get token
        login_data = {"email": test_user["email"], "password": "testpassword123"}
        response = client.post("/auth/login", json=login_data)
        token = response.json()["access_token"]

        # Set authorization header
        client.headers.update({"Authorization": f"Bearer {token}"})
        return client

    async def test_create_note_success(
        self, authenticated_client, database, test_user, test_transcript
    ):
        """Test successful note creation"""
        note_data = {
            "title": "Test Note",
            "content": "This is a test note content.",
            "transcript_id": test_transcript["id"],
        }

        response = authenticated_client.post("/notes/", json=note_data)

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == note_data["title"]
        assert data["content"] == note_data["content"]
        assert data["transcript_id"] == test_transcript["id"]
        assert data["user_id"] == test_user["id"]
        assert "id" in data
        assert "created_at" in data
        assert data["updated_at"] is None  # Should be None on creation

    async def test_create_note_invalid_transcript(
        self, authenticated_client, database, test_user
    ):
        """Test note creation with invalid transcript ID"""
        note_data = {
            "title": "Test Note",
            "content": "This is a test note content.",
            "transcript_id": 99999,  # Non-existent transcript
        }

        response = authenticated_client.post("/notes/", json=note_data)

        # Should succeed since transcript validation happens at business logic level
        assert response.status_code == 200

    async def test_get_note_success(self, authenticated_client, database, test_note):
        """Test successful note retrieval"""
        response = authenticated_client.get(f"/notes/{test_note['id']}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_note["id"]
        assert data["title"] == test_note["title"]
        assert data["content"] == test_note["content"]

    async def test_get_note_not_found(self, authenticated_client, database):
        """Test note retrieval with non-existent ID"""
        response = authenticated_client.get("/notes/99999")

        assert response.status_code == 404
        assert "Note not found" in response.json()["detail"]

    async def test_get_all_notes(self, authenticated_client, database, test_note):
        """Test getting all notes for user"""
        response = authenticated_client.get("/notes/")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert any(n["id"] == test_note["id"] for n in data)

    async def test_update_note_success(self, authenticated_client, database, test_note):
        """Test successful note update"""
        update_data = {
            "title": "Updated Note Title",
            "content": "Updated note content.",
        }

        response = authenticated_client.put(
            f"/notes/{test_note['id']}", json=update_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == update_data["title"]
        assert data["content"] == update_data["content"]
        assert data["updated_at"] is not None  # Should be set on update

    async def test_delete_note_success(
        self, authenticated_client, database, test_user, test_transcript
    ):
        """Test successful note deletion"""
        # Create a note to delete
        note_data = schemas.NoteCreate(
            title="Note to Delete",
            content="This note will be deleted.",
            transcript_id=test_transcript["id"],
        )
        note = await crud.create_note(database, note_data, test_user["id"])

        response = authenticated_client.delete(f"/notes/{note['id']}")

        assert response.status_code == 200
        assert "message" in response.json()

        # Verify it's gone
        get_response = authenticated_client.get(f"/notes/{note['id']}")
        assert get_response.status_code == 404


class TestAIEndpoints:
    """Test AI-powered endpoints"""

    @pytest.fixture
    def authenticated_client(self, client, test_user):
        """Create authenticated test client"""
        # Login to get token
        login_data = {"email": test_user["email"], "password": "testpassword123"}
        response = client.post("/auth/login", json=login_data)
        token = response.json()["access_token"]

        # Set authorization header
        client.headers.update({"Authorization": f"Bearer {token}"})
        return client

    @patch("app.ai_services.DeepSeekService.generate_note_from_transcript")
    async def test_generate_note_success(
        self, mock_generate, authenticated_client, database, test_transcript
    ):
        """Test successful note generation"""
        # Mock the AI service response
        mock_generate.return_value = (
            "### 测试生成的笔记\n\n#### 核心观点\n这是一个测试生成的笔记内容。"
        )

        response = authenticated_client.post(
            f"/transcripts/{test_transcript['id']}/generate-note"
        )

        assert response.status_code == 200
        data = response.json()
        assert "note" in data
        assert "message" in data
        assert data["message"] == "Note generated successfully"

        # Verify the AI service was called
        mock_generate.assert_called_once()

    async def test_generate_note_nonexistent_transcript(
        self, authenticated_client, database
    ):
        """Test note generation with non-existent transcript"""
        response = authenticated_client.post("/transcripts/99999/generate-note")

        assert response.status_code == 404
        assert "Transcript not found" in response.json()["detail"]

    @patch("app.ai_services.DeepSeekService.generate_follow_up_questions")
    async def test_generate_questions_success(
        self, mock_generate, authenticated_client, database, test_note
    ):
        """Test successful question generation"""
        # Mock the AI service response
        mock_generate.return_value = ["问题1：测试问题1？", "问题2：测试问题2？"]

        response = authenticated_client.post(
            f"/notes/{test_note['id']}/generate-questions"
        )

        assert response.status_code == 200
        data = response.json()
        assert "questions" in data
        assert "message" in data
        assert data["message"] == "Follow-up questions generated successfully"
        assert len(data["questions"]) == 2

        # Verify the AI service was called
        mock_generate.assert_called_once()

    async def test_generate_questions_nonexistent_note(
        self, authenticated_client, database
    ):
        """Test question generation with non-existent note"""
        response = authenticated_client.post("/notes/99999/generate-questions")

        assert response.status_code == 404
        assert "Note not found" in response.json()["detail"]

    @patch("app.ai_services.DeepSeekService.update_note_with_answer")
    async def test_update_note_with_answer_success(
        self, mock_update, authenticated_client, database, test_note
    ):
        """Test successful note update with answer"""
        # Mock the AI service response
        mock_update.return_value = (
            "### 更新后的笔记\n\n#### 核心观点\n这是一个根据答案更新后的笔记内容。"
        )

        answer_data = {"question": "测试问题？", "answer": "测试答案"}

        response = authenticated_client.post(
            f"/notes/{test_note['id']}/update-with-answer", json=answer_data
        )

        assert response.status_code == 200
        data = response.json()
        assert "note" in data
        assert "message" in data
        assert data["message"] == "Note updated successfully with answer"

        # Verify the AI service was called
        mock_update.assert_called_once()

    async def test_update_note_with_answer_missing_fields(
        self, authenticated_client, database, test_note
    ):
        """Test note update with missing question or answer"""
        # Missing question
        answer_data = {"answer": "测试答案"}
        response = authenticated_client.post(
            f"/notes/{test_note['id']}/update-with-answer", json=answer_data
        )
        assert response.status_code == 400

        # Missing answer
        answer_data = {"question": "测试问题？"}
        response = authenticated_client.post(
            f"/notes/{test_note['id']}/update-with-answer", json=answer_data
        )
        assert response.status_code == 400

    async def test_update_note_with_answer_nonexistent_note(
        self, authenticated_client, database
    ):
        """Test note update with non-existent note"""
        answer_data = {"question": "测试问题？", "answer": "测试答案"}

        response = authenticated_client.post(
            "/notes/99999/update-with-answer", json=answer_data
        )

        assert response.status_code == 404
        assert "Note not found" in response.json()["detail"]


class TestHealthEndpoints:
    """Test health and root endpoints"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)

    async def test_root_endpoint(self, client):
        """Test root endpoint"""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "NoteBuddy Backend API is running" in data["message"]

    async def test_health_endpoint(self, client):
        """Test health endpoint"""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"
