from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

from core.config import settings

# This is the "Full-Scale" fix.
# pool_recycle=1800 tells SQLAlchemy to automatically discard and
# replace any connection that has been idle for 1800 seconds (30 minutes).
# This prevents your app from ever using a stale/dead connection.
engine = create_engine(
    settings.DATABASE_URL,
    pool_recycle=1800 
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()