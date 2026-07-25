import os
import json
import time
import logging
import signal
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.sql import func
import redis

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://urlshortener:changeme@postgres:5432/urlshortener")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
CLICK_QUEUE = "clicks:queue"

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class ClickEvent(Base):
    __tablename__ = "click_events"
    id = Column(Integer, primary_key=True, index=True)
    short_code = Column(String(10), index=True, nullable=False)
    clicked_at = Column(DateTime(timezone=True), server_default=func.now())
    user_agent = Column(String(512))
    ip_address = Column(String(45))

Base.metadata.create_all(bind=engine)

redis_client = redis.from_url(REDIS_URL, decode_responses=True)


running = True
def shutdown(signum, frame):
    global running
    logger.info("Shutdown signal received, finishing current batch...")
    running = False

signal.signal(signal.SIGTERM, shutdown)
signal.signal(signal.SIGINT, shutdown)

def process_event(raw: str):
    try:
        event = json.loads(raw)
        db = SessionLocal()
        try:
            click = ClickEvent(
                short_code=event["short_code"],
                user_agent=event.get("user_agent", "")[:512],
                ip_address=event.get("ip_address", "")[:45],
            )
            db.add(click)
            db.commit()
            logger.info(f"Recorded click for {event['short_code']}")
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Failed to process event: {e}")

def main():
    logger.info("Worker starting up...")
    while running:
        try:
            result = redis_client.blpop(CLICK_QUEUE, timeout=5)
            if result:
                _, raw = result
                process_event(raw)
        except redis.ConnectionError as e:
            logger.error(f"Redis connection error: {e}, retrying in 5s")
            time.sleep(5)
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            time.sleep(1)
    logger.info("Worker stopped.")

if __name__ == "__main__":
    main()


    