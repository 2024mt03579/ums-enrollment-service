## Enrollment Service (University Management System)
This repository contains a starter Enrollment Service implemented with FastAPI that demonstrates:

- REST endpoints to register / drop / fetch enrollments
- Persistence with PostgreSQL (SQLAlchemy)
- Basic event publishing to RabbitMQ (RegistrationPendingPayment)
- A background consumer that listens for payment events and updates enrollments

#### Repo Structure
```
/app
  ├─ main.py 
  ├─ models.py
  ├─ schemas.py
  ├─ database.py
  └─ events.py
Dockerfile
/manifests
  ├─ config.yaml 
  ├─ deployment.yaml
  ├─ hpa.yaml
  ├─ postgresdb.yaml
  └─ rabbitmq.yaml
requirements.txt
README.md
LICENSE
enrolment_Service.drawio
```

#### Build and push Image:

`docker build . -t dtummidibits/enrolment-service:1.0`

`docker push dtummidibits/enrolment-service:1.0`

- Open API docs: `http://<NodePort_IP>:8000/docs`
- Open RabbitMQ management: `http://<NodePort_IP>:15672 (guest/guest)`

#### Deploy manifests to any Kubernetes environment

- Update the docker image version in the deployment.yaml 
- Run `kubectl apply -f ./manifests/.` 
- Verify services `kubectl get all -n ums`

#### How it works
- POST /enrollments creates an enrollment record with status PENDING and publishes a RegistrationPendingPayment event to RabbitMQ.
- Payment service consumes that event and will publish all "PENDING" payment students and their IDs.
- Payment service can approve the payment and mark it PaymentSucceeded.
- The Enrollment service runs a background consumer which listens to payment events and updates the enrollment status accordingly.