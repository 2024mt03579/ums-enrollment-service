# app/main.py
from typing import List, Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import os
import logging

from app import models, schemas, database, events

# config / env
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@db:5432/enrollment_db")
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq/")

# logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("enrollment-service")

app = FastAPI(title="Enrollment Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create DB tables and start background consumer at startup (for demo)
@app.on_event("startup")
def startup():
    logger.info("Initializing DB and starting payment event consumer...")
    database.init_db(DATABASE_URL)
    events.start_consumer(DATABASE_URL, RABBITMQ_URL)
    logger.info("Startup complete.")

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Root + health endpoints
@app.get("/")
def root():
    return {"service": "Enrollment Service", "status": "running", "endpoints": ["/enrollments", "/docs", "/openapi.json"]}

@app.get("/health")
def health():
    try:
        db = database.SessionLocal()
        # quick check
        db.execute("SELECT 1")
        db.close()
    except Exception as e:
        logger.exception("Health check failed: %s", e)
        raise HTTPException(status_code=503, detail="Database unreachable")
    return {"status": "ok"}

# Create enrollment (register) -> PENDING, publish RegistrationPendingPayment
@app.post("/enrollments", response_model=schemas.EnrollmentOut, status_code=201)
def register_course(enrollment_in: schemas.EnrollmentCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    enrollment = models.Enrollment(
        student_id=enrollment_in.student_id,
        course_id=enrollment_in.course_id,
        status="PENDING"
    )
    db.add(enrollment)
    db.commit()
    db.refresh(enrollment)

    # Publish RegistrationPendingPayment event (background)
    event = {
        "type": "RegistrationPendingPayment",
        "payload": {
            "enrollment_id": enrollment.id,
            "student_id": enrollment.student_id,
            "course_id": enrollment.course_id,
            "amount": enrollment_in.amount
        }
    }
    background_tasks.add_task(
        events.publish_event,
        os.getenv("RABBITMQ_URL", RABBITMQ_URL),
        "enrollment.events",
        event
    )
    logger.info("Created enrollment id=%s student=%s course=%s status=PENDING",
                enrollment.id, enrollment.student_id, enrollment.course_id)
    return schemas.EnrollmentOut.from_orm(enrollment)

# Get single enrollment by numeric id
@app.get("/enrollments/{enrollment_id}", response_model=schemas.EnrollmentOut)
def get_enrollment(enrollment_id: int, db: Session = Depends(get_db)):
    enrollment = db.query(models.Enrollment).filter(models.Enrollment.id == enrollment_id).first()
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    return schemas.EnrollmentOut.from_orm(enrollment)

# Delete/drop enrollment (soft state change)
@app.delete("/enrollments/{enrollment_id}", response_model=schemas.EnrollmentOut)
def drop_course(enrollment_id: int, db: Session = Depends(get_db)):
    enrollment = db.query(models.Enrollment).filter(models.Enrollment.id == enrollment_id).first()
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    enrollment.status = "DROPPED"
    db.commit()
    db.refresh(enrollment)
    logger.info("Dropped enrollment id=%s", enrollment_id)
    return schemas.EnrollmentOut.from_orm(enrollment)

# List enrollments (optionally filter by student_id)
@app.get("/enrollments", response_model=List[schemas.EnrollmentOut])
def list_enrollments(student_id: Optional[str] = Query(None), status: Optional[str] = Query(None), db: Session = Depends(get_db)):
    q = db.query(models.Enrollment)
    if student_id:
        q = q.filter(models.Enrollment.student_id == student_id)
    if status:
        q = q.filter(models.Enrollment.status == status.upper())
    results = q.order_by(models.Enrollment.created_at.desc()).all()
    return [schemas.EnrollmentOut.from_orm(e) for e in results]