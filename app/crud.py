from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.orm import selectinload
from datetime import datetime
from . import models, schemas
from .auth import get_password_hash


# User CRUD operations
async def create_user(db: AsyncSession, user: schemas.UserCreate):
    hashed_password = get_password_hash(user.password)

    db_user = models.User(
        email=user.email,
        hashed_password=hashed_password,
        language=user.language,
        first_name=user.first_name,
        last_name=user.last_name,
        nick_name=user.nick_name,
        gender=user.gender,
        created_at=datetime.utcnow(),
    )

    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user


async def get_user_by_email(db: AsyncSession, email: str):
    result = await db.execute(select(models.User).where(models.User.email == email))
    return result.scalar_one_or_none()


async def get_user(db: AsyncSession, user_id: int):
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    return result.scalar_one_or_none()


# Transcript CRUD operations
async def create_transcript(
    db: AsyncSession, transcript: schemas.TranscriptCreate, user_id: int
):
    db_transcript = models.Transcript(
        title=transcript.title,
        content=transcript.content,
        user_id=user_id,
        created_at=datetime.utcnow(),
    )

    db.add(db_transcript)
    await db.commit()
    await db.refresh(db_transcript)
    return db_transcript


async def get_transcript(db: AsyncSession, transcript_id: int, user_id: int):
    result = await db.execute(
        select(models.Transcript).where(
            models.Transcript.id == transcript_id, models.Transcript.user_id == user_id
        )
    )
    return result.scalar_one_or_none()


async def get_user_transcripts(
    db: AsyncSession, user_id: int, skip: int = 0, limit: int = 100
):
    result = await db.execute(
        select(models.Transcript)
        .where(models.Transcript.user_id == user_id)
        .order_by(
            models.Transcript.updated_at.desc().nulls_last(),
            models.Transcript.created_at.desc(),
        )
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


async def update_transcript(
    db: AsyncSession, transcript_id: int, transcript_update: dict, user_id: int
):
    transcript = await get_transcript(db, transcript_id, user_id)
    if transcript:
        for field, value in transcript_update.items():
            setattr(transcript, field, value)
        transcript.updated_at = datetime.utcnow()

        await db.commit()
        await db.refresh(transcript)
        return transcript
    return None


async def delete_transcript(db: AsyncSession, transcript_id: int, user_id: int):
    transcript = await get_transcript(db, transcript_id, user_id)
    if transcript:
        # First, delete the related note if it exists
        related_note = await get_note_by_transcript(db, transcript_id, user_id)
        if related_note:
            await delete_note(db, related_note.id, user_id)

        # Then delete the transcript
        await db.delete(transcript)
        await db.commit()
    return transcript


# Note CRUD operations
async def create_note(db: AsyncSession, note: schemas.NoteCreate, user_id: int):
    db_note = models.Note(
        title=note.title,
        content=note.content,
        transcript_id=note.transcript_id,
        user_id=user_id,
        created_at=datetime.utcnow(),
    )

    db.add(db_note)
    await db.commit()
    await db.refresh(db_note)
    return db_note


async def get_note(db: AsyncSession, note_id: int, user_id: int):
    result = await db.execute(
        select(models.Note).where(
            models.Note.id == note_id, models.Note.user_id == user_id
        )
    )
    return result.scalar_one_or_none()


async def get_user_notes(
    db: AsyncSession, user_id: int, skip: int = 0, limit: int = 100
):
    result = await db.execute(
        select(models.Note)
        .where(models.Note.user_id == user_id)
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


async def get_note_by_transcript(db: AsyncSession, transcript_id: int, user_id: int):
    result = await db.execute(
        select(models.Note).where(
            models.Note.transcript_id == transcript_id, models.Note.user_id == user_id
        )
    )
    return result.scalar_one_or_none()


async def update_note(db: AsyncSession, note_id: int, note_update: dict, user_id: int):
    note = await get_note(db, note_id, user_id)
    if note:
        for field, value in note_update.items():
            setattr(note, field, value)

        # Only set updated_at if not explicitly provided
        if "updated_at" not in note_update:
            note.updated_at = datetime.utcnow()

        await db.commit()
        await db.refresh(note)
        return note
    return None


async def update_note_with_answers(
    db: AsyncSession,
    note_id: int,
    updated_title: str,
    updated_content: str,
    user_id: int,
):
    note = await get_note(db, note_id, user_id)
    if note:
        note.title = updated_title
        note.content = updated_content
        note.updated_at = datetime.utcnow()

        await db.commit()
        await db.refresh(note)
        return note
    return None


async def delete_note(db: AsyncSession, note_id: int, user_id: int):
    note = await get_note(db, note_id, user_id)
    if note:
        await db.delete(note)
        await db.commit()
    return note


async def update_user(db: AsyncSession, user_id: int, user_update: dict):
    user = await get_user(db, user_id)
    if user:
        for field, value in user_update.items():
            setattr(user, field, value)

        await db.commit()
        await db.refresh(user)
        return user
    return None
