Enrollment Service (University Management System)
This repository contains a starter Enrollment Service implemented with FastAPI that demonstrates:

REST endpoints to register / drop / fetch enrollments
Persistence with PostgreSQL (SQLAlchemy)
Basic event publishing to RabbitMQ (RegistrationPendingPayment)
A background consumer that listens for payment events and updates enrollments
Structure
/app

  ├─ main.py            # FastAPI app and endpoints

  ├─ models.py          # SQLAlchemy models

  ├─ schemas.py         # Pydantic schemas

  ├─ database.py        # DB initialization and session factory

  └─ events.py          # RabbitMQ publisher and background consumer

Dockerfile

/manifests

requirements.txt

README.md
Run locally (Docker Compose)
Build and start services:

docker build . -t dtummidibits/enrolment-service:1.0

Open API docs: http://<NodePort_IP>:8000/docs
Open RabbitMQ management: http://<NodePort_IP>:15672 (guest/guest)
How it works (simplified)
POST /enrollments creates an enrollment record with status PENDING and publishes a RegistrationPendingPayment event to RabbitMQ.
Payment service (not included here) consumes that event and will publish PaymentConfirmed or PaymentFailed to the ums_events exchange under routing keys like payment.events.confirmed.
The Enrollment service runs a background consumer which listens to payment events and updates the enrollment status accordingly.

