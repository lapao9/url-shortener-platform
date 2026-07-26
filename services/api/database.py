import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://urlshortener:changeme@postgres:5432/urlshortener")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db(): #Retorna objeto do tipo SessionLocal
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()