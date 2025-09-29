from databases import Database
from typing import List, Optional
from . import models, schemas
from .auth import get_password_hash
import json


# User CRUD operations
async def create_user(db: Database, user: schemas.UserCreate):
    hashed_password = get_password_hash(user.password)
    from datetime import datetime

    query = models.User.__table__.insert().values(
        email=user.email,
        hashed_password=hashed_password,
        created_at=datetime.utcnow(),
    )
    user_id = await db.execute(query)
    return await get_user(db, user_id)


async def get_user_by_email(db: Database, email: str):
    query = models.User.__table__.select().where(models.User.email == email)
    return await db.fetch_one(query)


async def get_user(db: Database, user_id: int):
    query = models.User.__table__.select().where(models.User.id == user_id)
    return await db.fetch_one(query)


# Transcript CRUD operations
async def create_transcript(
    db: Database, transcript: schemas.TranscriptCreate, user_id: int
):
    from datetime import datetime

    query = models.Transcript.__table__.insert().values(
        title=transcript.title,
        content=transcript.content,
        user_id=user_id,
        created_at=datetime.utcnow(),
    )
    transcript_id = await db.execute(query)
    return await get_transcript(db, transcript_id, user_id)


async def get_transcript(db: Database, transcript_id: int, user_id: int):
    query = models.Transcript.__table__.select().where(
        models.Transcript.id == transcript_id, models.Transcript.user_id == user_id
    )
    return await db.fetch_one(query)


async def get_user_transcripts(
    db: Database, user_id: int, skip: int = 0, limit: int = 100
):
    query = (
        models.Transcript.__table__.select()
        .where(models.Transcript.user_id == user_id)
        .offset(skip)
        .limit(limit)
    )
    return await db.fetch_all(query)


async def update_transcript(
    db: Database, transcript_id: int, transcript_update: dict, user_id: int
):
    transcript = await get_transcript(db, transcript_id, user_id)
    if transcript:
        from datetime import datetime

        query = (
            models.Transcript.__table__.update()
            .where(
                models.Transcript.id == transcript_id,
                models.Transcript.user_id == user_id,
            )
            .values(**transcript_update, updated_at=datetime.utcnow())
        )
        await db.execute(query)
        return await get_transcript(db, transcript_id, user_id)
    return None


async def delete_transcript(db: Database, transcript_id: int, user_id: int):
    transcript = await get_transcript(db, transcript_id, user_id)
    if transcript:
        query = models.Transcript.__table__.delete().where(
            models.Transcript.id == transcript_id, models.Transcript.user_id == user_id
        )
        await db.execute(query)
    return transcript


# Note CRUD operations
async def create_note(db: Database, note: schemas.NoteCreate, user_id: int):
    from datetime import datetime

    query = models.Note.__table__.insert().values(
        title=note.title,
        content=note.content,
        transcript_id=note.transcript_id,
        user_id=user_id,
        created_at=datetime.utcnow(),
    )
    note_id = await db.execute(query)
    return await get_note(db, note_id, user_id)


async def get_note(db: Database, note_id: int, user_id: int):
    query = models.Note.__table__.select().where(
        models.Note.id == note_id, models.Note.user_id == user_id
    )
    note = await db.fetch_one(query)
    return note


async def get_user_notes(db: Database, user_id: int, skip: int = 0, limit: int = 100):
    query = (
        models.Note.__table__.select()
        .where(models.Note.user_id == user_id)
        .offset(skip)
        .limit(limit)
    )
    return await db.fetch_all(query)


async def get_note_by_transcript(db: Database, transcript_id: int, user_id: int):
    query = models.Note.__table__.select().where(
        models.Note.transcript_id == transcript_id, models.Note.user_id == user_id
    )
    return await db.fetch_one(query)


async def update_note(db: Database, note_id: int, note_update: dict, user_id: int):
    note = await get_note(db, note_id, user_id)
    if note:
        from datetime import datetime

        query = (
            models.Note.__table__.update()
            .where(models.Note.id == note_id, models.Note.user_id == user_id)
            .values(**note_update, updated_at=datetime.utcnow())
        )
        await db.execute(query)
        return await get_note(db, note_id, user_id)
    return None


async def update_note_with_answers(
    db: Database, note_id: int, updated_title: str, updated_content: str, user_id: int
):
    note = await get_note(db, note_id, user_id)
    if note:
        from datetime import datetime, timezone

        query = (
            models.Note.__table__.update()
            .where(models.Note.id == note_id, models.Note.user_id == user_id)
            .values(
                title=updated_title,
                content=updated_content,
                updated_at=datetime.now(timezone.utc),
            )
        )
        await db.execute(query)
        return await get_note(db, note_id, user_id)
    return None


async def delete_note(db: Database, note_id: int, user_id: int):
    note = await get_note(db, note_id, user_id)
    if note:
        query = models.Note.__table__.delete().where(
            models.Note.id == note_id, models.Note.user_id == user_id
        )
        await db.execute(query)
    return note
