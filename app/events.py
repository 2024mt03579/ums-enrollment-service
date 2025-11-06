import pika, json, threading, time
from app import models, database
from sqlalchemy.orm import Session
import os

def publish_event(rabbitmq_url: str, routing_key: str, event: dict):
    params = pika.URLParameters(rabbitmq_url)
    connection = pika.BlockingConnection(params)
    channel = connection.channel()
    channel.exchange_declare(exchange="ums_events", exchange_type="topic", durable=True)
    body = json.dumps(event)
    channel.basic_publish(exchange="ums_events", routing_key=routing_key, body=body)
    connection.close()

def _process_payment_event(body: dict, db: Session):
    etype = body.get("type")
    payload = body.get("payload", {})
    if etype == "PaymentConfirmed":
        enrollment_id = payload.get("enrollment_id")
        enrollment = db.query(models.Enrollment).filter(models.Enrollment.id == enrollment_id).first()
        if enrollment:
            enrollment.status = "CONFIRMED"
            db.commit()
    elif etype == "PaymentFailed":
        enrollment_id = payload.get("enrollment_id")
        enrollment = db.query(models.Enrollment).filter(models.Enrollment.id == enrollment_id).first()
        if enrollment:
            enrollment.status = "FAILED"
            db.commit()

def _consumer_thread(database_url: str, rabbitmq_url: str):
    # connect DB
    database.init_db(database_url)
    db = database.SessionLocal()
    params = pika.URLParameters(rabbitmq_url)
    connection = pika.BlockingConnection(params)
    channel = connection.channel()
    channel.exchange_declare(exchange="ums_events", exchange_type="topic", durable=True)
    # create queue and bind to payment.* events
    result = channel.queue_declare(queue="", exclusive=True)
    queue_name = result.method.queue
    # bind to payment events (assuming Payment service publishes to payment.events)
    channel.queue_bind(exchange="ums_events", queue=queue_name, routing_key="payment.events.#")
    print("Enrollment consumer waiting for payment events...")
    def callback(ch, method, properties, body):
        try:
            payload = json.loads(body)
            _process_payment_event(payload, db)
            ch.basic_ack(delivery_tag=method.delivery_tag)
        except Exception as e:
            print("Error processing payment event:", e)
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

    channel.basic_consume(queue=queue_name, on_message_callback=callback, auto_ack=False)
    try:
        channel.start_consuming()
    except Exception as e:
        print("Consumer stopped:", e)
    finally:
        db.close()
        connection.close()

_consumer = None
def start_consumer(database_url: str, rabbitmq_url: str):
    global _consumer
    if _consumer is None:
        _consumer = threading.Thread(target=_consumer_thread, args=(database_url, rabbitmq_url), daemon=True)
        _consumer.start()