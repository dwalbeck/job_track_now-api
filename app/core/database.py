from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .config import settings

# Create engine with proper connection pool configuration
# pool_size: Number of connections to maintain in the pool
# max_overflow: Number of connections that can be created beyond pool_size
# pool_timeout: Seconds to wait before giving up on getting a connection
# pool_recycle: Recycle connections after this many seconds (prevents stale connections)
# pool_pre_ping: Verify connections are alive before using them
engine = create_engine(
    settings.database_url,
    pool_size=20,           # Increased from default 5
    max_overflow=40,        # Increased from default 10
    pool_timeout=30,        # Wait up to 30 seconds for a connection
    pool_recycle=3600,      # Recycle connections after 1 hour
    pool_pre_ping=True,     # Test connections before use
    echo=False              # Set to True for SQL debugging
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception:
        # Rollback any uncommitted transaction on error
        db.rollback()
        raise
    finally:
        # Always close the session to return connection to pool
        db.close()