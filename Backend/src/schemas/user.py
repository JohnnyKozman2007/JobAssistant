"""User profile schemas."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    """Base user profile data."""
    email: EmailStr
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    phone_number: Optional[str] = None
    location: Optional[str] = None
    desired_job_title: Optional[str] = None
    years_of_experience: Optional[int] = Field(None, ge=0)


class UserCreate(UserBase):
    """Schema for creating a new user."""
    pass


class UserUpdate(BaseModel):
    """Schema for updating user profile."""
    email: Optional[EmailStr] = None
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    phone_number: Optional[str] = None
    location: Optional[str] = None
    desired_job_title: Optional[str] = None
    years_of_experience: Optional[int] = Field(None, ge=0)


class UserResponse(UserBase):
    """Schema for user profile response."""
    user_id: str
    created_at: datetime
    updated_at: datetime
    has_resume: bool = False

    class Config:
        from_attributes = True


class ResumeUpload(BaseModel):
    """Schema for resume upload endpoint."""
    filename: str = Field(..., min_length=1)
    content_type: str = Field(..., regex=r"application/(pdf|vnd\.openxmlformats-officedocument\.wordprocessingml\.document|msword)|text/plain")


class ResumeResponse(BaseModel):
    """Schema for resume response."""
    filename: str
    uploaded_at: datetime
    mimetype: str


class ScoreRequest(BaseModel):
    """Schema for resume scoring request."""
    job_url: str = Field(..., min_length=1)


class ScoreResponse(BaseModel):
    """Schema for scoring response."""
    match_percentage: float = Field(..., ge=0, le=100)
    key_matches: list[str]
    gaps: list[str]
    recommendations: list[str]


class TailorAnswerRequest(BaseModel):
    """Schema for tailored answer generation."""
    job_url: str = Field(..., min_length=1)
    user_question: str = Field(..., min_length=1)


class TailorAnswerResponse(BaseModel):
    """Schema for tailored answer response."""
    answer: str
    relevance_score: float = Field(..., ge=0, le=100)
