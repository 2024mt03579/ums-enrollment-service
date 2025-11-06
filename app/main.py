from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from app import models, schemas, database, events
from sqlalchemy.orm import Session
from fastapi import Depends
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@db:5432/enrollment_db")
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq/")

app = FastAPI(title="Enrollment Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create DB tables at startup if not exist (for demo)
@app.on_event("startup")
def startup():
    database.init_db(DATABASE_URL)
    events.start_consumer(DATABASE_URL, RABBITMQ_URL)

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/enrollments", response_model=schemas.EnrollmentOut, status_code=201)
def register_course(enrollment_in: schemas.EnrollmentCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    student_service_url = os.getenv("STUDENT_SERVICE_URL", "http://student-service")
    course_service_url = os.getenv("COURSE_SERVICE_URL", "http://course-service")

    enrollment = models.Enrollment(student_id=enrollment_in.student_id, course_id=enrollment_in.course_id, status="PENDING")
    db.add(enrollment)
    db.commit()
    db.refresh(enrollment)

    # publish RegistrationPendingPayment event
    event = {
        "type": "RegistrationPendingPayment",
        "payload": {
            "enrollment_id": enrollment.id,
            "student_id": enrollment.student_id,
            "course_id": enrollment.course_id,
            "amount": enrollment_in.amount
        }
    }
    # publish in background so request returns fast
    background_tasks.add_task(events.publish_event, os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq/"), "enrollment.events", event)
    return schemas.EnrollmentOut.from_orm(enrollment)

@app.get("/enrollments/{enrollment_id}", response_model=schemas.EnrollmentOut)
def get_enrollment(enrollment_id: int, db: Session = Depends(get_db)):
    enrollment = db.query(models.Enrollment).filter(models.Enrollment.id == enrollment_id).first()
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    return schemas.EnrollmentOut.from_orm(enrollment)

@app.delete("/enrollments/{enrollment_id}", response_model=schemas.EnrollmentOut)
def drop_course(enrollment_id: int, db: Session = Depends(get_db)):
    enrollment = db.query(models.Enrollment).filter(models.Enrollment.id == enrollment_id).first()
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    enrollment.status = "DROPPED"
    db.commit()
    db.refresh(enrollment)
    return schemas.EnrollmentOut.from_orm(enrollment)
