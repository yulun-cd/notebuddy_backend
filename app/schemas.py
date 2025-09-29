from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime


# User schemas
class UserBase(BaseModel):
    email: EmailStr


class UserCreate(BaseModel):
    email: EmailStr
    password: str


class User(UserBase):
    id: int = Field(read_only=True)
    created_at: datetime = Field(read_only=True)

    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    email: EmailStr
    password: str


# Token schemas
class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str


class TokenData(BaseModel):
    email: Optional[str] = None


class RefreshTokenRequest(BaseModel):
    refresh_token: str


# Transcript schemas
class TranscriptBase(BaseModel):
    title: str
    content: str


class TranscriptCreate(TranscriptBase):
    pass


class TranscriptUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None


class Transcript(TranscriptBase):
    id: int = Field(read_only=True)
    user_id: int = Field(read_only=True)
    created_at: datetime = Field(read_only=True)
    updated_at: Optional[datetime] = Field(read_only=True, default=None)

    class Config:
        from_attributes = True


# Note schemas
class NoteBase(BaseModel):
    title: str
    content: str


class NoteCreate(NoteBase):
    transcript_id: int


class NoteUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None


class Note(NoteBase):
    id: int = Field(read_only=True)
    user_id: int = Field(read_only=True)
    transcript_id: int = Field(read_only=True)
    created_at: datetime = Field(read_only=True)
    updated_at: Optional[datetime] = Field(read_only=True, default=None)

    class Config:
        from_attributes = True


# AI-related schemas
class NoteGenerationRequest(BaseModel):
    transcript_id: int


class FollowUpQuestionsRequest(BaseModel):
    note_id: int


class AnswerSubmission(BaseModel):
    question: str
    answer: str


class NoteUpdateRequest(BaseModel):
    note_id: int
    answers: Dict[str, str]


# Response schemas
class NoteGenerationResponse(BaseModel):
    note: Note
    message: str


class FollowUpQuestionsResponse(BaseModel):
    questions: List[str]
    message: str


class NoteUpdateResponse(BaseModel):
    note: Note
    message: str
