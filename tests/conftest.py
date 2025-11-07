"""
Test configuration and fixtures for NoteBuddy backend tests
"""

import pytest
import asyncio
from databases import Database
from sqlalchemy import create_engine
import os

# Set test environment and mock API key before importing app modules
os.environ["ENVIRONMENT"] = "test"
os.environ["DEEPSEEK_API_KEY"] = "test-api-key-12345"
os.environ["SECRET_KEY"] = "test-secret-key"

from app import models, schemas, crud, auth, ai_services


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_database_url():
    """Get test database URL"""
    return "sqlite+aiosqlite:///./test_notebuddy.db"


@pytest.fixture(scope="session")
def database_engine(test_database_url):
    """Create database engine for table creation"""
    engine = create_engine(test_database_url.replace("+aiosqlite", ""))
    models.Base.metadata.create_all(bind=engine)
    yield engine
    models.Base.metadata.drop_all(bind=engine)
    # Clean up the database file
    import os

    db_file = "./test_notebuddy.db"
    if os.path.exists(db_file):
        os.remove(db_file)


@pytest.fixture
async def database(test_database_url, database_engine):
    """Create database connection for tests"""
    database = Database(test_database_url)
    await database.connect()
    yield database
    # Clean up all data between tests
    await database.execute("DELETE FROM notes")
    await database.execute("DELETE FROM transcripts")
    await database.execute("DELETE FROM users")
    await database.disconnect()


@pytest.fixture
async def test_user(database):
    """Create a test user"""
    user_data = schemas.UserCreate(
        email="test@example.com",
        password="testpassword123",
        first_name="Test",
        last_name="User",
        language="Chinese",
    )
    user = await crud.create_user(database, user_data)
    return user


@pytest.fixture
async def test_transcript(database, test_user):
    """Create a test transcript"""
    transcript_data = schemas.TranscriptCreate(
        title="Test Transcript",
        content="This is a test transcript content for unit testing.",
    )
    transcript = await crud.create_transcript(
        database, transcript_data, test_user["id"]
    )
    return transcript


@pytest.fixture
async def test_note(database, test_user, test_transcript):
    """Create a test note"""
    note_data = schemas.NoteCreate(
        title="Test Note",
        content="This is a test note content for unit testing.",
        transcript_id=test_transcript["id"],
    )
    note = await crud.create_note(database, note_data, test_user["id"])
    return note


@pytest.fixture
def test_user_login():
    """Test user login data"""
    return schemas.UserLogin(email="test@example.com", password="testpassword123")


@pytest.fixture
def mock_deepseek_api_key():
    """Mock DeepSeek API key for testing"""
    return "test-api-key-12345"


@pytest.fixture
def sample_transcript_content():
    """Sample transcript content for testing"""
    return "这座城市总有一种力量，把人吸引进来，有时候是因为机会，有时候只是因为它能给人一种匿名的自由。"


@pytest.fixture
def sample_note_content():
    """Sample note content for testing"""
    return "### 城市印象的结构化笔记\n\n#### 核心观点\n这座城市是一个动态的生命体，通过其内在的矛盾与张力，持续地吸引并塑造着身处其中的人们。"


@pytest.fixture
def sample_questions():
    """Sample questions for testing"""
    return [
        "这次工作流测试的主要目标是什么？",
        "笔记具体在哪些方面进行了更新？",
        "工作流测试的结果或发现是什么？",
    ]


@pytest.fixture
def sample_answer_submission():
    """Sample answer submission for testing"""
    return schemas.AnswerSubmission(
        question="这次工作流测试的主要目标是什么？", answer="在正文后面加十个'。'"
    )


@pytest.fixture
def deepseek_service():
    """Create a DeepSeekService instance for testing"""
    return ai_services.DeepSeekService()


@pytest.fixture
def client():
    """Create test client"""
    from fastapi.testclient import TestClient
    from app.main import app

    return TestClient(app)
