"""
Unit tests for CRUD operations
"""

import pytest
from app import schemas, crud


class TestUserCRUD:
    """Test user CRUD operations"""

    async def test_create_user(self, database):
        """Test creating a new user"""
        user_data = schemas.UserCreate(
            email="newuser@example.com", password="newpassword123"
        )
        user = await crud.create_user(database, user_data)

        assert user["email"] == "newuser@example.com"
        assert user["id"] is not None
        assert user["created_at"] is not None

    async def test_get_user_by_email(self, database, test_user):
        """Test getting user by email"""
        user = await crud.get_user_by_email(database, test_user["email"])

        assert user is not None
        assert user["email"] == test_user["email"]
        assert user["id"] == test_user["id"]

    async def test_get_user_by_email_not_found(self, database):
        """Test getting non-existent user by email"""
        user = await crud.get_user_by_email(database, "nonexistent@example.com")
        assert user is None

    async def test_get_user(self, database, test_user):
        """Test getting user by ID"""
        user = await crud.get_user(database, test_user["id"])

        assert user is not None
        assert user["email"] == test_user["email"]
        assert user["id"] == test_user["id"]

    async def test_get_user_not_found(self, database):
        """Test getting non-existent user by ID"""
        user = await crud.get_user(database, 99999)
        assert user is None


class TestTranscriptCRUD:
    """Test transcript CRUD operations"""

    async def test_create_transcript(self, database, test_user):
        """Test creating a new transcript"""
        transcript_data = schemas.TranscriptCreate(
            title="New Test Transcript", content="This is new test transcript content."
        )
        transcript = await crud.create_transcript(
            database, transcript_data, test_user["id"]
        )

        assert transcript["title"] == "New Test Transcript"
        assert transcript["content"] == "This is new test transcript content."
        assert transcript["user_id"] == test_user["id"]
        assert transcript["id"] is not None
        assert transcript["created_at"] is not None
        assert transcript["updated_at"] is None  # Should be None on creation

    async def test_get_transcript(self, database, test_transcript, test_user):
        """Test getting transcript by ID"""
        transcript = await crud.get_transcript(
            database, test_transcript["id"], test_user["id"]
        )

        assert transcript is not None
        assert transcript["title"] == test_transcript["title"]
        assert transcript["content"] == test_transcript["content"]
        assert transcript["user_id"] == test_user["id"]

    async def test_get_transcript_not_found(self, database, test_user):
        """Test getting non-existent transcript"""
        transcript = await crud.get_transcript(database, 99999, test_user["id"])
        assert transcript is None

    async def test_get_transcript_wrong_user(self, database, test_transcript):
        """Test getting transcript with wrong user ID"""
        transcript = await crud.get_transcript(database, test_transcript["id"], 99999)
        assert transcript is None

    async def test_get_user_transcripts(self, database, test_user, test_transcript):
        """Test getting all transcripts for a user"""
        transcripts = await crud.get_user_transcripts(database, test_user["id"])

        assert isinstance(transcripts, list)
        assert len(transcripts) >= 1
        assert any(t["id"] == test_transcript["id"] for t in transcripts)

    async def test_get_user_transcripts_empty(self, database):
        """Test getting transcripts for user with no transcripts"""
        # Create a new user with no transcripts
        user_data = schemas.UserCreate(
            email="emptyuser@example.com", password="password123"
        )
        user = await crud.create_user(database, user_data)

        transcripts = await crud.get_user_transcripts(database, user["id"])
        assert isinstance(transcripts, list)
        assert len(transcripts) == 0

    async def test_update_transcript(self, database, test_transcript, test_user):
        """Test updating a transcript"""
        update_data = {
            "title": "Updated Transcript Title",
            "content": "Updated transcript content.",
        }
        updated_transcript = await crud.update_transcript(
            database, test_transcript["id"], update_data, test_user["id"]
        )

        assert updated_transcript is not None
        assert updated_transcript["title"] == "Updated Transcript Title"
        assert updated_transcript["content"] == "Updated transcript content."
        assert updated_transcript["updated_at"] is not None  # Should be set on update

    async def test_update_transcript_partial(
        self, database, test_transcript, test_user
    ):
        """Test partial update of a transcript"""
        update_data = {"title": "Partially Updated Title"}
        updated_transcript = await crud.update_transcript(
            database, test_transcript["id"], update_data, test_user["id"]
        )

        assert updated_transcript is not None
        assert updated_transcript["title"] == "Partially Updated Title"
        assert (
            updated_transcript["content"] == test_transcript["content"]
        )  # Should remain unchanged

    async def test_update_transcript_not_found(self, database, test_user):
        """Test updating non-existent transcript"""
        update_data = {"title": "Updated Title"}
        updated_transcript = await crud.update_transcript(
            database, 99999, update_data, test_user["id"]
        )
        assert updated_transcript is None

    async def test_delete_transcript(self, database, test_user):
        """Test deleting a transcript"""
        # Create a transcript to delete
        transcript_data = schemas.TranscriptCreate(
            title="Transcript to Delete", content="This transcript will be deleted."
        )
        transcript = await crud.create_transcript(
            database, transcript_data, test_user["id"]
        )

        # Delete the transcript
        deleted_transcript = await crud.delete_transcript(
            database, transcript["id"], test_user["id"]
        )

        assert deleted_transcript is not None
        assert deleted_transcript["id"] == transcript["id"]

        # Verify it's gone
        retrieved_transcript = await crud.get_transcript(
            database, transcript["id"], test_user["id"]
        )
        assert retrieved_transcript is None

    async def test_delete_transcript_not_found(self, database, test_user):
        """Test deleting non-existent transcript"""
        deleted_transcript = await crud.delete_transcript(
            database, 99999, test_user["id"]
        )
        assert deleted_transcript is None

    async def test_delete_transcript_with_note_cascade(
        self, database, test_user, test_transcript
    ):
        """Test that deleting a transcript also deletes its related note"""
        # Create a note for the transcript
        note_data = schemas.NoteCreate(
            title="Test Note for Cascade",
            content="This note should be deleted with the transcript.",
            transcript_id=test_transcript["id"],
        )
        note = await crud.create_note(database, note_data, test_user["id"])

        # Verify note exists
        retrieved_note = await crud.get_note(database, note["id"], test_user["id"])
        assert retrieved_note is not None

        # Delete the transcript
        deleted_transcript = await crud.delete_transcript(
            database, test_transcript["id"], test_user["id"]
        )
        assert deleted_transcript is not None

        # Verify transcript is gone
        retrieved_transcript = await crud.get_transcript(
            database, test_transcript["id"], test_user["id"]
        )
        assert retrieved_transcript is None

        # Verify note is also gone (cascade deletion)
        retrieved_note_after = await crud.get_note(
            database, note["id"], test_user["id"]
        )
        assert retrieved_note_after is None

    async def test_delete_transcript_without_note(self, database, test_user):
        """Test that deleting a transcript without a note works correctly"""
        # Create a transcript without a note
        transcript_data = schemas.TranscriptCreate(
            title="Transcript Without Note",
            content="This transcript has no related note.",
        )
        transcript = await crud.create_transcript(
            database, transcript_data, test_user["id"]
        )

        # Delete the transcript
        deleted_transcript = await crud.delete_transcript(
            database, transcript["id"], test_user["id"]
        )
        assert deleted_transcript is not None

        # Verify transcript is gone
        retrieved_transcript = await crud.get_transcript(
            database, transcript["id"], test_user["id"]
        )
        assert retrieved_transcript is None


class TestNoteCRUD:
    """Test note CRUD operations"""

    async def test_create_note(self, database, test_user, test_transcript):
        """Test creating a new note"""
        note_data = schemas.NoteCreate(
            title="New Test Note",
            content="This is new test note content.",
            transcript_id=test_transcript["id"],
        )
        note = await crud.create_note(database, note_data, test_user["id"])

        assert note["title"] == "New Test Note"
        assert note["content"] == "This is new test note content."
        assert note["transcript_id"] == test_transcript["id"]
        assert note["user_id"] == test_user["id"]
        assert note["id"] is not None
        assert note["created_at"] is not None
        assert note["updated_at"] is None  # Should be None on creation

    async def test_get_note(self, database, test_note, test_user):
        """Test getting note by ID"""
        note = await crud.get_note(database, test_note["id"], test_user["id"])

        assert note is not None
        assert note["title"] == test_note["title"]
        assert note["content"] == test_note["content"]
        assert note["user_id"] == test_user["id"]

    async def test_get_note_not_found(self, database, test_user):
        """Test getting non-existent note"""
        note = await crud.get_note(database, 99999, test_user["id"])
        assert note is None

    async def test_get_note_wrong_user(self, database, test_note):
        """Test getting note with wrong user ID"""
        note = await crud.get_note(database, test_note["id"], 99999)
        assert note is None

    async def test_get_user_notes(self, database, test_user, test_note):
        """Test getting all notes for a user"""
        notes = await crud.get_user_notes(database, test_user["id"])

        assert isinstance(notes, list)
        assert len(notes) >= 1
        assert any(n["id"] == test_note["id"] for n in notes)

    async def test_get_user_notes_empty(self, database):
        """Test getting notes for user with no notes"""
        # Create a new user with no notes
        user_data = schemas.UserCreate(
            email="emptynoteuser@example.com", password="password123"
        )
        user = await crud.create_user(database, user_data)

        notes = await crud.get_user_notes(database, user["id"])
        assert isinstance(notes, list)
        assert len(notes) == 0

    async def test_get_note_by_transcript(self, database, test_note, test_user):
        """Test getting note by transcript ID"""
        note = await crud.get_note_by_transcript(
            database, test_note["transcript_id"], test_user["id"]
        )

        assert note is not None
        assert note["id"] == test_note["id"]
        assert note["transcript_id"] == test_note["transcript_id"]

    async def test_get_note_by_transcript_not_found(self, database, test_user):
        """Test getting note by non-existent transcript ID"""
        note = await crud.get_note_by_transcript(database, 99999, test_user["id"])
        assert note is None

    async def test_update_note(self, database, test_note, test_user):
        """Test updating a note"""
        update_data = {
            "title": "Updated Note Title",
            "content": "Updated note content.",
        }
        updated_note = await crud.update_note(
            database, test_note["id"], update_data, test_user["id"]
        )

        assert updated_note is not None
        assert updated_note["title"] == "Updated Note Title"
        assert updated_note["content"] == "Updated note content."
        assert updated_note["updated_at"] is not None  # Should be set on update

    async def test_update_note_partial(self, database, test_note, test_user):
        """Test partial update of a note"""
        update_data = {"title": "Partially Updated Title"}
        updated_note = await crud.update_note(
            database, test_note["id"], update_data, test_user["id"]
        )

        assert updated_note is not None
        assert updated_note["title"] == "Partially Updated Title"
        assert (
            updated_note["content"] == test_note["content"]
        )  # Should remain unchanged

    async def test_update_note_not_found(self, database, test_user):
        """Test updating non-existent note"""
        update_data = {"title": "Updated Title"}
        updated_note = await crud.update_note(
            database, 99999, update_data, test_user["id"]
        )
        assert updated_note is None

    async def test_update_note_with_answers(self, database, test_note, test_user):
        """Test updating note with answers"""
        updated_title = "Updated Note Title"
        updated_content = "This note has been updated with answers."
        updated_note = await crud.update_note_with_answers(
            database, test_note["id"], updated_title, updated_content, test_user["id"]
        )

        assert updated_note is not None
        assert updated_note["title"] == updated_title
        assert updated_note["content"] == updated_content
        assert updated_note["updated_at"] is not None  # Should be set on update

    async def test_update_note_with_answers_not_found(self, database, test_user):
        """Test updating non-existent note with answers"""
        updated_note = await crud.update_note_with_answers(
            database, 99999, "Updated Title", "Updated content", test_user["id"]
        )
        assert updated_note is None

    async def test_delete_note(self, database, test_user, test_transcript):
        """Test deleting a note"""
        # Create a note to delete
        note_data = schemas.NoteCreate(
            title="Note to Delete",
            content="This note will be deleted.",
            transcript_id=test_transcript["id"],
        )
        note = await crud.create_note(database, note_data, test_user["id"])

        # Delete the note
        deleted_note = await crud.delete_note(database, note["id"], test_user["id"])

        assert deleted_note is not None
        assert deleted_note["id"] == note["id"]

        # Verify it's gone
        retrieved_note = await crud.get_note(database, note["id"], test_user["id"])
        assert retrieved_note is None

    async def test_delete_note_not_found(self, database, test_user):
        """Test deleting non-existent note"""
        deleted_note = await crud.delete_note(database, 99999, test_user["id"])
        assert deleted_note is None
