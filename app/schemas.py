# app/schemas.py
from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

class EnrollmentCreate(BaseModel):
    student_id: str
    course_id: str
    amount: Optional[float] = 0.0

class EnrollmentOut(BaseModel):
    # enable from_orm/from_attributes for Pydantic v2
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: str
    course_id: str
    status: str
    created_at: Optional[datetime] = None