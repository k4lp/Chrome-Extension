"""Database setup and session management."""

from typing import Generator
from pathlib import Path
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from loguru import logger

# Base class for all models
Base = declarative_base()

# Global engine and session factory
_engine: Engine = None
_SessionLocal: sessionmaker = None


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    """Enable foreign keys for SQLite."""
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def init_db(db_path: str, echo: bool = False) -> None:
    """Initialize database connection and create tables.

    Args:
        db_path: Path to SQLite database file
        echo: Enable SQL echo for debugging
    """
    global _engine, _SessionLocal

    # Ensure directory exists
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    # Create engine
    _engine = create_engine(
        f"sqlite:///{db_path}",
        echo=echo,
        connect_args={"check_same_thread": False},  # Needed for SQLite
        pool_pre_ping=True,  # Verify connections before using
    )

    # Create session factory
    _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)

    # Import all models to register them
    from . import models  # noqa: F401

    # Create all tables
    Base.metadata.create_all(bind=_engine)
    logger.info(f"Database initialized at {db_path}")


def get_db() -> Generator[Session, None, None]:
    """Get database session.

    Yields:
        Database session
    """
    if _SessionLocal is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")

    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_engine() -> Engine:
    """Get database engine.

    Returns:
        SQLAlchemy engine
    """
    if _engine is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return _engine


def close_db() -> None:
    """Close database connections."""
    global _engine, _SessionLocal
    if _engine:
        _engine.dispose()
        _engine = None
        _SessionLocal = None
        logger.info("Database connections closed")


def recreate_db(db_path: str) -> None:
    """Drop all tables and recreate schema.

    CAUTION: This will delete all data!

    Args:
        db_path: Path to SQLite database file
    """
    global _engine, _SessionLocal

    # Close existing connections
    close_db()

    # Ensure directory exists
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    # Create engine
    _engine = create_engine(
        f"sqlite:///{db_path}",
        echo=False,
        connect_args={"check_same_thread": False},
        pool_pre_ping=True,
    )

    # Import all models to register them
    from . import models  # noqa: F401

    # Drop all tables
    Base.metadata.drop_all(bind=_engine)
    logger.info("Dropped all tables")

    # Create all tables with new schema
    Base.metadata.create_all(bind=_engine)
    logger.info(f"Recreated database at {db_path} with new schema")

    # Create session factory
    _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
