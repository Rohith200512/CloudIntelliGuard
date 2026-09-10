"""pytest configuration and shared async fixtures."""
import asyncio
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database.connection import Base, get_db
from app.main import app
from app.database.seed import seed_defaults
from app.core.config import settings

# Use an in-memory SQLite database for tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="session")
async def test_session_factory(test_engine):
    return async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


@pytest_asyncio.fixture
async def db(test_session_factory):
    async with test_session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture(scope="session")
async def seeded_db(test_session_factory):
    """Session-scoped fixture that seeds roles and admin user once."""
    async with test_session_factory() as session:
        await seed_defaults(session)
    yield


@pytest_asyncio.fixture
async def client(test_session_factory, seeded_db):
    """AsyncClient with DB dependency override."""
    async def override_get_db():
        async with test_session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def auth_headers(client):
    """Returns Authorization headers for the seeded admin user."""
    resp = await client.post(
        "/api/v1/auth/login",
        data={
            "username": settings.admin_username,
            "password": settings.admin_password,
        },
    )
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
