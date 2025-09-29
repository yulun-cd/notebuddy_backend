from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine
from databases import Database
import os
import json
from dotenv import load_dotenv
from datetime import datetime, timedelta

from . import models, schemas, crud, auth, ai_services
from .auth import get_current_user, security


load_dotenv()

# Database setup - support environment-specific databases
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
if ENVIRONMENT == "test":
    DATABASE_URL = os.getenv(
        "TEST_DATABASE_URL", "sqlite+aiosqlite:///./test_notebuddy.db"
    )
else:
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./notebuddy.db")

database = Database(DATABASE_URL)

# SQLAlchemy setup for table creation
engine = create_engine(DATABASE_URL.replace("+aiosqlite", ""))
models.Base.metadata.create_all(bind=engine)

# FastAPI app
app = FastAPI(
    title="NoteBuddy Backend",
    description="AI-powered note generation from Chinese transcripts using DeepSeek",
    version="1.0.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Database dependency
async def get_db():
    await database.connect()
    try:
        yield database
    finally:
        await database.disconnect()


# Create a dependency that includes database session
async def get_current_active_user(credentials=Depends(security), db=Depends(get_db)):
    return await get_current_user(credentials, db)


# Authentication endpoints
@app.post("/auth/register", response_model=schemas.User)
async def register(user: schemas.UserCreate, db=Depends(get_db)):
    # Check if email already exists
    existing_user_by_email = await crud.get_user_by_email(db, user.email)
    if existing_user_by_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    return await crud.create_user(db, user)


@app.post("/auth/login", response_model=schemas.Token)
async def login(user_login: schemas.UserLogin, db=Depends(get_db)):
    user = await auth.authenticate_user(db, user_login.email, user_login.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    # Create access token
    access_token = auth.create_access_token(data={"sub": user["email"]})

    # Create refresh token
    refresh_token = auth.create_refresh_token()
    refresh_token_hash = auth.get_refresh_token_hash(refresh_token)
    expires_at = datetime.utcnow() + timedelta(days=auth.REFRESH_TOKEN_EXPIRE_DAYS)

    # Store refresh token in database
    from .models import RefreshToken

    query = RefreshToken.__table__.insert().values(
        user_id=user["id"],
        token_hash=refresh_token_hash,
        expires_at=expires_at,
        created_at=datetime.utcnow(),
    )
    await db.execute(query)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@app.post("/auth/refresh", response_model=schemas.Token)
async def refresh_token(
    refresh_request: schemas.RefreshTokenRequest, db=Depends(get_db)
):
    from .models import RefreshToken

    # Find the refresh token in database
    query = RefreshToken.__table__.select().where(
        RefreshToken.expires_at > datetime.utcnow()
    )
    tokens = await db.fetch_all(query)

    # Find matching token
    matching_token = None
    for token in tokens:
        if auth.verify_refresh_token(
            refresh_request.refresh_token, token["token_hash"]
        ):
            matching_token = token
            break

    if not matching_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )

    # Get user
    user = await crud.get_user(db, matching_token["user_id"])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )

    # Create new access token
    access_token = auth.create_access_token(data={"sub": user["email"]})

    # Create new refresh token (token rotation)
    new_refresh_token = auth.create_refresh_token()
    new_refresh_token_hash = auth.get_refresh_token_hash(new_refresh_token)
    expires_at = datetime.utcnow() + timedelta(days=auth.REFRESH_TOKEN_EXPIRE_DAYS)

    # Update refresh token in database
    update_query = (
        RefreshToken.__table__.update()
        .where(RefreshToken.id == matching_token["id"])
        .values(
            token_hash=new_refresh_token_hash,
            expires_at=expires_at,
            created_at=datetime.utcnow(),
        )
    )
    await db.execute(update_query)

    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
    }


# Transcript endpoints
@app.post("/transcripts/", response_model=schemas.Transcript)
async def create_transcript(
    transcript: schemas.TranscriptCreate,
    current_user: models.User = Depends(get_current_active_user),
    db=Depends(get_db),
):
    return await crud.create_transcript(db, transcript, current_user.id)


@app.get("/transcripts/", response_model=list[schemas.Transcript])
async def read_transcripts(
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(get_current_active_user),
    db=Depends(get_db),
):
    transcripts = await crud.get_user_transcripts(
        db, current_user.id, skip=skip, limit=limit
    )
    return transcripts


@app.get("/transcripts/{transcript_id}", response_model=schemas.Transcript)
async def read_transcript(
    transcript_id: int,
    current_user: models.User = Depends(get_current_active_user),
    db=Depends(get_db),
):
    transcript = await crud.get_transcript(db, transcript_id, current_user.id)
    if transcript is None:
        raise HTTPException(status_code=404, detail="Transcript not found")
    return transcript


@app.put("/transcripts/{transcript_id}", response_model=schemas.Transcript)
async def update_transcript(
    transcript_id: int,
    transcript_update: schemas.TranscriptUpdate,
    current_user: models.User = Depends(get_current_active_user),
    db=Depends(get_db),
):
    # Update the transcript
    update_data = transcript_update.model_dump(exclude_unset=True)
    transcript = await crud.update_transcript(
        db, transcript_id, update_data, current_user.id
    )
    if transcript is None:
        raise HTTPException(status_code=404, detail="Transcript not found")
    return transcript


@app.delete("/transcripts/{transcript_id}")
async def delete_transcript(
    transcript_id: int,
    current_user: models.User = Depends(get_current_active_user),
    db=Depends(get_db),
):
    transcript = await crud.delete_transcript(db, transcript_id, current_user.id)
    if transcript is None:
        raise HTTPException(status_code=404, detail="Transcript not found")
    return {"message": "Transcript deleted successfully"}


# AI-powered note generation endpoints
@app.post(
    "/transcripts/{transcript_id}/generate-note",
    response_model=schemas.NoteGenerationResponse,
)
async def generate_note_from_transcript(
    transcript_id: int,
    current_user: models.User = Depends(get_current_active_user),
    db=Depends(get_db),
):
    # Get the transcript
    transcript = await crud.get_transcript(db, transcript_id, current_user.id)
    if transcript is None:
        raise HTTPException(status_code=404, detail="Transcript not found")

    # Check if note already exists for this transcript
    existing_note = await crud.get_note_by_transcript(
        db, transcript_id, current_user.id
    )
    if existing_note:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Note already exists for this transcript",
        )

    # Generate note using DeepSeek
    try:
        note_title, note_content = (
            await ai_services.deepseek_service.generate_note_from_transcript(
                transcript.content
            )
        )
    except Exception as e:
        if ENVIRONMENT == "Production":
            detail = "Internal error. Please contact the product team."
        else:
            error_message = str(e)
            # Provide more specific error messages
            if (
                "API key" in error_message.lower()
                or "authorization" in error_message.lower()
            ):
                detail = "DeepSeek API authentication failed. Please check your API key configuration."
            elif (
                "connection" in error_message.lower()
                or "timeout" in error_message.lower()
            ):
                detail = "Unable to connect to DeepSeek API. Please check your internet connection."
            elif "quota" in error_message.lower() or "limit" in error_message.lower():
                detail = "DeepSeek API quota exceeded. Please check your usage limits."
            else:
                detail = f"Error generating note: {error_message}"

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
        )

    # Create the note
    note_data = schemas.NoteCreate(
        title=note_title,
        content=note_content,
        transcript_id=transcript_id,
    )

    note = await crud.create_note(db, note_data, current_user.id)

    return schemas.NoteGenerationResponse(
        note=note, message="Note generated successfully"
    )


@app.post(
    "/notes/{note_id}/generate-questions",
    response_model=schemas.FollowUpQuestionsResponse,
)
async def generate_follow_up_questions(
    note_id: int,
    current_user: models.User = Depends(get_current_active_user),
    db=Depends(get_db),
):
    # Get the note
    note = await crud.get_note(db, note_id, current_user.id)
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found")

    # Generate follow-up questions using DeepSeek
    try:
        questions = await ai_services.deepseek_service.generate_follow_up_questions(
            note.content
        )
    except Exception as e:
        error_message = str(e)
        # Provide more specific error messages
        if (
            "API key" in error_message.lower()
            or "authorization" in error_message.lower()
        ):
            detail = "DeepSeek API authentication failed. Please check your API key configuration."
        elif (
            "connection" in error_message.lower() or "timeout" in error_message.lower()
        ):
            detail = "Unable to connect to DeepSeek API. Please check your internet connection."
        elif "quota" in error_message.lower() or "limit" in error_message.lower():
            detail = "DeepSeek API quota exceeded. Please check your usage limits."
        else:
            detail = f"Error generating questions: {error_message}"

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
        )

    return schemas.FollowUpQuestionsResponse(
        questions=questions, message="Follow-up questions generated successfully"
    )


@app.post(
    "/notes/{note_id}/update-with-answer", response_model=schemas.NoteUpdateResponse
)
async def update_note_with_answer(
    note_id: int,
    answer_data: schemas.AnswerSubmission,
    current_user: models.User = Depends(get_current_active_user),
    db=Depends(get_db),
):
    # Get the note
    note = await crud.get_note(db, note_id, current_user.id)
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found")

    # Validate that both question and answer are provided
    if not answer_data.question or not answer_data.answer:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Both question and answer are required",
        )

    # Update note with answer using DeepSeek
    try:
        updated_title, updated_content = (
            await ai_services.deepseek_service.update_note_with_answer(
                note.content, answer_data.question, answer_data.answer
            )
        )
    except Exception as e:
        error_message = str(e)
        # Provide more specific error messages
        if (
            "API key" in error_message.lower()
            or "authorization" in error_message.lower()
        ):
            detail = "DeepSeek API authentication failed. Please check your API key configuration."
        elif (
            "connection" in error_message.lower() or "timeout" in error_message.lower()
        ):
            detail = "Unable to connect to DeepSeek API. Please check your internet connection."
        elif "quota" in error_message.lower() or "limit" in error_message.lower():
            detail = "DeepSeek API quota exceeded. Please check your usage limits."
        else:
            detail = f"Error updating note: {error_message}"

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
        )

    # Update the note in database
    updated_note = await crud.update_note_with_answers(
        db, note_id, updated_title, updated_content, current_user.id
    )

    return schemas.NoteUpdateResponse(
        note=updated_note, message="Note updated successfully with answer"
    )


# Note endpoints
@app.post("/notes/", response_model=schemas.Note)
async def create_note(
    note: schemas.NoteCreate,
    current_user: models.User = Depends(get_current_active_user),
    db=Depends(get_db),
):
    return await crud.create_note(db, note, current_user.id)


@app.get("/notes/", response_model=list[schemas.Note])
async def read_notes(
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(get_current_active_user),
    db=Depends(get_db),
):
    notes = await crud.get_user_notes(db, current_user.id, skip=skip, limit=limit)
    return notes


@app.get("/notes/{note_id}", response_model=schemas.Note)
async def read_note(
    note_id: int,
    current_user: models.User = Depends(get_current_active_user),
    db=Depends(get_db),
):
    note = await crud.get_note(db, note_id, current_user.id)
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found")
    return note


@app.put("/notes/{note_id}", response_model=schemas.Note)
async def update_note(
    note_id: int,
    note_update: schemas.NoteUpdate,
    current_user: models.User = Depends(get_current_active_user),
    db=Depends(get_db),
):
    # Update the note
    update_data = note_update.model_dump(exclude_unset=True)
    note = await crud.update_note(db, note_id, update_data, current_user.id)
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found")
    return note


@app.delete("/notes/{note_id}")
async def delete_note(
    note_id: int,
    current_user: models.User = Depends(get_current_active_user),
    db=Depends(get_db),
):
    note = await crud.delete_note(db, note_id, current_user.id)
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found")
    return {"message": "Note deleted successfully"}


# Health check endpoint
@app.get("/")
async def root():
    return {"message": "NoteBuddy Backend API is running"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
