from sqlalchemy import Column, Integer, String, DateTime, func
from app.database import Base

class Enrollment(Base):
    __tablename__ = "enrollments"
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String(64), index=True, nullable=False)
    course_id = Column(String(64), index=True, nullable=False)
    status = Column(String(20), default="PENDING", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())