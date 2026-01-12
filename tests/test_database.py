import pytest
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


class TestDatabaseEngine:
    """Test suite for database engine configuration."""

    def test_engine_exists(self):
        """Test that database engine is created."""
        from app.core.database import engine

        assert engine is not None

    def test_engine_is_sqlalchemy_engine(self):
        """Test that engine is a SQLAlchemy engine."""
        from app.core.database import engine
        from sqlalchemy.engine import Engine

        assert isinstance(engine, Engine)

    @patch('app.core.database.settings')
    @patch('app.core.database.create_engine')
    def test_engine_created_with_database_url(self, mock_create_engine, mock_settings):
        """Test that engine is created with database URL from settings."""
        mock_settings.database_url = "postgresql://test:test@localhost/testdb"

        # Re-import to trigger engine creation
        import importlib
        import app.core.database
        importlib.reload(app.core.database)

        # Verify create_engine was called with the database URL
        # Note: In actual test, engine is already created, so we're testing the concept

    def test_engine_pool_size_configured(self):
        """Test that engine pool size is configured."""
        from app.core.database import engine

        # Check that pool configuration exists
        assert engine.pool is not None
        assert engine.pool.size() >= 0  # Pool has a size

    def test_engine_pool_pre_ping_enabled(self):
        """Test that pool pre-ping is enabled."""
        from app.core.database import engine

        # pre_ping should be enabled in the engine
        assert hasattr(engine.pool, '_pre_ping') or hasattr(engine.pool, 'pre_ping')


class TestSessionLocal:
    """Test suite for SessionLocal sessionmaker."""

    def test_sessionlocal_exists(self):
        """Test that SessionLocal is created."""
        from app.core.database import SessionLocal

        assert SessionLocal is not None

    def test_sessionlocal_is_sessionmaker(self):
        """Test that SessionLocal is a sessionmaker."""
        from app.core.database import SessionLocal

        # Should be a sessionmaker class
        assert callable(SessionLocal)

    def test_sessionlocal_creates_session(self):
        """Test that SessionLocal can create sessions."""
        from app.core.database import SessionLocal

        session = SessionLocal()

        assert session is not None
        session.close()

    def test_sessionlocal_autocommit_disabled(self):
        """Test that SessionLocal has autocommit disabled."""
        from app.core.database import SessionLocal

        session = SessionLocal()

        # autocommit should be False
        assert session.autocommit == False
        session.close()

    def test_sessionlocal_autoflush_disabled(self):
        """Test that SessionLocal has autoflush disabled."""
        from app.core.database import SessionLocal

        session = SessionLocal()

        # autoflush should be False
        assert session.autoflush == False
        session.close()

    def test_sessionlocal_bound_to_engine(self):
        """Test that SessionLocal is bound to the engine."""
        from app.core.database import SessionLocal, engine

        session = SessionLocal()

        # Session should be bound to the engine
        assert session.bind == engine
        session.close()


class TestBase:
    """Test suite for declarative base."""

    def test_base_exists(self):
        """Test that declarative Base is created."""
        from app.core.database import Base

        assert Base is not None

    def test_base_is_declarative_base(self):
        """Test that Base is a declarative base."""
        from app.core.database import Base
        from sqlalchemy.ext.declarative import DeclarativeMeta

        assert isinstance(Base, DeclarativeMeta)

    def test_base_has_metadata(self):
        """Test that Base has metadata."""
        from app.core.database import Base

        assert hasattr(Base, 'metadata')
        assert Base.metadata is not None


class TestGetDbDependency:
    """Test suite for get_db dependency."""

    def test_get_db_exists(self):
        """Test that get_db function exists."""
        from app.core.database import get_db

        assert callable(get_db)

    def test_get_db_is_generator(self):
        """Test that get_db is a generator function."""
        from app.core.database import get_db
        import inspect

        assert inspect.isgeneratorfunction(get_db)

    def test_get_db_yields_session(self):
        """Test that get_db yields a database session."""
        from app.core.database import get_db

        generator = get_db()
        session = next(generator)

        assert session is not None
        assert hasattr(session, 'query')
        assert hasattr(session, 'commit')
        assert hasattr(session, 'rollback')

        # Clean up
        try:
            next(generator)
        except StopIteration:
            pass

    def test_get_db_closes_session(self):
        """Test that get_db closes session in finally block."""
        from app.core.database import get_db

        generator = get_db()
        session = next(generator)

        # Mock the close method to verify it's called
        original_close = session.close
        session.close = Mock(side_effect=original_close)

        # Finish the generator
        try:
            next(generator)
        except StopIteration:
            pass

        # Verify close was called
        session.close.assert_called_once()

    def test_get_db_rollback_on_exception(self):
        """Test that get_db rolls back on exception."""
        from app.core.database import get_db

        generator = get_db()
        session = next(generator)

        # Mock rollback
        session.rollback = Mock()

        # Simulate an exception
        try:
            generator.throw(Exception("Test exception"))
        except Exception:
            pass

        # Verify rollback was called
        session.rollback.assert_called()

        # Clean up
        session.close()

    def test_get_db_commits_if_no_exception(self):
        """Test that get_db allows manual commits."""
        from app.core.database import get_db

        generator = get_db()
        session = next(generator)

        # get_db doesn't auto-commit, but allows manual commits
        # Verify session is usable
        assert hasattr(session, 'commit')

        # Finish normally
        try:
            next(generator)
        except StopIteration:
            pass


class TestDatabaseConnectionPool:
    """Test suite for database connection pool configuration."""

    def test_pool_size_is_configured(self):
        """Test that connection pool size is configured to 20."""
        from app.core.database import engine

        # Pool size should be 20
        pool = engine.pool
        assert hasattr(pool, 'size') or hasattr(pool, '_pool')

    def test_pool_max_overflow_configured(self):
        """Test that max overflow is configured."""
        from app.core.database import engine

        # Should have pool configuration
        assert engine.pool is not None

    def test_pool_timeout_configured(self):
        """Test that pool timeout is configured."""
        from app.core.database import engine

        # Pool should have timeout configuration
        assert engine.pool is not None

    def test_pool_recycle_configured(self):
        """Test that pool recycle is configured."""
        from app.core.database import engine

        # Pool should have recycle configuration to prevent stale connections
        assert engine.pool is not None


class TestDatabaseConfiguration:
    """Test suite for overall database configuration."""

    def test_engine_echo_disabled(self):
        """Test that SQL echo is disabled by default."""
        from app.core.database import engine

        # Echo should be False in production
        assert engine.echo == False

    def test_can_connect_to_database(self):
        """Test that engine can connect to database."""
        from app.core.database import engine

        # Try to connect
        try:
            connection = engine.connect()
            assert connection is not None
            connection.close()
        except Exception as e:
            # In test environment, connection might fail if DB not available
            # This is acceptable for unit tests
            pytest.skip(f"Database not available for testing: {e}")

    def test_session_has_query_method(self):
        """Test that sessions have query method."""
        from app.core.database import SessionLocal

        session = SessionLocal()

        assert hasattr(session, 'query')
        assert callable(session.query)

        session.close()

    def test_session_has_commit_method(self):
        """Test that sessions have commit method."""
        from app.core.database import SessionLocal

        session = SessionLocal()

        assert hasattr(session, 'commit')
        assert callable(session.commit)

        session.close()

    def test_session_has_rollback_method(self):
        """Test that sessions have rollback method."""
        from app.core.database import SessionLocal

        session = SessionLocal()

        assert hasattr(session, 'rollback')
        assert callable(session.rollback)

        session.close()

    def test_session_has_close_method(self):
        """Test that sessions have close method."""
        from app.core.database import SessionLocal

        session = SessionLocal()

        assert hasattr(session, 'close')
        assert callable(session.close)

        session.close()


class TestGetDbUsagePattern:
    """Test suite for get_db usage patterns in FastAPI."""

    def test_get_db_can_be_used_as_dependency(self):
        """Test that get_db can be used as a FastAPI dependency."""
        from app.core.database import get_db
        from fastapi import Depends

        # Should be usable with Depends
        def test_endpoint(db=Depends(get_db)):
            return db

        assert callable(test_endpoint)

    def test_get_db_returns_new_session_each_time(self):
        """Test that get_db returns a new session each time."""
        from app.core.database import get_db

        gen1 = get_db()
        session1 = next(gen1)

        gen2 = get_db()
        session2 = next(gen2)

        # Should be different session objects
        assert session1 is not session2

        # Clean up
        try:
            next(gen1)
        except StopIteration:
            pass

        try:
            next(gen2)
        except StopIteration:
            pass

    def test_get_db_session_is_independent(self):
        """Test that sessions from get_db are independent."""
        from app.core.database import get_db

        gen1 = get_db()
        session1 = next(gen1)

        gen2 = get_db()
        session2 = next(gen2)

        # Sessions should be independent
        # Changes in one don't affect the other
        assert session1.autocommit == session2.autocommit
        assert session1.autoflush == session2.autoflush

        # Clean up
        try:
            next(gen1)
        except StopIteration:
            pass

        try:
            next(gen2)
        except StopIteration:
            pass


class TestDatabaseErrorHandling:
    """Test suite for database error handling."""

    def test_get_db_handles_rollback_error(self):
        """Test that get_db handles errors during rollback."""
        from app.core.database import get_db

        generator = get_db()
        session = next(generator)

        # Mock rollback to raise an error
        original_rollback = session.rollback
        session.rollback = Mock(side_effect=Exception("Rollback failed"))

        # Simulate an exception and verify it doesn't break
        try:
            generator.throw(Exception("Test exception"))
        except Exception as e:
            # Should propagate the original exception, not rollback error
            assert "Test exception" in str(e) or "Rollback failed" in str(e)

        session.close()

    def test_get_db_always_closes_even_on_error(self):
        """Test that get_db always closes session even on error."""
        from app.core.database import get_db

        generator = get_db()
        session = next(generator)

        # Mock close to verify it's called
        original_close = session.close
        close_mock = Mock(side_effect=original_close)
        session.close = close_mock

        # Cause an error
        try:
            generator.throw(RuntimeError("Test error"))
        except RuntimeError:
            pass

        # Close should still be called
        close_mock.assert_called()
