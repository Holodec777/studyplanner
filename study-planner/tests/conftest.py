import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.auth import hash_password
from app.db import Base, get_db
from app.main import app
from app.models import User


@pytest.fixture
def client(tmp_path):
    engine = create_engine("sqlite:///" + str(tmp_path / "test.db"), connect_args={"check_same_thread": False})
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(engine)
    with TestingSession() as db:
        db.add_all(
            [
                User(username="student", password_hash=hash_password("student123"), role="student"),
                User(username="other", password_hash=hash_password("otherpass123"), role="student"),
                User(username="admin", password_hash=hash_password("admin123"), role="admin"),
            ]
        )
        db.commit()

    def override_get_db():
        with TestingSession() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    engine.dispose()
